'''
Experimental reconceptualisation of Webhistorian in Python
'''

import os
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


large_font = Pack(padding=10, font_weight='bold', font_size=14)


def get_domain(url):
    t = urlparse(url).netloc
    full = t.split('.')
    if full[0] == 'www':
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
                style=Pack(padding=10, padding_left=25)
            )

        self.main_window = toga.MainWindow(title=self.formal_name, size=(1024,768))

        self.left = toga.Box(id='left', style=Pack(direction=COLUMN, flex=1))
        self.right = toga.Box(id='right', style=Pack(direction=ROW, flex=2))

        self.main_box = toga.Box()

        self.main_box.add(self.left)
        self.main_box.add(self.right)

        self.main_window.size = (1024, 768)

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
            'Wieviele Besuche pro Domain, um erfasst zu werden?',
            style=large_font)
        self.visit_limiter = toga.NumberInput(
            min_value=0,
            max_value=500,
            default=10,
            step=10,
            style=large_font
            )
        self.left.add(limiter_label)
        self.left.add(self.visit_limiter)

        self.left.add(toga.Button(
            'Zeige besuchte Domains',
            style=large_font,
            on_press=self.show_histories
        ))

        self.main_window.content = self.main_box
        self.main_window.show()

    def remove_row(self, table, row):
        row.domain = '[gelöscht]'

    def create_export(self, button):
        data = {}
        i = 0
        for row in self.table.data:
            if row.domain == '[gelöscht]':
                key = f'[geloescht_{i}]'
                i += 1
            else:
                key = row.domain
            data[key] = row.visits

        if button.id == "preview":
            try:
                for i in range(3):
                    self.preview.remove(self.preview.children[0])
            except IndexError:
                pass
            self.preview.add(toga.MultilineTextInput(
                initial=yaml.dump(data), readonly=True,
                style=Pack(flex=1)
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
            ['domain', 'visits'],
            data=data, style=Pack(flex=1),
            on_double_click=self.remove_row,
            accessors=['domain', 'visits'])

        self.table_container.add(self.table)
        self.table_container.add(toga.Label(
            'Doppelklicken um eine Seite zu löschen.',
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
                        'Hi there!',
                        textwrap.dedent("""\
                            Hello,
                            for privacy reasons, MacOS requires you to give this app Full Disk Access \
                            to analyse your Safari History.
                            Please, in the just opened Preference Window

                            1. Click the lock and enter your password
                            2. Select "Full Disk Access" on the left.
                            3. Drag and drop this App from your Applications folder into the list on the right.
                            5. Restart the app.

                            Thank you so much!""")
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

        top_df = top_domains[top_domains >= self.visit_limiter.value]

        top_df = top_df.reset_index()
        top_df.columns = ['domain', 'visits']
        data = top_df.to_dict('records')

        return data


def main():
    return WebhistoPy()
