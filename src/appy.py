"""
Goal is to create a desktop app with tkinter for different web scrapers.
Each is going to be within it's own tab within the main window.
Includes error pop-ups.

TODO
Clean up code, maybe break down methods a bit?
Error handling
Styling
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

        # TODO Implement help documentation
        # Main menu button for help
        self.__mainMenu.add_command(label="Help", command=self.openHelp)

        # Notebook widget to use as tab control in the window
        self.__tabControl = ttk.Notebook(self)
        self.__tabControl.pack(expand=1, fill="both")

        # Create the 3 tabs and pass tab control for target reference
        self.__duunitoriScraper = DuunitoriScraper(self.__tabControl)
        self.__alko = AlkoScraper(self.__tabControl)
        self.__tori = ToriScraper(self.__tabControl)
        self.__reddit = RedditScraper(self.__tabControl)

        # Duunitori menu
        self.__duunitoriMenu.add_command(label="New search profile", command=DuunitoriScraper.openSettings)
        self.__duunitoriMenu.add_command(label="Open search profile", command=self.__duunitoriScraper.loadSearch)

        self.mainloop()

    @staticmethod
    def openHelp():
        Help()


class Tab(ttk.Frame):
    """
    Super class for tabs, inherits from ttk Frame widget. Basically passes the created tab into tab control
    """

    def __init__(self, target=None, name=None):
        super().__init__(target)
        target.add(self, text=name)


class DuunitoriScraper(Tab):
    stop_scrape = True
    iid = 0
    profile = {"keywords": [""],
               "locations": [""],
               "searchDesc": False,
               }

    def __init__(self, target):
        super().__init__(target, "Duunitori Scraper")

        # Frame for holding the job listings and it's scrollbar
        self.__resultFrame = tk.Frame(self)
        self.__resultFrame.pack(expand=True, fill="both")

        # Treeview widget for holding all the found job listings
        self.__job_list = ttk.Treeview(self.__resultFrame)
        self.__job_list["columns"] = ("location", "employer", "vatid", "field", "link")
        self.__job_list["displaycolumns"] = ("location", "employer", "vatid", "field")
        self.__job_list.column("#0", anchor="w", width=200, minwidth=20)
        self.__job_list.column("location", anchor="w", width=200)
        self.__job_list.column("employer", anchor="w", width=200)
        self.__job_list.column("vatid", anchor="center", width=100)
        self.__job_list.column("field", anchor="w", width=200)

        self.__job_list.heading("#0", text="Job title", anchor="w")
        self.__job_list.heading("location", text="Location", anchor="w")
        self.__job_list.heading("employer", text="Employer", anchor="w")
        self.__job_list.heading("vatid", text="VatID", anchor="center")
        self.__job_list.heading("field", text="Field", anchor="w")

        # Include a scrollbar
        self.__scrollbar = ttk.Scrollbar(self.__resultFrame)
        # Set scrollbar to command job lists vertical view
        self.__scrollbar.configure(command=self.__job_list.yview)
        self.__job_list.configure(yscrollcommand=self.__scrollbar.set)
        # Pack 'em
        self.__scrollbar.pack(side="right", fill="y")
        self.__job_list.pack(expand=True, fill="both")

        # Event binding to make jobs in the job list clickable
        self.__job_list.bind("<Double-Button-1>", self.openLink)

        # Use another frame for the rest of the widgets for easier resizing
        self.__bottomFrame = tk.Frame(self)
        self.__bottomFrame.pack(expand=True, fill="both")

        self.__keywordVar = tk.StringVar()
        self.updateKeywordLabel()
        self.__keywordLabel = tk.Label(self.__bottomFrame, textvariable=self.__keywordVar)
        self.__keywordLabel.grid(row=0, column=0, sticky="nsew")

        self.__locationVar = tk.StringVar()
        self.updateLocationLabel()
        self.__locationLabel = tk.Label(self.__bottomFrame, textvariable=self.__locationVar)
        self.__locationLabel.grid(row=0, column=1, sticky="nsew")

        self.__startButton = tk.Button(self.__bottomFrame, text="Start", command=self.startScrape)
        self.__startButton.grid(row=1, column=0, sticky="nsew")

        # Create the cancel button, progress bar, and done label, but don't pack
        self.__page_counter = self.numOfPages()
        self.__progressbar = ttk.Progressbar(self.__bottomFrame, orient="horizontal", length=50,
                                             maximum=self.__page_counter, mode="determinate")

        self.__doneLabel = tk.Label(self.__bottomFrame, text="Done!")
        self.__cancelButton = tk.Button(self.__bottomFrame, text="Cancel", command=self.cancelSearch)

        # Set the grid weights for rezising to work
        self.__bottomFrame.grid_columnconfigure(0, weight=1)
        self.__bottomFrame.grid_columnconfigure(1, weight=1)
        self.__bottomFrame.grid_rowconfigure(0, weight=1)
        self.__bottomFrame.grid_rowconfigure(1, weight=1)

    def loadSearch(self):
        """
        Method for loading existing search profiles.
        Loads the file and parses it, then updates the profile dictionary.
        """
        # TODO error handling
        # Get the path for profiles folder
        path = os.path.dirname(os.getcwd()) + "/search_profiles"
        # Open file
        file = filedialog.askopenfile(mode="r", initialdir=path, title="Select search profile",
                                      filetypes=((".txt", "*.txt"),))
        if file:  # Only if a file was opened
            content = file.readlines()
            file.close()
            # First 3 splits lines to lists that contains the key: value pairs
            content = [line.split("=") for line in content]
            content = [[elem.strip("\n") for elem in line] for line in content]
            content = [[elem.split(",") for elem in line] for line in content]
            # Since the splits introduce unnecessary list layers into keywords, using some list comprehension to get rid of them
            keys = [[elem[0] for elem in inner_content][0] for inner_content in content]
            # Values are easy to fetch, just grab the latter data within and element
            values = [elem[1] for elem in content]
            # Zip makes keys and values into a tuple, that dict can make a dictionary from
            profile = dict(zip(keys, values))
            # Load the parsed profile into class variable
            DuunitoriScraper.profile = profile
            self.updateKeywordLabel()
            self.updateLocationLabel()

    @staticmethod
    def openSettings():
        """
        Just a pass through
        """
        DuunitoriScraperSettings()

    def cancelSearch(self):
        # TODO
        """
        Cancel the search
        """
        DuunitoriScraper.stop_scrape = True
        print("Canceled search")
        self.__cancelButton.grid_forget()
        self.__startButton.grid(row=1, column=0, sticky="nsew")

    @staticmethod
    def numOfPages():
        """
        Method to get the number of pages to scrape based on keywords etc.
        Works by doing the initial search and locating the last page number from the bottom.
        """
        url = DuunitoriScraper.getUrl()
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
        DuunitoriScraper.stop_scrape = False
        self.__startButton.grid_forget()
        self.__cancelButton.grid(row=1, column=0, sticky="nsew")
        self.__page_counter = self.numOfPages()
        self.__progressbar.configure(maximum=self.__page_counter)
        self.__progressbar.grid(row=1, column=1, sticky="nsew")
        self.__scrapeThread = Thread(target=self.scrape)
        self.__scrapeThread.start()

    def scrape(self):
        """
        Goes through the results one by one, opening them, and extracting data in the info cell.
        eg. Location, business name, VatID, and field.
        Updates all the found data into the treeview, and stores links.
        Also updates the progress bar according to search page number.
        """
        # Set the first iid for the treeview
        iid = 0

        for i in range(1, self.__page_counter + 1, 1):
            if DuunitoriScraper.stop_scrape:
                break
            url = self.getUrl() + "&sivu=" + str(i)

            site = requests.get(url)
            soup = BeautifulSoup(site.content, "html.parser")
            results = soup.findAll("a", class_="job-box__hover gtm-search-result")

            for result in results:
                if DuunitoriScraper.stop_scrape:
                    break
                time.sleep(0.1)
                link = "https://duunitori.fi/" + result["href"]
                page = requests.get(link)
                page_soup = BeautifulSoup(page.content, "html.parser")
                title = page_soup.find("h1", class_="header__title").string
                info_cell = page_soup.find("div", class_="1/1 grid__cell info-listing")
                if info_cell is not None:
                    info_blocks = info_cell.findAll("div", class_="info-listing__block")

                    location = employer = vatid = field = "-"

                    for block in info_blocks:
                        heading = block.find("h4", class_="info-listing__heading").string
                        value_block = block.find("div", class_="info-listing__value")

                        if heading == "Työpaikan sijainti":
                            location = value_block.find("span").string
                        if heading == "Toiminimi":
                            employer = value_block.find("span").string
                        if heading == "Y-tunnus":
                            vatid = value_block.find("span").string
                        if heading == "Toimiala":
                            field = value_block.find("span").string

                    self.__job_list.insert(parent="", index="end", iid=iid, text=title,
                                           values=(location, employer, vatid, field, link))
                    iid += 1
            self.__progressbar["value"] = i
            self.update_idletasks()
            self.__progressbar.update()
        # Once done
        self.__progressbar.grid_forget()
        self.__doneLabel.grid(row=1, column=1, sticky="nsew")

    @staticmethod
    def getUrl():
        """
        Method injects given keywords and locations into url query.
        Also checks for "searchDesc".
        """
        url = "https://duunitori.fi/"
        kw_list = DuunitoriScraper.profile["keywords"]
        if len(kw_list) != 0:
            url += "tyopaikat?haku=" + kw_list[0]
            if len(kw_list) > 1:
                for i in range(1, len(kw_list), 1):
                    url += "%3B" + kw_list[i]

        loc_list = DuunitoriScraper.profile["locations"]
        if len(loc_list) != 0:
            url += "&alue=" + loc_list[0]
            if len(loc_list) > 1:
                for i in range(1, len(loc_list), 1):
                    url += "%3B" + loc_list[i]

        if DuunitoriScraper.profile["searchDesc"]:
            url += "&search_also_descr=1"

        return url

    def openLink(self, event):
        """
        Uses the webbrowser module to open clicked link
        """
        # Select iid based on item clicked. "Item" means the entire row and event.x and event.y just specify coordinates.
        iid = int((self.__job_list.identify("item", event.x, event.y)))
        # Links are saved in a list separate from the treeview, just use the iid from the treeview to select link
        item = self.__job_list.item(iid)
        url = item["values"][-1]
        webbrowser.open(url)

    def updateKeywordLabel(self):
        keywords = self.profile["keywords"]
        kw_string = ", ".join(keywords)
        self.__keywordVar.set("Keywords: " + kw_string)

    def updateLocationLabel(self):
        locations = self.profile["locations"]
        loc_string = ", ".join(locations)
        self.__locationVar.set("Locations: " + loc_string)


class DuunitoriScraperSettings(tk.Toplevel):
    """
    Settings for scraping -- widget used:
    -Number of keywords -- Combobox
    -Number of locations -- Combobox
    -Keywords -- Entries
    -Locations -- Entries
    -Search description? -- Checkbutton
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

        # Same as above
        self.__searchDescVar = tk.BooleanVar()
        self.__searchDescCheck = tk.Checkbutton(self, text="Also search job description?",
                                                variable=self.__searchDescVar)
        self.__searchDescCheck.grid(row=3, column=0, padx=padding, pady=padding)

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

            # All into one list for writeLines()
            lines = [keywords, locations, searchDesc]
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
    def extractEntries(entryfield):
        """
        Take entryField as parameter to polymorph method.
        Get the string inside the entryField.
        Split with commas as separator.
        And clean up possible whitespaces.
        """
        entryString = entryfield.get()
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


class ToriScraper(Tab):
    # TODO Implement
    """
    Tori.fi scraper for finding the best deals on stools?
    """

    def __init__(self, target):
        super().__init__(target, "Tori.fi")


class RedditScraper(Tab):
    # TODO Implement
    """
    Reddit scraper??
    """

    def __init__(self, target):
        super().__init__(target, "Reddit")


class Help(tk.Toplevel):
    def __init__(self):
        super().__init__()

        self.wm_title("Help")
        self.wm_iconbitmap(App.icon_path)

        self.__DuunitoriHelpFrame = tk.LabelFrame(self, text="Duunitori Scraper")
        self.__DuunitoriHelpFrame.pack(anchor="nw")

        self.__duunitori_help_text = "HOW TO USE:\n" \
                                     "You must first create and open a new search profile\n" \
                                     "or if you have an existing search profile, you can just open it.\n" \
                                     "\n" \
                                     "To create a new search profile:\n" \
                                     "1. Go to File -> Duunitori scraper -> New search profile\n" \
                                     "2. Enter the wanted search options\n" \
                                     "(Empty fields will search all, eg. empty location searches everywhere)\n" \
                                     "3. Click Save search\n" \
                                     "\n" \
                                     "To open an existing search profile:\n" \
                                     "1. Go to File -> Duunitori scraper -> Open search profile\n" \
                                     "2. Select the text file containing your search profile\n" \
                                     "3. Click Open\n" \
                                     "\n" \
                                     "After opening a search profile, your keywords and locations should\n" \
                                     "be visible bottom of the window. Then you can just press Start\n" \
                                     "to begin scraping. The results will show in your window.\n" \
                                     "You can click any result to open it in your default browser"
        self.__duunitori_help_label = tk.Label(self.__DuunitoriHelpFrame, text=self.__duunitori_help_text)
        self.__duunitori_help_label.pack(anchor="nw")


if __name__ == "__main__":
    app = App()
