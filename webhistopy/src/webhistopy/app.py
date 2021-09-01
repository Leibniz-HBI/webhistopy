'''
Experimental reconceptualisation of Webhistorian in Python
'''

import datetime
import os
import subprocess
import textwrap
import webbrowser
from time import sleep
from urllib.parse import urlparse

import browser_history
import nextcloud_client
import numpy as np
import pandas as pd
import toga
from toga.widgets.scrollcontainer import ScrollContainer
import yaml
from browser_history.browsers import Safari
from toga.style import Pack
from toga.style.pack import COLUMN, ROW

'''
def bar_plot_domains(topdomains, path=None):
    if path is None:
        path = Path.cwd()
    plot = topdomains.sort_values().plot.barh(log=True, figsize=(10, 35), )
    fig = plot.get_figure()
    fig.savefig(path / 'figure.png', bbox_inches='tight')
'''

large_font = Pack(padding=5, font_weight='bold', font_size=11)
large_font_flex = Pack(padding=5, font_size=11, flex=1)
small_font_flex = Pack(padding=5, font_size=9, flex=1)
switch_font = Pack(padding=3, padding_left=25, font_size=11)


def get_domain(url):
    t = urlparse(url).netloc
    full = t.split('.')
    if full[0] == 'www' or full[0] == 'ww':
        return '.'.join(full[1:])
    else:
        return '.'.join(full)


class WebhistoPy(toga.App):

    def startup(self):

        # config

        with open(self.paths.app / "config.yaml") as f:
            config = yaml.safe_load(f)

        self.visits_limit = config['visits_limit']  # minimum visits for a domain not to be hidden
        self.time_limit = config['time_limit']  # number of days to retrieve history for
        self.day_names = config['day_names']
        # Nextcloud drop folder link (use https for encrypted transit!)
        self.drop_link = config['drop_link']
        assert self.drop_link.startswith('https://')  # enforce encryption
        self.contact = config['contact']
        # config end

        self.day_map = dict()

        i = 0
        for day in self.day_names:
            self.day_map[day] = i
            i += 1
            print(self.day_map)

        self.browsers = []
        self.days = []
        self.hidden_domains = []
        self.times = {}
        self.data = {}

        def toggle_browser(switch):
            browser = switch.label
            if browser not in self.browsers:
                self.browsers.append(browser)
            else:
                self.browsers.remove(browser)
            print(self.browsers)

        def browser_switch(browser):
            return toga.Switch(
                browser,
                on_toggle=toggle_browser,
                style=switch_font
            )

        def toggle_day(switch):
            day = switch.label
            if day not in self.days:
                self.days.append(day)
            else:
                self.days.remove(day)
            print(self.days)

        def day_switch(day):
            return toga.Switch(
                day, on_toggle=toggle_day,
                style=switch_font
            )

        def select_time(selection):
            self.times[selection.id] = selection.value
            print(self.times)

        def time_select(name):
            box = toga.Box(style=Pack(direction=ROW))
            box.add(toga.Label(f'Üblicher {name} um ',
                    style=small_font_flex),
                    )
            box.add(toga.Selection(id=name,
                    items=[''] + [str(time) for time in range(24)],
                    on_select=select_time,
                    style=small_font_flex
                    ))
            box.add(toga.Label(' Uhr.',  style=small_font_flex))

            return box

        self.main_window = toga.MainWindow(
            size=(1200, 800), position=(100, 100),
            title=self.formal_name)

        self.left = toga.Box(id='left', style=Pack(direction=COLUMN, flex=1))
        self.right = toga.Box(id='right', style=Pack(direction=ROW, flex=2))

        self.main_box = toga.Box()

        self.main_box.add(self.left)
        self.main_box.add(self.right)

        pseudonym_text = toga.Label(
            "Wie lautet Ihr Teilnahme-Code?",
            style=large_font)
        self.left.add(pseudonym_text)

        self.pseudonym = toga.TextInput(
            placeholder='Bitte hier ihren persönlichen Code eintragen',
            style=large_font
            )

        self.left.add(self.pseudonym)

        select_browser_text = toga.Label(
            "Welche Browser verwenden Sie beruflich?",
            style=large_font)
        self.left.add(select_browser_text)

        supported_browsers = browser_history.utils.get_browsers()
        browser_list = [browser.__name__ for browser in supported_browsers]

        for browser in browser_list:
            self.left.add(browser_switch(browser))

        select_day_text = toga.Label(
            "An welchen Tagen arbeiten Sie üblicherweise?",
            style=large_font)
        self.left.add(select_day_text)

        for day in self.day_names:
            self.left.add(day_switch(day))

        self.left.add(time_select('Beginn'))
        self.left.add(time_select('Feierabend'))

        self.table_container = toga.Box(style=Pack(direction=COLUMN, flex=1))
        self.right.add(self.table_container)
        self.preview = toga.Box(style=Pack(flex=1, direction=COLUMN))
        self.right.add(self.preview)

        '''
        limiter_label = toga.Label(
            'Verberge alle Seiten mit weniger als',
            style=large_font)
        self.visit_limiter = toga.NumberInput(
            min_value=0,
            max_value=500,
            default=10,
            step=10,
            style=large_font
            )
        limiter_label_2 = toga.Label(
            'Besuchen.',
            style=large_font)
        self.left.add(limiter_label)
        self.left.add(self.visit_limiter)
        self.left.add(limiter_label_2)
        '''

        self.left.add(toga.Button(
            'Zeige besuchte Domains',
            style=large_font,
            on_press=self.show_histories
        ))

        self.visit_limiter = self.visits_limit
        limiter_label = toga.Label(
            textwrap.dedent(f'''
            Nur Besuche der letzten {self.time_limit} Tage werden erfasst und
            Domains mit weniger als {self.visit_limiter} Besuchen
            sowie außerhalb der Arbeitszeiten werden verborgen.
            '''),
            style=small_font_flex)
        self.left.add(limiter_label)

        self.main_window.content = self.main_box
        self.main_window.show()


    def remove_row(self, table, row):
        if row.hide == ' ⌫ ':
            row.hide = row.domain
            row.domain = '[verborgen]'
        else:
            row.domain = row.hide
            row.hide = ' ⌫ '

    def create_export(self, button):
        data = {'domains': {}, 'browsers': self.browsers, 'days': self.days, 'times': self.times,
                'participant_code': self.pseudonym.value}
        i = 0
        history = self.history
        for row in self.unmasked_data:
            if row['domain'] in self.hidden_domains:
                key = f'[verborgen_{i}]'
                history['domain'].replace(to_replace=row['domain'], value=f'[verborgen_{i}]', inplace=True)
                i += 1
            elif row['domain'] == '':
                key = 'N/A'
            else:
                key = str(row['domain'])
            data['domains'][key] = row['visits']

        if button.id == "preview":
            try:
                for i in range(len(self.preview.children)):
                    self.preview.remove(self.preview.children[0])
            except IndexError:
                pass
            self.preview.add(toga.MultilineTextInput(
                initial=str(yaml.dump(data)), readonly=True,
                style=small_font_flex
            ))

            self.preview.add(toga.MultilineTextInput(
                initial=history.to_string(index=False, header=['Zeit', 'Domain']), readonly=True,
                style=small_font_flex
            ))
            self.preview.add(toga.Label('Nur exakt diese Daten werden erfasst.'))
            self.preview.add(self.export_button())
            # self.preview.refresh()

        self.data = data

    def preview_button(self):
        button = toga.Button(
            'Vorschau', id='preview', style=large_font,
            on_press=self.create_export)
        return button

    def upload(self, button):
        history_path = os.path.expanduser(f"~/Desktop/{self.pseudonym.value}_web_histopy_history.csv")
        data_path = os.path.expanduser(f"~/Desktop/{self.pseudonym.value}_web_histopy_stats.yaml")

        self.history.to_csv(history_path,
                            header=['Zeit', 'Domain'], index=False)
        with open(data_path, 'w') as f:
            yaml.dump(self.data, f)

        nc = nextcloud_client.Client.from_public_link(self.drop_link)
        nc.drop_file(history_path)
        nc.drop_file(data_path)

        self.main_window.info_dialog(
            'Vielen Dank für Ihre Teilnahme!',
            textwrap.dedent(f"""\
                            Sie können das Programm jetzt schließen und deinstallieren.
                            Die hochgeladenen Dateien wurden für Sie noch einmal in ihrem Desktop-Ordner zur Einsicht
                            gespeichert. Sie können der Nutzung und Speicherung Ihrer Daten jederzeit via Email an {self.contact}
                            widersprechen.
                            """)
        )

    def export_button(self):
        button = toga.Button('Upload', style=large_font, on_press=self.upload)
        return button

    def toggle_domain(self, switch):
            domain = switch.label
            if domain not in self.hidden_domains:
                self.hidden_domains.append(domain)
            else:
                self.hidden_domains.remove(domain)
            print(self.hidden_domains)

    def domain_switch(self, domain):

        return toga.Switch(label=domain, on_toggle=self.toggle_domain)

    def domain_check_list(self, data):
        
        check_list = toga.Box(style=Pack(direction=COLUMN))
        
        for item in data:
            if item['domain'] != '[verborgen]':
                check_list.add(self.domain_switch(item['domain']))

        return toga.ScrollContainer(content=check_list, style=Pack(flex=1))

    def show_histories(self, button):
        if len(self.browsers) == 0:
            self.main_window.error_dialog('Keine Auswahl', 'Bitte wählen Sie mindestens einen Browser.')
            return 1
        data = self.get_histories(self.browsers)

        try:
            for child in range(3):
                self.table_container.remove(self.table_container.children[0])
        except IndexError:
            pass

        self.table_container.add(toga.Label(
            'Welche Domains wollen Sie verbergen?',
            style=large_font))

        self.hidden_domains = []
        self.table = self.domain_check_list(data)

        self.table_container.add(self.table)
        
        self.table_container.add(self.preview_button())

    def get_histories(self, browsers):

        output_df = pd.DataFrame(columns=['domain', 'visits'])

        for browser in browsers:
            Browser = browser_history.utils.get_browser(browser)
            try:
                b = Browser()
            except TypeError:
                self.main_window.error_dialog(
                    'Nicht unterstützt',
                    textwrap.dedent(
                        f"""\
                        {browser} ist leider nicht unterstützt auf ihrem Betriebssystem.
                        Falls dieser Browser installiert ist und sie ihn regelmäßig verwenden, \
                        kontaktieren Sie bitte den Entwickler. Ansonsten wählen sie den Browser bitte ab.
                        """
                    )
                )
                continue
            try:
                output = b.fetch_history()
            except PermissionError:
                if isinstance(b, Safari):
                    webbrowser.open(
                        'x-apple.systempreferences:com.apple.preference.security?Privacy')
                    sleep(1)
                    subprocess.Popen(["open", '/Applications'])
                    sleep(1)
                    self.main_window.info_dialog(
                        'Moin!',
                        textwrap.dedent("""\
                            Aus Privatsphäre-Gründen benötigen wir Ihre Erlaubnis, Safari-Daten auszuwerten.

                            Wechseln Sie bitte ins soeben geöffnete Einstellungsfenster und
                            1. klicken Sie auf das Schloss und geben ihr System-Passwort ein.
                            2. wählen Sie "Vollständiger Datenzugriff" im Menü links.
                            3. ziehen Sie die Webhistopy App aus ihrem "Anwendungen"-Ordner in die Liste \
                                auf der rechten Seite.
                            4. starten Sie die App erneut.

                            Sie haben die Möglichkeit, alle Daten vor Upload zu bereinigen.
                            Herzlichen Dank!""")
                    )
                    raise

            history = output.histories

            df = pd.DataFrame(history)
            
            try:
                df = df[df[0].dt.tz_localize(None) > np.datetime64(
                    datetime.datetime.now() - pd.to_timedelta(f"{self.time_limit}days"))]  # limit to last x days

                week_day_numbers = [self.day_map[day] for day in self.days]

                print(self.days)
                print(week_day_numbers)

                df = df[df[0].dt.weekday.isin(week_day_numbers)]  # limit to work_days

                df = df[df[0].dt.hour < int(self.times['Feierabend'])]
                df = df[df[0].dt.hour > int(self.times['Beginn'])]  # limit to times

                print(df)

                df['domain'] = df[1].apply(lambda url: get_domain(url))
                output_df = output_df.append(df)

            except KeyError:
                self.main_window.error_dialog(
                    'Keine Daten',
                    textwrap.dedent(
                        f"""\
                        Keine Daten für {browser}. Falls dieser Browser installiert ist und sie ihn regelmäßig verwenden, \
                        kontaktieren Sie bitte den Entwickler. Ansonsten wählen sie den Browser ab.
                        """
                        )
                )
                continue
            
        self.history = output_df[[0, 'domain']].sort_values(0)

        top_domains = output_df.value_counts('domain')

        top_df = top_domains
        # top_df = top_domains[top_domains >= self.visit_limiter.value]

        top_df = top_df.reset_index()
        top_df.columns = ['domain', 'visits']

        self.history['domain'][self.history['domain'].isin(
            top_df['domain'][top_df['visits'] <= self.visit_limiter])] = '[verborgen]'

        top_df['domain'][top_df['visits'] <= self.visit_limiter] = '[verborgen]'
        top_df['hide'] = False
        self.unmasked_data = top_df.to_dict('records')

        return self.unmasked_data


def main():
    return WebhistoPy()
