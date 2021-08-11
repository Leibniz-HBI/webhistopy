'''
Experimental reconceptualisation of Webhistorian in Python
'''

import subprocess
import textwrap
import webbrowser
from time import sleep
from urllib.parse import urlparse

import browser_history
import pandas as pd
import toga
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


large_font = Pack(padding=10, font_weight='bold', font_size=15)
large_font_flex = Pack(padding=10, font_size=15, flex=1)


def get_domain(url):
    t = urlparse(url).netloc
    full = t.split('.')
    if full[0] == 'www' or full[0] == 'ww':
        return '.'.join(full[1:])
    else:
        return '.'.join(full)


class WebhistoPy(toga.App):

    def startup(self):

        self.browsers = []

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
                style=Pack(padding=10, padding_left=25, font_size=15)
            )

        self.main_window = toga.MainWindow(
            size=(1024, 768), position=(100, 100),
            title=self.formal_name)

        self.left = toga.Box(id='left', style=Pack(direction=COLUMN, flex=1))
        self.right = toga.Box(id='right', style=Pack(direction=ROW, flex=2))

        self.main_box = toga.Box()

        self.main_box.add(self.left)
        self.main_box.add(self.right)

        select_browser_text = toga.Label(
            "Welche Browser verwenden Sie beruflich?",
            style=large_font)
        self.left.add(select_browser_text)

        supported_browsers = browser_history.utils.get_browsers()
        browser_list = [browser.__name__ for browser in supported_browsers]

        for browser in browser_list:
            self.left.add(browser_switch(browser))

        self.table_container = toga.Box(style=Pack(direction=COLUMN, flex=1))
        self.right.add(self.table_container)
        self.preview = toga.Box(style=Pack(flex=1, direction=COLUMN))
        self.right.add(self.preview)

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

        self.left.add(toga.Button(
            'Zeige besuchte Domains',
            style=large_font,
            on_press=self.show_histories
        ))

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
        data = {'domains': {}, 'browsers': self.browsers}
        i = 0
        for row in self.table.data:
            if row.domain == '[verborgen]':
                key = f'[verborgen_{i}]'
                i += 1
            elif row.domain == '':
                key = 'N/A'
            else:
                key = str(row.domain)
            data['domains'][key] = row.visits

        if button.id == "preview":
            try:
                for i in range(3):
                    self.preview.remove(self.preview.children[0])
            except IndexError:
                pass
            self.preview.add(toga.MultilineTextInput(
                initial=str(yaml.dump(data)), readonly=True,
                style=large_font_flex
            ))
            self.preview.add(toga.Label('Exakt dieser Text wird hochgeladen.', style=large_font))
            self.preview.add(self.export_button())
            # self.preview.refresh()

    def preview_button(self):
        button = toga.Button(
            'Vorschau', id='preview', style=large_font,
            on_press=self.create_export)
        return button

    def export_button(self):
        button = toga.Button('Upload', style=large_font)
        return button

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

        self.table = toga.Table(
            ['domain', 'visits', 'hide'],
            data=data, style=large_font_flex,
            on_select=self.remove_row)

        self.table_container.add(self.table)
        self.table_container.add(toga.Label(
            'Klicken um eine Seite zu verbergen.',
            style=Pack(padding=10, font_weight='bold', font_size=14)))
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

        top_domains = output_df.value_counts('domain')

        top_df = top_domains
        # top_df = top_domains[top_domains >= self.visit_limiter.value]

        top_df = top_df.reset_index()
        top_df.columns = ['domain', 'visits']
        top_df['domain'][top_df['visits'] <= self.visit_limiter.value] = '[verborgen]'
        top_df['hide'] = " ⌫ "
        data = top_df.to_dict('records')

        return data


def main():
    return WebhistoPy()
