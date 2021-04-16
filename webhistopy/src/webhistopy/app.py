"""
Experimental reconceptualisation of Webhistorian in Python
"""
from pathlib import Path
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
        """
        Construct and show the Toga application.

        Usually, you would add your application to a main content box.
        We then create a main window (with a name matching the app), and
        show the main window.
        """
        b = Firefox()
        output = b.fetch_history()
        history = output.histories

        df = pd.DataFrame(history)
        df['domain'] = df[1].apply(lambda url: get_domain(url))
        top_domains = df.value_counts('domain')
        top_208 = top_domains[top_domains >= 0]
        print(top_208)
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

        main_box = toga.SplitContainer()

        main_box.content = [table, table]

        self.main_window = toga.MainWindow(title=self.formal_name)
        self.main_window.content = main_box
        self.main_window.show()


def main():
    return WebhistoPy()
