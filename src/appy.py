"""
Goal is to create a desktop app with tkinter for different web scrapers.
Each is going to be within it's own tab within the main window.
Includes error pop-ups.
"""

import tkinter as tk
from tkinter import filedialog
from tkinter import ttk
from tkinter import messagebox
from threading import Thread
import time
import requests
from bs4 import BeautifulSoup
import os
import webbrowser


class Style(ttk.Style):
    """
    Style class for the main window to use, yet to be implemented
    """
    def __init__(self):
        super().__init__()


class App(tk.Tk):
    """
    Main application window
    """
    # Icon path as a variable for popups etc. to use
    icon_path = os.path.dirname(os.getcwd())
    icon_path += "/Images/icon.ico"

    settings = {"padding": 5}

    def __init__(self):
        super().__init__()
        self.title("Scrapers Extravaganza")
        self.iconbitmap(App.icon_path)

        self.__mainMenu = tk.Menu(self)
        self.config(menu=self.__mainMenu)

        # File menu
        self.__fileMenu = tk.Menu(self.__mainMenu, tearoff=False)
        self.__mainMenu.add_cascade(label="File", menu=self.__fileMenu)
        self.__duunitoriMenu = tk.Menu(self.__fileMenu, tearoff=False)
        self.__fileMenu.add_cascade(label="Duunitori scraper", menu=self.__duunitoriMenu)
        self.__alkoMenu = tk.Menu(self.__fileMenu, tearoff=False)
        self.__fileMenu.add_cascade(label="Alko prices", menu=self.__alkoMenu)
        self.__toriMenu = tk.Menu(self.__fileMenu, tearoff=False)
        self.__fileMenu.add_cascade(label="Tori.fi", menu=self.__toriMenu)

        # Duunitori menu
        self.__duunitoriMenu.add_command(label="New search profile", command=DuunitoriScraper.openSettings)
        self.__duunitoriMenu.add_command(label="Open search profile", command=DuunitoriScraper.loadSearch)

        # TODO Implement help documentation
        # Main menu button for help
        self.__mainMenu.add_command(label="Help")

        # Notebook widget to use as tab control in the window
        self.__tabControl = ttk.Notebook(self)
        self.__tabControl.pack(expand=1, fill="both")

        # Create the 3 tabs and pass tab control for target refence
        self.__duunitoriScraper = DuunitoriScraper(self.__tabControl)
        self.__alko = AlkoScraper(self.__tabControl)
        self.__tori = ToriScraper(self.__tabControl)

        self.mainloop()


class Popup(tk.Toplevel):
    """
    Popup class for displaying possible errors (messageboxes make redunaant?)
    """
    def __init__(self, error_msg=""):
        super().__init__()
        self.wm_title("Error")

        self.__error_msg = tk.Label(self, text=error_msg)
        self.__error_msg.pack(pady=10, padx=10)

        self.__button = tk.Button(self, text="Okay", command=self.destroy)
        self.__button.pack(padx=10, pady=10)


class Tab(ttk.Frame):
    """
    Super class for tabs, inherits from ttk Frame widget. Basically handles the tab created as a frame into tab control
    """
    def __init__(self, target=None, name=None):
        super().__init__(target)
        target.add(self, text=name)


class DuunitoriScraper(Tab):
    # TODO implement default profiles or previous profiles or anything else
    profile = {"keywords": ["python"],
               "locations": ["salo"],
               "searchDesc": False,
               "includeAll": False
               }

    def __init__(self, target):
        super().__init__(target, "Duunitori Scraper")

        # TODO get rid of these
        self.__links = []
        self.__keywords = ["python"]

        # Frame for holding the job listings and it's scrollbar
        self.__resultFrame = tk.Frame(self)
        self.__resultFrame.grid(row=0, column=0, columnspan=3)

        # Treeview widget for holding all the found job listings
        self.__job_list = ttk.Treeview(self.__resultFrame)
        self.__job_list["columns"] = ("desc")
        self.__job_list.column("#0", width=100, minwidth=20)
        self.__job_list.column("desc", anchor="w", width=300)

        self.__job_list.heading("#0", text="Company")
        self.__job_list.heading("desc", text="Job description", anchor="w")

        # Include a scrollbar
        self.__scrollbar = ttk.Scrollbar(self.__resultFrame)
        # Set scrollbar to command job lists vertical view
        self.__scrollbar.configure(command=self.__job_list.yview)
        self.__job_list.configure(yscrollcommand=self.__scrollbar.set)
        # Pack 'em
        self.__scrollbar.pack(side="right", fill="y")
        self.__job_list.pack()

        # Event binding to make jobs in the job list clickable
        self.__job_list.bind("<Double-Button-1>", self.openLink)

        self.__startButton = tk.Button(self, text="Start", command=self.startScrape)
        self.__startButton.grid(row=1, column=0)

        # Create the cancel button, progress bar, and done label, but don't pack
        self.__page_counter = self.numOfPages()
        self.__progressbar = ttk.Progressbar(self, orient="horizontal", length=50,
                                             maximum=self.__page_counter, mode="determinate")

        self.__doneLabel = tk.Label(self, text="Done!")
        self.__cancelButton = tk.Button(self, text="Cancel", command=self.cancelSearch)

    @staticmethod
    def loadSearch():
        """
        Method for loading existing search profiles
        """
        # TODO error handling
        # Get the path for profiles folder
        path = os.path.dirname(os.getcwd()) + "/search_profiles"
        # Open file
        file = filedialog.askopenfile(mode="r", initialdir=path, title="Select search profile", filetypes=((".txt", "*.txt"),))
        if file:  # Only if a file was opened
            content = file.readlines()
            file.close()
            # First 3 splits lines to lists that contains the key: value pairs
            content = [line.split("=") for line in content]
            content = [[elem.strip("\n") for elem in line] for line in content]
            content = [[elem.split(",") for elem in line] for line in content]
            # Since the splits introduce unneccessary list layers into keywords, using some list comprehension to get rid of them
            keys = [[elem[0] for elem in inner_content][0] for inner_content in content]
            # Values are easy to fetch, just grab the latter data within and element
            values = [elem[1] for elem in content]
            # Zip makes keys and values into a tuple, that dict can make a dictionary from
            profile = dict(zip(keys, values))
            # Load the parsed profile into class variable
            DuunitoriScraper.profile = profile

    @staticmethod
    def openSettings():
        """
        Just a pass through
        """
        settingsWindow = DuunitoriScraperSettings()

    def cancelSearch(self):
        # TODO
        """
        Cancel the search
        """
        pass

    def numOfPages(self):
        """
        Method to get the number of pages to scrape based on keywords etc.
        """
        url = self.url()
        response = requests.get(url)
        soup = BeautifulSoup(response.content, "html.parser")
        page_counter = soup.find_all("a", class_="pagination__pagenum")
        page_counter = page_counter[-1]
        page_counter = str(page_counter)
        # Non-pythonic combination to get the final page number from the html element
        page_counter = page_counter.split("=")[-1].split('"')[0]
        page_counter = int(page_counter)
        return page_counter

    def startScrape(self):
        """
        Starts the scraping in another thread to allow windows to function relatively normally.
        """
        thread = Thread(target=self.scrape)
        thread.start()

    def scrape(self):
        # TODO UPDATE THIS
        """
        The actual scraping part.
        """
        # Set the first iid for the treeview
        iid = 0
        self.__progressbar.grid(row=1, column=2)
        for i in range(1, self.__page_counter + 1, 1):
            time.sleep(0.05)
            # Set url for given page number
            url = self.url() + "&sivu=" + str(i)
            # Fetch the site
            response = requests.get(url)
            # Turn it into soup using html parser
            soup = BeautifulSoup(response.content, "html.parser")
            # Find the element in which the search results reside
            results = soup.find_all("a", class_="job-box__hover gtm-search-result")
            for result in results:
                title = self.parseHref(result["href"])
                link = self.intoLink(result["href"])
                self.__links.append(link)
                self.__job_list.insert(parent="", index="end", iid=iid, text=result["data-company"], values=(title, ) )
                iid += 1
            self.__progressbar["value"] = i
            self.update_idletasks()
            self.__progressbar.update()
        # Once done
        self.__progressbar.grid_forget()
        self.__doneLabel.grid(row=1, column=2)

    def url(self):
        # TODO Update with scrape?
        """
        Method injects given keywords into url query. Also searches the description
        """
        if len(self.__keywords) != 0:
            url = "https://duunitori.fi/tyopaikat?haku=" + self.__keywords[0]
            if len(self.__keywords) > 1:
                for i in range(1, len(self.__keywords), 1):
                    print(i)
                    url += "%3B" + self.__keywords[i]
            url += "&search_also_descr=1"
            url += "&alue=helsinki"
        return url

    def parseHref(self, href):
        # TODO replace with getting the titles etc. from html instead of href. Href gives wacky results
        """
        Parse the href to display just the job title
        """
        href = href.split("/")
        href = href[-1]
        href = href.split("-")
        href = href[:-2]
        href[0] = href[0].capitalize()
        separator = " "
        href = separator.join(href)
        return href

    def intoLink(self, href):
        """
        Turn href into a link.
        """
        link = "https://www.duunitori.fi" + href
        return link

    def openLink(self, event):
        """
        Uses the webbrowser module to open clicked link
        """
        # Select iid based on item clicked. "Item" means the entire row and event.x and event.y just specify coordinates.
        iid = int((self.__job_list.identify("item", event.x, event.y)))
        # Links are saved in a list separate from the treeview, just use the iid from the treeview to select link
        url = self.__links[iid]
        webbrowser.open(url)


class DuunitoriScraperSettings(tk.Toplevel):
    """
    Settings for scraping -- widget used:
    -Number of keywords -- Combobox
    -Number of locations -- Combobox
    -Keywords -- Entries
    -Locations -- Entries
    -Search description? -- Checkbutton
    -Must include all keywords? -- Checkbutton
    """
    def __init__(self):
        super().__init__()
        # TODO Update some namings
        # Get padding value from class variable
        padding = App.settings["padding"]

        self.wm_title("Duunitori scraper settings")
        self.wm_iconbitmap(App.icon_path)

        # Entry field for keywords, they will need to be separated by commas, and spaces are parsed anyway.
        self.__keywordLabel = tk.Label(self, text="Keywords (Separated by commas) ")
        self.__keywordLabel.grid(row=1, column=0, padx=padding, pady=padding)
        self.__keywordEntry = tk.Entry(self, width=50)
        self.__keywordEntry.grid(row=1, column=1, padx=padding, pady=padding)

        # Identical to entry field for keywords, but for locations, eg. Cities
        self.__locationsLabel = tk.Label(self, text="Locations (Separated by commas)")
        self.__locationsLabel.grid(row=2, column=0, padx=padding, pady=padding)
        self.__locationsEntry = tk.Entry(self, width=50)
        self.__locationsEntry.grid(row=2, column=1, padx=padding, pady=padding)

        # Use tkinter boolean var as checkbutton variable
        self.__includeAllVar = tk.BooleanVar()
        self.__includeAllCheck = tk.Checkbutton(self, text="Must the result include all keywords?", variable=self.__includeAllVar)
        self.__includeAllCheck.grid(row=3, column=0, padx=padding, pady=padding)

        # Same as above
        self.__searchDescVar = tk.BooleanVar()
        self.__searchDescCheck = tk.Checkbutton(self, text="Also search job description?", variable=self.__searchDescVar)
        self.__searchDescCheck.grid(row=3, column=1, padx=padding, pady=padding)

        # Buttons for discarding made profile or saving it
        self.__discardButton = tk.Button(self, text="Discard changes", command=self.discard)
        self.__discardButton.grid(row=4, column=0, padx=padding, pady=padding)

        self.__saveButton = tk.Button(self, text="Save search", command=self.saveSearch)
        self.__saveButton.grid(row=4, column=1, padx=padding, pady=padding)

    def discard(self):
        """
        Load settings again from config file and destroy window
        (whole window doesn't affect the main tabs settings so just destroy?)
        """
        self.destroy()

    def saveSearch(self):
        # TODO tweak error handling?
        # TODO Check if splitting and joining back together makes sense?
        """
        Make sure all settings are up to date and then save new config and destroy window
        """
        try:
            # Comma is used as the separator
            separator = ","
            # Retrieves a list of words from keyword entry field
            keywords = self.extractEntries(self.__keywordEntry)
            # Join them back into a string together with key
            keywords = "keywords=" + separator.join(keywords) + "\n"
            # Same as above
            locations = self.extractEntries(self.__locationsEntry)
            locations = "locations=" + separator.join(locations) + "\n"
            # Save keys + and their boolean vars as a string
            searchDesc = "searchDesc=" + str(self.__searchDescVar.get()) + "\n"
            includeAll = "includeAll=" + str(self.__includeAllVar.get()) + "\n"

            # All into one list for writeLines()
            lines = [keywords, locations, searchDesc, includeAll]
        except Exception as e:  # Error is broad for now
            messagebox.showerror("Error", e)

        try:
            path = os.path.dirname(os.getcwd()) + "/search_profiles"
            file = filedialog.asksaveasfile(mode="w", initialdir=path, title="Save profile", defaultextension=".txt")
            if file:
                file.writelines(lines)
                file.close()
        except Exception as e:  # Error is broad for now
            messagebox.showerror("Error", e)
        finally:
            # Destroy window when done
            self.destroy()

    @staticmethod
    def extractEntries(entryField):
        """
        Take entryField as parameter to polymorp method.
        Get the string inside the entryField.
        Split with commas as separator.
        And clean up possible whitespaces.
        """
        entryString = entryField.get()
        entries = entryString.split(",")
        entries = [entry.strip(" ") for entry in entries]
        return entries


class AlkoScraper(Tab):
    # TODO Implement
    """
    Alko price/alcohol calculator tab
    """
    def __init__(self, target):
        super().__init__(target, "Alko")
        self.__job_list = ttk.Treeview(self)
        self.__job_list["columns"] = ("desc")
        self.__job_list.column("#0", width=80, minwidth=20)
        self.__job_list.column("desc", anchor="w", width=240)

        self.__job_list.heading("#0", text="Keyword")
        self.__job_list.heading("desc", text="Job description", anchor="w")

        # Include a scrollbar
        self.__scrollbar = ttk.Scrollbar(self)
        self.__scrollbar.pack(side="right", fill="y")
        self.__scrollbar.configure(command=self.__job_list.yview)
        self.__job_list.configure(yscrollcommand=self.__scrollbar.set)

        for i in range(30):
            self.__job_list.insert(parent="", index="end", iid=i, text="Python", values=("Job description here", ))  # Colon to make last column show correctly

        self.__job_list.pack()


class ToriScraper(Tab):
    # TODO Implement
    """
    Tori.fi scraper for finding the best deals on stools?
    """
    def __init__(self, target):
        super().__init__(target, "Tori.fi")


if __name__ == "__main__":
    app = App()
