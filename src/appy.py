"""
Goal is to create a desktop app with tkinter for different web scrapers.
Each is going to be within it's own tab within the main window.
Includes error pop-ups.
"""

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox


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
    def __init__(self):
        self.__root = tk.Tk()
        self.__root.title("Scraper")

        self.__tabControl = ttk.Notebook(self.__root)
        self.__tabControl.pack(expand=1, fill="both")

        self.__jobFinder = JobFinder(self.__tabControl)  # pass tabControl as target object
        self.__alko = AlkoScraper(self.__tabControl)

        self.__root.mainloop()


class Popup(tk.Toplevel):
    """
    Popup class for displaying possible errors
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

        self.__label1 = tk.Label(self, text="Select which sites to scrape")
        self.__label1.grid(row=0, column=0, columnspan=2, pady=self.__PADDING, padx=self.__PADDING)

        self.__check_duunitori = tk.Checkbutton(self, text="Duunitori")
        self.__check_duunitori.grid(row=1, column=0, pady=self.__PADDING, padx=self.__PADDING)

        self.__check_monster = tk.Checkbutton(self, text="Monster")
        self.__check_monster.grid(row=1, column=1, pady=self.__PADDING, padx=self.__PADDING)

        self.__label2 = tk.Label(self, text="Number of keywords: ")
        self.__label2.grid(row=2, column=0, pady=self.__PADDING, padx=self.__PADDING)

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
        except Exception:
            messagebox.showerror("Error", "Invalid input")
        else:
            for i in range(num_of_entries):
                entry = tk.Entry(self)
                entry.grid(row=i+4, column=0, columnspan=3, pady=self.__PADDING, padx=self.__PADDING)
                self.__entries.append(entry)
        finally:
            # Clear existing button
            if self.getSearchButton() != None:
                self.__search_button.destroy()
            self.__search_button = tk.Button(self, text="Search", command=self.scrape)
            self.__search_button.grid(row=4 + num_of_entries, column=0, columnspan=3, pady=self.__PADDING, padx=self.__PADDING)

    def scrape(self):
        print("test")

    def comboCallback(self, event): # even if event is not used, it must be placed since combobox callback gives it Initi
        self.addEntries()

    def getSearchButton(self) -> object:
        return self.__search_button


class AlkoScraper(Tab):
    """
    Alko price/alcohol calculator tab
    """
    def __init__(self, target):
        super().__init__(target, "Alko")


if __name__ == "__main__":
    app = App()
