'''
Experimental reconceptualisation of Webhistorian in Python
'''

import webbrowser
import subprocess
import textwrap

from time import sleep
from urllib.parse import urlparse

import browser_history
import pandas as pd
import toga

from browser_history.browsers import Safari
from toga.style import Pack
from toga.style.pack import COLUMN

'''
def bar_plot_domains(topdomains, path=None):
    if path is None:
        path = Path.cwd()
    plot = topdomains.sort_values().plot.barh(log=True, figsize=(10, 35), )
    fig = plot.get_figure()
    fig.savefig(path / 'figure.png', bbox_inches='tight')
'''


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

        self.main_window = toga.MainWindow(title=self.formal_name, size=(1024, 768))

        main_box = toga.SplitContainer()

        left = toga.Box(id='left', style=Pack(direction=COLUMN))
        right = toga.Box(id='right')

        main_box.content = [left, right]

        select_browser_text = toga.Label(
            "Welche Browser verwenden Sie beruflich?",
            style=Pack(flex=1, padding=10))
        left.add(select_browser_text)

        supported_browsers = browser_history.utils.get_browsers()
        browser_list = [browser.__name__ for browser in supported_browsers]

        for browser in browser_list:
            left.add(browser_switch(browser))

        self.table_container = right

        left.add(toga.Button(
            'Zeige besuchte Domains',
            style=Pack(padding=20),
            on_press=self.show_histories
        ))

        self.main_window.content = main_box
        self.main_window.show()

    def show_histories(self, button):
        data = self.get_histories(self.browsers)
        if len(self.table_container.children) > 0:
            self.table_container.remove(self.table_container.children[0])
        table = toga.Table(['domain', 'visits'],
                           data=data, style=Pack(flex=1))

        self.table_container.add(table)

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

        top_df = top_domains[top_domains >= 100]

        top_df = top_df.reset_index()
        top_df.columns = ['domain', 'visits']
        data = top_df.to_dict('records')

        return data


def main():
    return WebhistoPy()
