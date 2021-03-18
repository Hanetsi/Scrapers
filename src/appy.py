"""
Goal is to create a desktop app with tkinter for different web scrapers.
Each is going to be within it's own tab within the main window.
Includes error pop-ups.
"""

import tkinter as tk
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
    Style class for the main window to use
    """
    def __init__(self):
        super().__init__()


class App:
    """
    Main application window
    """
    icon_path = os.path.dirname(os.getcwd())
    icon_path += "/Images/icon.ico"

    def __init__(self):
        self.__root = tk.Tk()
        self.__root.title("Scrapers Extravaganza")
        self.__root.iconbitmap(App.icon_path)

        self.__tabControl = ttk.Notebook(self.__root)
        self.__tabControl.pack(expand=1, fill="both")

        self.__jobFinder = JobFinder(self.__tabControl)  # pass tabControl as target object
        self.__alko = AlkoScraper(self.__tabControl)
        self.__tori = ToriScraper(self.__tabControl)

        self.__root.mainloop()


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
    Super class for tabs, inherits from ttk Frame widget
    """
    def __init__(self, target=None, name=None):
        super().__init__(target)
        target.add(self, text=name)


class JobFinder(Tab):
    """
    Job finder tab
    """
    def __init__(self, target):
        super().__init__(target, "Job Finder")

        self.__PADDING = 5
        self.__keywords = []
        self.__entries = []
        self.__search_button = None
        self.__dt_check = tk.BooleanVar()
        self.__dt_check.set(True)
        self.__mn_check = tk.BooleanVar()

        self.__label1 = tk.Label(self, text="Select which sites to scrape")
        self.__label1.grid(row=0, column=0, columnspan=2,
                           pady=self.__PADDING, padx=self.__PADDING)

        self.__check_duunitori = tk.Checkbutton(self, text="Duunitori", variable=self.__dt_check)
        self.__check_duunitori.grid(row=1, column=0,
                                    pady=self.__PADDING, padx=self.__PADDING)

        self.__check_monster = tk.Checkbutton(self, text="Monster", variable=self.__mn_check)
        self.__check_monster.grid(row=1, column=1,
                                  pady=self.__PADDING, padx=self.__PADDING)

        self.__label2 = tk.Label(self, text="Number of keywords: ")
        self.__label2.grid(row=2, column=0,
                           pady=self.__PADDING, padx=self.__PADDING)

        self.__numberOfKeywords = ttk.Combobox(self, values=[i for i in range(1, 6)])
        self.__numberOfKeywords.grid(row=2, column=1)
        self.__numberOfKeywords.current(0)
        self.__numberOfKeywords.bind("<<ComboboxSelected>>", self.comboCallback)    # If selected by clicking
        self.__numberOfKeywords.bind("<Return>", self.comboCallback)                # Or pressing enter

    def addEntries(self):
        """
        Adds entries based on the number selected in self.__numberOfKeyWords.
        """
        num_of_entries = self.__numberOfKeywords.get()
        # Destroy existing widgets if there are any
        if len(self.__entries) != 0:
            for entry in self.__entries:
                entry.destroy()
        # try to convert entered value to an int for the for loop
        try:
            num_of_entries = int(num_of_entries)
        # A broad exception, doesn't really matter since it's only checking if input is valid
        except ValueError:
            messagebox.showerror("Error", "Couldn't convert input to integer")
        except:
            messagebox.showerror("Error", "Error")
        else:
            for i in range(num_of_entries):
                entry = tk.Entry(self)
                entry.grid(row=i+4, column=0, columnspan=3,
                           pady=self.__PADDING, padx=self.__PADDING)
                self.__entries.append(entry)
        finally:
            # Clear existing button
            if self.getSearchButton() is not None:
                self.__search_button.destroy()
            self.__search_button = tk.Button(self, text="Search", command=self.scrape)
            self.__search_button.grid(row=4 + num_of_entries, column=0, columnspan=3,
                                      pady=self.__PADDING, padx=self.__PADDING)
            self.__search_button.bind("<Return>", self.searchButtonCallback)

    def scrape(self):
        # Clear keywords
        self.__keywords = []
        # Get keywords from each entry
        for i in range(len(self.__entries)):
            keyword = self.__entries[i].get()
            self.__keywords.append(keyword)
        if self.__dt_check.get():
            Duunitoriscraper = DuunitoriScrape(self.__keywords)
        if self.__mn_check.get():
            Monsterscraper = MonsterScrape()

    def comboCallback(self, event):  # even if event is not used, it must be placed since combobox callback gives it Initi
        self.addEntries()

    def searchButtonCallback(self, event):
        self.scrape()

    def getSearchButton(self) -> object:
        return self.__search_button

    def getKWs(self):
        return self.__keywords


class DuunitoriScrape(tk.Toplevel):
    """
    Scraper for Duunitori.fi. More efficient way would be to insert keywords into query in url.
    But this is just done for learning more about scraping html.
    """
    def __init__(self, keywords):
        super().__init__()

        self.__keywords = keywords
        self.__links = []

        self.wm_title("Duunitori Scraper")
        self.wm_iconbitmap(App.icon_path)

        # Treeview widget for holding all the found job listings
        self.__job_list = ttk.Treeview(self)
        self.__job_list["columns"] = ("desc")
        self.__job_list.column("#0", width=100, minwidth=20)
        self.__job_list.column("desc", anchor="w", width=300)

        self.__job_list.heading("#0", text="Company")
        self.__job_list.heading("desc", text="Job description", anchor="w")

        # Include a scrollbar but dont pack it yet
        self.__scrollbar = ttk.Scrollbar(self)
        self.__scrollbar.configure(command=self.__job_list.yview)
        self.__job_list.configure(yscrollcommand=self.__scrollbar.set)

        self.__scrollbar.pack(side="right", fill="y")
        self.__job_list.pack()

        self.__job_list.bind("<Double-Button-1>", self.openLink)

        self.__page_counter = self.numOfPages()
        self.__progressbar = ttk.Progressbar(self, orient="horizontal", length=self.__page_counter*3,
                                             maximum=self.__page_counter, mode="determinate")
        self.__progressbar.pack()
        self.__cancelButton = tk.Button(self, text="Cancel")
        self.__cancelButton.pack()

        thread = Thread(target=self.fun)
        thread.start()

    def numOfPages(self):
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

    def fun(self):
        # Once this function is done, remove scrollbar and button and insert a scrollable treeview with hyperlink binding
        iid = 0
        for i in range(1, self.__page_counter + 1, 1):
            time.sleep(0.05)
            # Set url for given page number
            url = self.url() + "&sivu=" + str(i)
            print(url)
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
            self.__progressbar.pack()

        self.__progressbar.destroy()
        self.__cancelButton.destroy()

    def url(self):
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
        Turn href into a link
        """
        link = "https://www.duunitori.fi" + href
        return link

    def openLink(self, event):
        iid = int((self.__job_list.identify("item", event.x, event.y)))
        url = self.__links[iid]
        webbrowser.open(url)


class MonsterScrape(tk.Toplevel):
    def __init__(self):
        super().__init__()

        self.wm_title("Monster Scraper")
        self.__cancelButton = tk.Button(self, text="Cancel")
        self.__cancelButton.pack()


class AlkoScraper(Tab):
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
    """
    Tori.fi scraper for finding the best deals on stools?
    """
    def __init__(self, target):
        super().__init__(target, "Tori.fi")


if __name__ == "__main__":
    app = App()
