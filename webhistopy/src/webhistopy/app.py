"""
Experimental reconceptualisation of Webhistorian in Python
"""

import datetime
import os
import subprocess
import sys
import textwrap
import webbrowser

from pathlib import Path
from time import sleep
from urllib.parse import urlparse
from os.path import expanduser

import browser_history
# import nextcloud_client
import numpy as np
import pandas as pd
import networkx as nx
import toga
import yaml
from pyvis.network import Network
from browser_history.browsers import Safari
from toga.style import Pack
from toga.style.pack import COLUMN, ROW

# from webhistopy.browser_viz import beehive
# from webhistopy.visuals import visuals

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import rcParams
rcParams.update({'figure.autolayout': True})
import toga


cwd = os.getcwd()

"""
def bar_plot_domains(topdomains, path=None):
    if path is None:
        path = Path.cwd()
    plot = topdomains.sort_values().plot.barh(log=True, figsize=(10, 35), )
    fig = plot.get_figure()
    fig.savefig(path / 'figure.png', bbox_inches='tight')
"""


if sys.platform != "darwin":
    large_font = Pack(padding=5, font_weight="bold", font_size=10)
    large_font_flex = Pack(padding=5, font_weight="bold", font_size=10, flex=1)
    small_font_flex = Pack(padding=5, font_size=8, flex=1)
    switch_font = Pack(padding=3, padding_left=25, font_size=10)
else:
    large_font = Pack(padding=4, font_weight="bold", font_size=9)
    large_font_flex = Pack(padding=4, font_weight="bold", flex=1, font_size=9)
    small_font_flex = Pack(padding=4, flex=1)
    switch_font = Pack(padding=0, padding_left=25, font_size=8)


#this is an unfinished list of lists supposed to store button labels, texts etc in different languages. 
#get a string by using labels[id of language][id of string]
labels = []
#English (0)
labels.append(["English","Create a Webhistopy file","Visualize existing Webhistopy file","Languages","Back to Menu"])
#German (1) (work in progress)
labels.append(["Deutsch","Webhistopy-Datei erstellen","Webhistopy-Datei visualisieren","Sprachen","Menu"])
#set default language (English in this case)
current_lang = 0

def get_domain(url):
    t = urlparse(url).netloc
    full = t.split(".")
    if full[0] == "www" or full[0] == "ww":
        return ".".join(full[1:])
    else:
        return ".".join(full)


class WebhistoPy(toga.App):

    def startup(self):

        # config

        with open(self.paths.app / "config.yaml") as f:
            config = yaml.safe_load(f)

        # minimum visits for a domain not to be hidden
        self.visits_limit = config["visits_limit"]
        # number of days to retrieve history for
        self.time_limit = config["time_limit"]
        self.day_names = config["day_names"]
        # Nextcloud drop folder link (use https for encrypted transit!)
        self.drop_link = config["drop_link"]
        assert self.drop_link.startswith("https://")  # enforce encryption
        self.contact = config["contact"]
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
        csv_path = ""

        def toggle_browser(switch):
            browser = switch.text
            if browser not in self.browsers:
                self.browsers.append(browser)
            else:
                self.browsers.remove(browser)
            print(self.browsers)

        def browser_switch(browser):
            return toga.Switch(browser, on_change=toggle_browser, style=switch_font)

        def toggle_day(switch):
            day = switch.text
            if day not in self.days:
                self.days.append(day)
            else:
                self.days.remove(day)
            print(self.days)

        def day_switch(day):
            return toga.Switch(day, on_change=toggle_day, style=switch_font)

        def select_time(selection):
            self.times[selection.id] = selection.value
            print(self.times)

        def time_select(name):
            box = toga.Box(style=Pack(direction=ROW))
            box.add(
                toga.Label(f"Work usually {name} at ", style=small_font_flex),
            )
            box.add(
                toga.Selection(
                    id=name,
                    items=[""] + [str(time) for time in range(24)],
                    on_change=select_time,
                    style=small_font_flex,
                )
            )
            box.add(toga.Label(" o'clock.", style=small_font_flex))

            return box

        #setting up main window

        self.main_window = toga.MainWindow(
            size=(1350, 768), position=(25, 25), title=self.formal_name
        )
        self.main_window.show()
        
        # SCREEN 1: (choose between creating browser history and visualization)
        self.menu = toga.Box(id="menu", style=Pack(direction=COLUMN, flex=1, padding=5))
        self.menu.add(
            toga.Button(labels[current_lang][1], style=large_font, on_press=self.toscreen2))
        self.menu.add(
            toga.Button(labels[current_lang][2], style=large_font, on_press=self.toscreen3))
        #Language menu (wip)
        """self.menu.add(
            toga.Button("Languages", style=large_font, on_press=self.languages)
        )"""
        self.main_window.content = self.menu
        self.main_window.size = (500,500)

        # SCREEN 2: (creating browser history)

        self.left = toga.Box(id="left", style=Pack(direction=COLUMN, flex=1, padding=5))
        self.right = toga.Box(id="right", style=Pack(direction=ROW, flex=2, padding=5))

        self.screen2 = toga.Box()

        self.screen2.add(self.left)
        self.screen2.add(self.right)
        scroll_container = toga.ScrollContainer(content=self.screen2, vertical=True)

        self.left.add(
            toga.Button(labels[current_lang][4], style=large_font, on_press=self.tomenu)
        )

        pseudonym_text = toga.Label("What is your unique participation code?", style=large_font)
        self.left.add(pseudonym_text)

        self.pseudonym = toga.TextInput(
            placeholder="Please enter your code here", style=large_font
        )

        self.left.add(self.pseudonym)

        select_browser_text = toga.Label(
            "Which browser(s) do you use for work?", style=large_font
        )
        self.left.add(select_browser_text)

        supported_browsers = browser_history.utils.get_browsers()
        browser_list = [browser.__name__ for browser in supported_browsers]

        for browser in browser_list:
            self.left.add(browser_switch(browser))
        
        weeks_text = toga.Label("How many days into the past do you want Webhistopy to check?",style=large_font)
        self.left.add(weeks_text)
        self.weeks = toga.NumberInput(min_value=7, max_value=105, step=7)
        self.left.add(self.weeks)

        select_day_text = toga.Label(
            "What days do you usually work?", style=large_font
        )
        self.left.add(select_day_text)

        for day in self.day_names:
            self.left.add(day_switch(day))

        self.left.add(time_select("starts"))
        self.left.add(time_select("ends"))

        self.table_container = toga.Box(
            style=Pack(direction=COLUMN, flex=1, padding=10)
        )
        self.right.add(self.table_container)
        self.preview = toga.Box(style=Pack(flex=1, direction=COLUMN, padding=10))
        self.right.add(self.preview)

        self.visit_limiter = self.visits_limit
        limiter_label = toga.Label(
            textwrap.dedent(
                f"""
            Only visits during your selected time period will 
            be registered. Domains with less than {self.visit_limiter} visits
            as well as domains visited outside of work hours will be hidden.
            """
            ),
            style=small_font_flex,
        )
        self.left.add(limiter_label)

        self.left.add(
            toga.Button(
                "Show visited domains", style=large_font, on_press=self.show_histories
            ))

        self.screen2 = scroll_container
    
    # #SCREEN 3: visualization
    #file explorer
    async def selectfile(self,widget):
        filechoice = self.main_window.open_file_dialog("Choose a file", initial_directory=None, file_types=['csv'], multiple_select=False)
        self.csv_path = await filechoice
    
    #selecting a folder to save files in
    async def selectfolder(self,widget):
        folderchoice = self.main_window.select_folder_dialog("Choose a folder to save your files in", initial_directory=None, multiple_select=False, on_result=None, multiselect=None)
        self.folderpath = await folderchoice

    #show top 30 domains
    def top30(self,button):
        try:
            f = open(self.csv_path,'r')
            history = pd.read_csv(f)
            result = history.groupby('Domain').count()
            result.sort_values('Time',inplace=True,ascending=True)
            result.columns = ['visits']
            data = result.tail(30)
            finishedplot = data.plot(kind='barh', title=str(self.prefix.value) + " top 30",ylabel='visits', figsize=(10,10))
            home = expanduser("~")
            #plt.savefig(Path(home).joinpath("Desktop",str(self.prefix.value)+"web_histopy_top_30.svg"))
            plt.savefig(self.folderpath.joinpath(str(self.prefix.value)+"web_histopy_top_30.svg"))
            #nx.write_gexf(plt, self.folderpath.joinpath(str(self.prefix.value)+"web_histopy_top_30.gexf"))
            f.close()
        except AttributeError:
            print("select file first")
    
    def create_networks(self,button):
        max_timedelta = 600 # maximum time between visits to count as an edge in seconds
        edge_list = pd.DataFrame(columns=['source', 'target', 'timestamp', 'timedelta'])
        try:
            f = open(self.csv_path, 'r')
        except AttributeError:
            print("select file first")
            return 1 # exit function if no file is selected
        history = pd.read_csv(f, parse_dates=['Time'])
        df = history.sort_values(by='Time')
        i = 0
        previous = None
        for row in df.iterrows():
            if previous is not None:
                if row[1]['Time'] - previous[1]['Time'] > pd.Timedelta(0, 's') and row[1]['Time'] - previous[1]['Time'] < pd.Timedelta(max_timedelta, 's'):
                    edge = (previous[1]['Domain'], row[1]['Domain'], row[1]['Time'], (row[1]['Time'] - previous[1]['Time']).seconds)
                    edge_list.loc[len(edge_list)] = edge
            previous = row
        home = expanduser("~")
        edge_path = Path(home).joinpath("Desktop",str(self.prefix.value)+"_web_histopy_edge_list.csv")
        edge_list.to_csv(edge_path, index=False)
        print(f'finished edge list for selected file')
        f.close()
        f = open(edge_path, 'r')
        multi_network = pd.read_csv(f)
        # delete catch all rows for sites visited less than x times
        multi_network = multi_network[multi_network['source'] != '[hidden]']
        multi_network = multi_network[multi_network['target'] != '[hidden]']
        multi_network = multi_network[multi_network['timedelta'] <= 300]  # only include edges with timedelta under 5 minutes
        multi_network = multi_network[multi_network['source'] != multi_network['target']]  # remove self-loops
        grouped = multi_network.groupby(['source', 'target'], as_index=False).count()[['source','target','timestamp']]
        grouped.columns = ['source', 'target', 'weight']
        grouped = grouped[grouped['weight'] >= 2]
        grouped['source'] = grouped['source'].str.replace('hidden', '')
        grouped['target'] = grouped['target'].str.replace('hidden', '')
        f.close()
        f = grouped

        domain_net = Network(height='1080px', width='100%', notebook=False, directed=True, cdn_resources="in_line")
        
        # set the physics layout of the network
        # domain_net.barnes_hut()
        domain_net.force_atlas_2based()
        network = nx.from_pandas_edgelist(f, edge_attr=True, create_using=nx.DiGraph)
        for node in network.nodes:
            network.nodes[node]['title'] = str()
            network.nodes[node]['size'] = 200 * (network.out_degree(node, weight='weight') + 1) / network.size(weight='weight')
        
        domain_net.from_nx(network, node_size_transf= lambda x: x,edge_scaling=True)
        neighbor_map = domain_net.get_adj_list()
        
        # add neighbor data to node hover data
        for node in domain_net.nodes:
            node['title'] += ' Neighbors:<br>' + '<br>'.join(neighbor_map[node['id']])
        
        # domain_net.show_buttons(filter_='edges')
        
        domain_net.set_options("""
        var options = {
            "nodes": {
                "font": {
                    "size": 32
                }},
            "edges": {
                "color": {
                    "inherit": true
                },
                "smooth": {
                    "type": "dynamic",
                    "forceDirection": "none"
                }
            },
            "physics": {
                "forceAtlas2Based": {
                    "gravitationalConstant": -30,
                    "springLength": 0,
                    "springConstant": 0.025,
                    "avoidOverlap": 0.5
                },
                "minVelocity": 0.75,
                "dampening": 0,
                "solver": "forceAtlas2Based"
            }
        }
        """
        )

        #domain_net.show(str(Path(home).joinpath("Desktop","web_history_graph.html")),notebook=False)
        #domain_net.save_graph(self.folderpath.joinpath(str(self.prefix.value)+"_web_history_graph.html"))
        #nx.write_gexf(plt, self.folderpath.joinpath(str(self.prefix.value)+"_web_history_graph.gexf"))
        nx.write_gexf(plt, self.folderpath.joinpath(str(self.prefix.value)+"web_histopy_top_30.gexf"))
        

    #set up window and buttons
    def viswindow(self):
        self.visualization = toga.Box(id="visualization", style=Pack(direction=COLUMN, flex=1, padding=5))
        self.visualization.add(
            toga.Button(labels[current_lang][4], style=large_font, on_press=self.tomenu))

        #self.file_text = toga.Label("Select a Webhistopy file to visualize.", style=large_font)
        #self.visualization.add(self.file_text)
        self.visualization.add(
            toga.Button("Select Webhistopy file to visualize", style=large_font, on_press=self.selectfile))
        
        #choose a folder to save your files to
        self.visualization.add(
            toga.Button("Select a folder to save your files too", style=large_font, on_press=self.selectfolder)
        )
        
        #self.prefix_text = toga.Label("Add an optional prefix to your output files' names.", style=large_font)
        #self.visualization.add(self.prefix_text)
        self.prefix = toga.TextInput(
            placeholder="Optional output file prefix", style=large_font
        )
        self.visualization.add(self.prefix)
        
        #.top30_text = toga.Label("Generate a bar diagram with your top 30 domains and save it to your desktop as both a .svg and a .gexf file.", style=large_font)
        #self.visualization.add(self.top30_text)
        self.visualization.add(
            toga.Button("Show top 30 domains", style=large_font, on_press=self.top30)
        )

        
        #self.weightednetwork_text = toga.Label("Generate a weighted network and save it to your desktop as both a .html and a .gexf file.", style=large_font)
        #self.visualization.add(self.weightednetwork_text)
        self.visualization.add(
            toga.Button("Create weighted network", style=large_font, on_press=self.create_networks)
        )

        self.main_window.content = self.visualization

    def toscreen2(self,button):
        self.main_window.size=(1350, 768)
        self.main_window.content = self.screen2

    def toscreen3(self,button):
        self.main_window.size = (500,500)
        self.viswindow()
    
    def tomenu(self,button):
        self.main_window.size = (500,500)
        self.main_window.content = self.menu


    def create_export(self, button):
        data = {
            "domains": {},
            "browsers": self.browsers,
            "days": self.days,
            "times": self.times,
            "participant_code": self.pseudonym.value,
        }
        i = 0
        history = self.history
        for row in self.unmasked_data:
            if row["domain"] in self.hidden_domains:
                key = f"[hidden_{i}]"
                history["domain"].replace(
                    to_replace=row["domain"], value=f"[hidden_{i}]", inplace=True
                )
                i += 1
            elif row["domain"] == "":
                key = "N/A"
            else:
                key = str(row["domain"])
            data["domains"][key] = row["visits"]

        if button.id == "preview":
            try:
                for i in range(len(self.preview.children)):
                    self.preview.remove(self.preview.children[0])
            except IndexError:
                pass
            self.preview.add(
                toga.MultilineTextInput(
                    value=str(yaml.dump(data)), readonly=True, style=small_font_flex
                )
            )

            self.preview.add(
                toga.MultilineTextInput(
                    value=history.to_string(index=False, header=["Time", "Domain"]),
                    readonly=True,
                    style=small_font_flex,
                )
            )
            self.preview.add(toga.Label("Only exactly this data will be saved."))
            self.preview.add(self.export_button())
            # self.preview.refresh()

        self.data = data

    def preview_button(self):
        button = toga.Button(
            "Preview",
            id="preview",
            style=large_font,
            on_press=self.create_export,
        )
        return button

    async def upload(self,button):
        folderchoice = self.main_window.select_folder_dialog("Choose a folder to save your files in", initial_directory=None, multiple_select=False, on_result=None, multiselect=None)
        self.folderpath = await folderchoice
        history_path = self.folderpath.joinpath(str(self.pseudonym.value)+"_web_histopy_history.csv")
        data_path = self.folderpath.joinpath(str(self.pseudonym.value)+"_web_histopy_stats.yaml")

        self.history.to_csv(history_path, header=["Time", "Domain"], index=False)
        with open(data_path, "w") as f:
            yaml.dump(self.data, f)

        self.main_window.info_dialog(
            "Successfully created Webhistopy file",
            textwrap.dedent(
                f"""\
                The Webhistopy file has been created and saved to your desktop.
                """
            ),
        )

    """def upload(self, button):
        home = expanduser("~")
        history_path = Path(home).joinpath("Desktop",str(self.pseudonym.value)+"_web_histopy_history.csv")
        data_path = Path(home).joinpath("Desktop",str(self.pseudonym.value)+"_web_histopy_stats.yaml")

        self.history.to_csv(history_path, header=["Time", "Domain"], index=False)
        with open(data_path, "w") as f:
            yaml.dump(self.data, f)

        self.main_window.info_dialog(
            "Successfully created Webhistopy file",
            textwrap.dedent(
                f""""""\
                The Webhistopy file has been created and saved to your desktop.
                """"""
            ),
        )"""

    def export_button(self):
        button = toga.Button("Save to Desktop", style=large_font, on_press=self.upload)
        return button

    def toggle_domain(self, switch):
        domain = switch.text
        if domain not in self.hidden_domains:
            self.hidden_domains.append(domain)
        else:
            self.hidden_domains.remove(domain)
        print(self.hidden_domains)

    def domain_switch(self, domain):

        return toga.Switch(text=domain, on_change=self.toggle_domain, style=switch_font)

    def domain_check_list(self, data):

        check_list = toga.Box(style=Pack(direction=COLUMN))

        for item in data:
            if item["domain"] != "[hidden]":
                check_list.add(self.domain_switch(item["domain"]))

        return toga.ScrollContainer(content=check_list, style=Pack(flex=1))

    def show_histories(self, button):
        if len(self.browsers) == 0:
            self.main_window.error_dialog(
                "No selection", "Please select at least one browser."
            )
            return 1
        data = self.get_histories(self.browsers)

        try:
            for child in range(3):
                self.table_container.remove(self.table_container.children[0])
        except IndexError:
            pass

        self.table_container.add(
            toga.Label("Please select any domains you want to hide.", style=large_font)
        )

        self.hidden_domains = []
        self.table = self.domain_check_list(data)

        self.table_container.add(self.table)

        self.table_container.add(self.preview_button())

    def get_histories(self, browsers):
        self.time_limit = self.weeks.value
        output_df = pd.DataFrame(columns=["domain", "visits"])

        for browser in browsers:
            Browser = browser_history.utils.get_browser(browser)
            try:
                b = Browser()
            except TypeError:
                self.main_window.error_dialog(
                    "Not supported",
                    textwrap.dedent(
                        f"""\
                        {browser} is not supported by your operating system.
                        If you do have this browser installed and regularly use it, \
                        please contact the developers. Otherwise, please deselect the browser.

                        """
                    ),
                )
                continue
            try:
                output = b.fetch_history()
            except PermissionError:
                if isinstance(b, Safari):
                    webbrowser.open(
                        "x-apple.systempreferences:com.apple.preference.security?Privacy"
                    )
                    sleep(1)
                    subprocess.Popen(["open", "/Applications"])
                    sleep(1)
                    self.main_window.info_dialog(
                        "Moin!",
                        textwrap.dedent(
                            """\
                            Due to privacy reasons we need your permission to evaluate your Safari data.
                            Please change to the window which has just opened and follow the following steps:

                            1. Click the lock and enter your system password.
                            2. Select "full data access" in the menu on the left.
                            Aus Privatsphäre-Gründen benötigen wir Ihre Erlaubnis, Safari-Daten auszuwerten.
                            3. Pull your Webhistopy App from your "Apps" folder into the list on the right side.
                            4. Restart the app.

                            You will have the option to revise all of your data before it is saved.

                            Thanks a lot!"""
                        ),
                    )
                    raise

            history = output.histories

            df = pd.DataFrame(history)

            try:
                df = df[
                    df[0].dt.tz_localize(None)
                    > np.datetime64(
                        datetime.datetime.now()
                        - pd.to_timedelta(f"{self.time_limit}days")
                    )
                ]  # limit to last x days

                week_day_numbers = [self.day_map[day] for day in self.days]

                print(self.days)
                print(week_day_numbers)

                # limit to work_days
                df = df[df[0].dt.weekday.isin(week_day_numbers)]

                df = df[df[0].dt.hour < int(self.times["ends"])]
                # limit to times
                df = df[df[0].dt.hour > int(self.times["starts"])]

                print(df)

                df["domain"] = df[1].apply(lambda url: get_domain(url))
                output_df = pd.concat([output_df, df], ignore_index=True)

            except KeyError:
                self.main_window.error_dialog(
                    "No data",
                    textwrap.dedent(
                        f"""\
                        No data found for {browser}. 
                        If you do have this browser installed and regularly use it, \
                        please contact the developers. Otherwise, please deselect the browser.
                        """
                    ),
                )
                continue

        self.history = output_df[[0, "domain"]].sort_values(0)

        top_domains = output_df.value_counts("domain")

        top_df = top_domains
        # top_df = top_domains[top_domains >= self.visit_limiter.value]

        top_df = top_df.reset_index()
        top_df.columns = ["domain", "visits"]

        self.history["domain"][
            self.history["domain"].isin(
                top_df["domain"][top_df["visits"] <= self.visit_limiter]
            )
        ] = "[hidden]"

        top_df["domain"][top_df["visits"] <= self.visit_limiter] = "[hidden]"
        top_df["hide"] = False
        self.unmasked_data = top_df.to_dict("records")

        return self.unmasked_data


def main():
    return WebhistoPy()
