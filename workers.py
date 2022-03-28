"""
Any Thread based work I do.
"""

import time

from PyQt5.QtCore import pyqtSignal, QObject

import shopping_list

class StringMonitor(QObject):
    """
    Monitors a string.IO for changes.

    Parameters
    ----------
    monitor_str : io.StringIO
        The string to watch.
    """

    string_changed = pyqtSignal(str)

    def __init__(self, monitor_str):
        super().__init__()
        self.monitor_str = monitor_str
        self.alive = True
        self.cur_len = len(self.monitor_str.getvalue())

    def run(self):
        """
        Periodically monitor the length of string.io
        if it changes, notify the main gui.
        """
        while self.alive:
            time.sleep(0.5)
            if self.monitor_str.closed:
                self.alive = False
                break
            value = self.monitor_str.getvalue()
            if value != self.cur_len:
                self.string_changed.emit(value)
                self.cur_len = value

class ShoppingWorker(QObject):
    """
    Runs the main function of shopping list.

    Parameters
    ----------
    sheet_names : dict
        Names of the sheets to load and the days
        to use from them.
    out_file : Path
        The path to the output file.
    string_io : io.StringIO
        String to monitor for changes.
    ignored : set
        A set of names that should be ignored.
    """

    finished = pyqtSignal(dict, dict)

    def __init__(self, sheet_names, out_file, string_io, ignored):
        super().__init__()
        self.sheet_names = sheet_names
        self.out_file = out_file
        self.string_io = string_io
        self.ignored = ignored

    def run(self):
        """
        Builds the shopping list on a thread.
        """
        food_items, recipes = shopping_list.main(
            self.sheet_names, self.out_file, self.string_io, self.ignored)
        self.finished.emit(food_items, recipes)
