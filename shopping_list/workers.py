"""
Any Thread based work I do.
"""

import time

from PyQt5.QtCore import pyqtSignal, QObject

from shopping_list import builder, core

class StringMonitor(QObject):
    """
    Monitors a string.IO for changes.

    Parameters
    ----------
    monitor_str : io.StringIO
        The string to watch.
    """

    string_changed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.alive = True
        self.cur_len = len(core.LOG_STRING.getvalue())

    def run(self):
        """
        Periodically monitor the length of string.io
        if it changes, notify the main gui.
        """
        while self.alive:
            time.sleep(0.5)
            if core.LOG_STRING.closed:
                self.alive = False
                break
            value = core.LOG_STRING.getvalue()
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
    fn_callback : func, optional, default=None
        If provided will be passed through the finished signal.
    """

    finished = pyqtSignal(dict, dict, 'PyQt_PyObject')

    def __init__(self, sheet_names, out_file, ignored, fn_callback=None):
        super().__init__()
        self.sheet_names = sheet_names
        self.out_file = out_file
        self.ignored = ignored
        self.fn_callback = fn_callback

    def run(self):
        """
        Builds the shopping list on a thread.
        """
        food_items, recipes = builder.build(
            self.sheet_names, self.out_file, self.ignored)
        self.finished.emit(food_items, recipes, self.fn_callback)
