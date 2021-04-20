"""
Experimental reconceptualisation of Webhistorian in Python
"""
import webbrowser
import subprocess
import textwrap

from time import sleep
from urllib.parse import urlparse

from browser_history.browsers import Brave, Chrome, Firefox, Safari
import pandas as pd
import toga
from toga.style import Pack

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

        self.main_window = toga.MainWindow(title=self.formal_name)

        b = Safari()
        try:
            output = b.fetch_history()
        except PermissionError:
            if isinstance(b, Safari):
                webbrowser.open('x-apple.systempreferences:com.apple.preference.security?Privacy')
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
        df['domain'] = df[1].apply(lambda url: get_domain(url))
        top_domains = df.value_counts('domain')
        top_208 = top_domains[top_domains >= 0]
        # bar_plot_domains(top_208)
        top_df = top_208.reset_index()
        top_df.columns = ['domain', 'visits']
        data = top_df.to_dict('records')

        table = toga.Table(['domain', 'visits'],
                           data=data,
                           style=Pack(flex=1))

        # cwd = str(Path.cwd())
        # image = toga.Image(
        #     f'{cwd}/figure.png',
        #     )
        # plot = toga.ImageView(
        #     image,
        #     style=Pack(padding=50),
        #     )
        # plot_viewer = toga.ScrollContainer(
        #    content=plot,
        #     style=Pack(flex=1)
        # )

        main_box = toga.Box()

        main_box.add(table)

        self.main_window.content = main_box
        self.main_window.show()


def main():
    return WebhistoPy()
