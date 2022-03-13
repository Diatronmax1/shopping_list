"""
Main application window to create shopping lists from.
"""
import os
from pathlib import Path
import time

from PyQt5.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QWidget,
)
from PyQt5.QtGui import QTextCursor
from PyQt5.QtCore import pyqtSignal, QObject, QThread

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
            value = self.monitor_str.getvalue()
            if value != self.cur_len:
                self.string_changed.emit(value)
                self.cur_len = value

class ShoppingWorker(QObject):
    """
    Runs the main function of shopping list.

    Parameters
    ----------
    days : list
        List of days to run.
    out_file : Path
        The path to the output file.
    string_io : io.StringIO
        String to monitor for changes.

    """

    finished = pyqtSignal()

    def __init__(self, days, out_file, string_io):
        super().__init__()
        self.days = days
        self.out_file = out_file
        self.string_io = string_io

    def run(self):
        """
        Builds the shopping list on a thread.
        """
        shopping_list.main(self.days, self.out_file, self.string_io)
        self.finished.emit()

class MainWidget(QWidget):
    """
    Primary application entry point.

    Parameters
    ----------
    log_capture_string : io.StringIO
        A dynamic string that contains logging
        information, tied to the QTextEdit to display
        elements as logging is logged.

    """

    def __init__(self, string_io):
        super().__init__()
        self.setWindowTitle('Shopping List Creator')
        #Checkable days.
        days = ('Sunday',
            'Monday',
            'Tuesday',
            'Wednesday',
            'Thursday',
            'Friday',
            'Saturday')
        self.string_io = string_io
        self.button_group = QButtonGroup()
        self.button_group.setExclusive(False)
        for day in days:
            new_day = QCheckBox(day, self)
            self.button_group.addButton(new_day)
        #Name of the file.
        self.file_name = QLineEdit()
        self.file_name.setText('shopping_list')
        #Output directory.
        def_path = Path.home() / 'Desktop'
        self.output_dir = QLineEdit()
        self.output_dir.setText(str(def_path))
        self.status = QTextEdit()
        #Setup the string monitor.
        self.shop_thread = None
        self.shopping_worker = None
        self.mon_thread = None
        self.string_worker = None
        self.generate_list_but = QPushButton('Generate List')
        #Signals
        self.generate_list_but.clicked.connect(self.make_shopping_list)
        #Layout
        day_group = QGroupBox('Days')
        layout = QHBoxLayout(day_group)
        for button in self.button_group.buttons():
            button.setChecked(True)
            layout.addWidget(button)
        layout = QFormLayout(self)
        layout.addRow('Select Days', day_group)
        layout.addRow('FileName', self.file_name)
        layout.addRow('Output Directory', self.output_dir)
        layout.addRow('Status', self.status)
        layout.addWidget(self.generate_list_but)

    def update_status(self, new_value):
        """
        Updates the status editor with the new value.

        Parameters
        ----------
        new_value : str
            New status string.
        """
        self.status.setText(new_value)
        self.status.moveCursor(QTextCursor.End)
        self.status.ensureCursorVisible()

    def make_shopping_list(self):
        """
        Builds the shopping list when geenrate is chosen.
        """
        self.build_string_monitor()
        self.generate_list_but.setEnabled(False)
        days = {}
        for button in self.button_group.buttons():
            days[button.text().lower()] = button.isChecked()
        file_name = os.path.splitext(self.file_name.text())[0] + '.txt'
        out_dir = Path(self.output_dir.text())
        out_file = out_dir / file_name
        if not out_dir.exists():
            self.status.setText(f'Output dir does not exist! {out_dir}')
            return
        self.shop_thread = QThread()
        self.shopping_worker = ShoppingWorker(days, out_file, self.string_io)
        self.shopping_worker.moveToThread(self.shop_thread)
        self.shopping_worker.finished.connect(self.all_done)
        self.shop_thread.started.connect(self.shopping_worker.run)
        self.shop_thread.start()

    def build_string_monitor(self):
        """
        Creates the thread for the string worker
        and sets it to the log string.
        """
        self.mon_thread = QThread()
        self.string_worker = StringMonitor(self.string_io)
        self.string_worker.moveToThread(self.mon_thread)
        self.mon_thread.started.connect(self.string_worker.run)
        self.string_worker.string_changed.connect(self.update_status)
        self.mon_thread.start()

    def all_done(self):
        """
        Close the string monitor and re-enable the list
        generator.
        """
        self.string_worker.alive = False
        self.mon_thread.quit()
        self.mon_thread.wait()
        self.shop_thread.quit()
        self.shop_thread.wait()
        self.generate_list_but.setEnabled(True)
