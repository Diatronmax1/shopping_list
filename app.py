"""
Main application window to create shopping lists from.
"""
#pylint: disable=unspecified-encoding, invalid-name
import datetime as dt
from functools import partial
import os
from pathlib import Path
import time

from PyQt5.QtWidgets import (
    QAction,
    QButtonGroup,
    QCheckBox,
    QDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from PyQt5.QtGui import QTextCursor
from PyQt5.QtCore import pyqtSignal, QObject, QThread
import yaml

import shopping_list

#Prep for all Day -> datetime conversions.
DAYS = {}

def build_days():
    """
    Creates 7 days and adds them to the global
    DAYS dictionary.
    """
    global DAYS
    today = dt.date.today()
    for num in range(7):
        day = today + dt.timedelta(days=num)
        DAYS[day.strftime("%A")] = day

build_days()

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
    already_have : set
        A set of names that should be ignored.
    """

    finished = pyqtSignal()

    def __init__(self, sheet_names, out_file, string_io, already_have):
        super().__init__()
        self.sheet_names = sheet_names
        self.out_file = out_file
        self.string_io = string_io
        self.already_have = already_have

    def run(self):
        """
        Builds the shopping list on a thread.
        """
        shopping_list.main(
            self.sheet_names, self.out_file, self.string_io, self.already_have)
        self.finished.emit()

class HaveCheck(QCheckBox):
    """
    Subclassing the Checkbox to catch
    the right click events.

    """

    new_name = pyqtSignal(QCheckBox, str)
    remove_name = pyqtSignal(QCheckBox)

    def contextMenuEvent(self, event):
        """
        Handles the right click scenario for check boxes

        Parameters
        ==========
        event : QtGui.QContextMenuEvent
            The event.
        """
        con_menu = QMenu(self)
        new_name_act = con_menu.addAction("Change Name")
        remove_act = con_menu.addAction("Delete")
        action = con_menu.exec_(self.mapToGlobal(event.pos()))
        if action == new_name_act:
            text, ok_pressed = QInputDialog.getText(self,
                'Enter new name',
                'Name: ',)
            if text and ok_pressed:
                self.new_name.emit(self, text)
        elif action == remove_act:
            self.remove_name.emit(self)

class AlreadyHave(QDialog):
    """
    Widget that allows manipulation of the underlying
    ini file and can set and remove different names
    to be ignored.
    """

    MAX_ROWS = 10

    def __init__(self, parent, config_path):
        super().__init__(parent)
        self.setWindowTitle('Check boxes to modify values')
        self.config_path = config_path
        self.names = {}
        with open(self.config_path, 'rb') as y_file:
            self.names = yaml.load(y_file, yaml.Loader)['names']
        self.save_and_close = QPushButton('Save and Close')
        self.cancel_but = QPushButton('Cancel')
        self.create_new = QPushButton('New')
        self.create_new.clicked.connect(self.new_element)
        self.save_and_close.clicked.connect(self.accept)
        self.cancel_but.clicked.connect(self.reject)
        #Checkboxes.
        self.checks = QWidget()
        self.check_layout = QGridLayout(self.checks)
        for food, used in self.names.items():
            self.new_check(food, used)
        #Main Layout
        self.main_layout = QGridLayout(self)
        self.resize(400,400)
        self.refresh_layout()

    def refresh_layout(self):
        """
        Clears the main layout and rebuilds it.
        """
        for _ in range(self.main_layout.count()):
            layout_item = self.main_layout.takeAt(0)
            layout_item.widget().setParent(None)
        self.main_layout.addWidget(self.create_new,     0, 1)
        self.main_layout.addWidget(self.checks,         1, 0, 2, 1)
        self.main_layout.addWidget(self.cancel_but,     2, 0)
        self.main_layout.addWidget(self.save_and_close, 2, 1)

    def new_check(self, name, val):
        """
        Convenience method to add a new check box.

        Parameters
        ----------
        name : str
            Name of the new checkbox.
        val : bool
            Representing the state of the checkbox.
        """
        name_check = HaveCheck(name)
        name_check.setChecked(val)
        func = lambda:self.name_change(name, name_check.isChecked())
        name_check.clicked.connect(func)
        name_check.new_name.connect(self.modify_name)
        name_check.remove_name.connect(self.remove_name)
        #Compute what row and col this should be added to based on
        #the number of items in the layout.
        num_items = self.check_layout.count()
        row = num_items % self.MAX_ROWS
        col = num_items // self.MAX_ROWS
        self.check_layout.addWidget(name_check, row, col)

    def new_element(self):
        """
        Creates a widget to request the new name
        and modifies the layout to include the new checkbox.
        """
        text, ok_pressed = QInputDialog.getText(
            self,
            'Provide a name',
            'Name:')
        if text and ok_pressed:
            self.new_check(text, True)
            self.name_change(text, True)
        self.refresh_layout()

    def modify_name(self, widget, new_name):
        """
        Updates the name in the dictionary to the new
        one preserving the state.

        Parameters
        ----------
        widget : HaveCheck
            The widget to eliminate and replace.
        new_name : str
            The new name for the dictionary.
        """
        self.names.pop(widget.text())
        self.take_check(widget)
        self.new_check(new_name, widget.isChecked())
        self.name_change(new_name, widget.isChecked())
        self.refresh_layout()

    def take_check(self, widget):
        """
        Convenience method to handle removing a widget
        from a layout consistently.

        Parameters
        ----------
        widget : QWidget
            The widget to remove from the check layout.
        """
        idx = self.check_layout.indexOf(widget)
        self.check_layout.takeAt(idx)
        widget.setParent(None)

    def remove_name(self, widget):
        """
        Removes a name from config.

        Parameters
        ----------
        widget : HaveCheck
            The widget to delete.
        """
        self.names.pop(widget.text())
        self.take_check(widget)
        self.refresh_layout()

    def name_change(self, name, is_checked):
        """
        Modifies name in the internal config.

        Parameters
        ----------
        name : str
            Name of the value to update.
        is_checked : bool
            The state for the name.
        """
        self.names[name] = is_checked

    def accept(self):
        """
        Saves the cfg to the file.
        """
        with open(self.config_path, 'rb') as y_file:
            yml_dict = yaml.load(y_file, yaml.Loader)
            yml_dict['names'] = self.names
        with open(self.config_path, 'w') as y_file:
            yaml.dump(yml_dict, y_file, yaml.Dumper)
        super().accept()

class SheetData(QDialog):
    """
    Spawns when a sheet name button is pressed. Allows
    for fine control of days by sheet names.

    Parameters
    ----------
    parent : QWidget
        Parent widget, should contain the config path.
    sheet_name : str
        The name of the sheet to modify.

    """

    def __init__(self, parent, sheet_name):
        super().__init__(parent)
        self.sheet_name = sheet_name
        self.sheets = self.parent().get_sheet_data()
        self.current_sheet = self.sheets[self.sheet_name]
        layout = QFormLayout(self)
        layout.addRow('Editing Sheet', QLabel(sheet_name))
        used_days = {day.strftime("%A") for day in self.current_sheet}
        self._checks = []
        for day in DAYS:
            new_check = QCheckBox(day)
            if not any(used_days) or day in used_days:
                new_check.setChecked(True)
            layout.addWidget(new_check)
            self._checks.append(new_check)
        save_but = QPushButton('Save')
        save_but.clicked.connect(self.accept)
        layout.addWidget(save_but)

    def accept(self):
        """
        Accepts and saves and closes the yaml.
        """
        #Convert the sheets data to yaml format.
        use_all = True
        for check in self._checks:
            use_all &= check.isChecked()
            if check.isChecked():
                self.current_sheet.add(DAYS[check.text()])
        #Clear them all if using them all.
        if use_all:
            self.current_sheet.clear()
        #Update the current sheet.
        save_sheets = {}
        for sheet_name, used_days in self.sheets.items():
            save_sheets[sheet_name] = [day.strftime('%A') for day in used_days]
        with open(self.parent().PATH, 'rb') as y_file:
            cur_yml = yaml.load(y_file, yaml.Loader)
            cur_yml['sheets'] = save_sheets
        with open(self.parent().PATH, 'w') as y_file:
            yaml.dump(cur_yml, y_file, yaml.Dumper)
        super().accept()

class MainWidget(QMainWindow):
    """
    Primary application entry point.

    Parameters
    ----------
    log_capture_string : io.StringIO
        A dynamic string that contains logging
        information, tied to the QTextEdit to display
        elements as logging is logged.

    """

    PATH = Path('config.yml')

    def __init__(self, string_io):
        super().__init__()
        self.setWindowTitle('Shopping List Creator')
        self.check_config()
        with open(self.PATH, 'rb') as y_file:
            cfg_dict = yaml.load(y_file, yaml.Loader)
        self._threaded = cfg_dict['threaded']
        #Checkable days.
        self.already_haves = None
        already_have_act = QAction('Edit Already Haves', self)
        already_have_act.triggered.connect(self.edit_already_haves)
        threaded_act = QAction('Threaded', self)
        threaded_act.setCheckable(True)
        threaded_act.setChecked(self._threaded)
        threaded_act.toggled.connect(self.change_threaded_state)
        file_menu = self.menuBar().addMenu('File')
        file_menu.addAction(already_have_act)
        edit_menu = self.menuBar().addMenu('Edit')
        edit_menu.addAction(threaded_act)
        self.string_io = string_io
        self.button_group = QButtonGroup()
        self.button_group.setExclusive(False)
        for day in DAYS.values():
            new_check = QCheckBox(day.strftime('%A (%m/%d)'), self)
            self.button_group.addButton(new_check)
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
        #Contains sheet names and sets.
        self.generate_list_but = QPushButton('Generate List')
        apply_all_but = QPushButton('Apply To All Sheets')
        #Signals
        self.generate_list_but.clicked.connect(self.make_shopping_list)
        apply_all_but.clicked.connect(self.update_all_sheet_data)
        #Layout
        day_group = QGroupBox('Days')
        layout = QHBoxLayout(day_group)
        for button in self.button_group.buttons():
            button.setChecked(True)
            layout.addWidget(button)
        layout.addWidget(apply_all_but)
        sheet_group = QGroupBox('Sheets')
        layout = QHBoxLayout(sheet_group)
        for sheet_name in self.get_sheet_data():
            new_button = QPushButton(sheet_name)
            new_button.clicked.connect(partial(self.edit_sheet_data, sheet_name))
            layout.addWidget(new_button)
        name_line = QWidget()
        layout = QHBoxLayout(name_line)
        layout.addWidget(QLabel('File name'))
        layout.addWidget(self.file_name)
        out_line = QWidget()
        layout = QHBoxLayout(out_line)
        layout.addWidget(QLabel('Output Directory'))
        layout.addWidget(self.output_dir)
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(day_group)
        layout.addWidget(sheet_group)
        layout.addWidget(name_line)
        layout.addWidget(out_line)
        layout.addWidget(QLabel('Status'))
        layout.addWidget(self.status)
        layout.addWidget(self.generate_list_but)
        self.setCentralWidget(widget)
        self.edit_already_haves()

    def change_threaded_state(self, state):
        """
        Modifies the threaded state.
        """
        self._threaded = state
        with open(self.PATH, 'rb') as y_file:
            yaml_dict = yaml.load(y_file, yaml.Loader)
            yaml_dict['threaded'] = self._threaded
        with open(self.PATH, 'w') as y_file:
            yaml_dict = yaml.dump(yaml_dict, y_file, yaml.Dumper)

    def edit_sheet_data(self, sheet_name):
        """
        Called when a button is pressed in the GUI spawns
        the sheet editor.
        """
        dialog = SheetData(self, sheet_name)
        dialog.open()

    def update_all_sheet_data(self):
        """
        Casts all data from the main gui to each sheet name in the
        configuration.
        """
        result = QMessageBox.information(
            self,
            'Update All',
            'Warning this will update all current user sheet days!',
            QMessageBox.Ok | QMessageBox.Cancel,
            QMessageBox.Ok
            )
        if result == QMessageBox.Cancel:
            return
        #Now go through and update all sheet data to match
        #the current buttons.
        sheets = self.get_sheet_data()
        fmt_days = {day.strftime('%A (%m/%d)'):day.strftime("%A") for day in DAYS.values()}
        update_days = set()
        use_all = True
        for button in self.button_group.buttons():
            if button.isChecked():
                update_days.add(fmt_days[button.text()])
            else:
                use_all = False
        if use_all:
            update_days.clear()
        #Now go over each sheet and reset their data.
        for sheet_name in sheets:
            sheets[sheet_name] = list(update_days)
        #Now convert for writing.
        with open(self.PATH, 'r') as y_file:
            yml_dict = yaml.load(y_file, yaml.Loader)
            yml_dict['sheets'] = sheets
        with open(self.PATH, 'w') as y_file:
            yaml.dump(yml_dict, y_file, yaml.Dumper)

    def check_for_keyfile(self):
        """
        Validates there is a key to connect to sheets.

        Raises
        ------
        FileNotFoundError
            When the keyfile isn't setup correctly.
        """
        keyfile = Path('pers_key.json')
        if not keyfile.exists():
            key_text, ok_pressed = QInputDialog.getText(self,
                'No Key File detected, create new',
                'Key:')
            if key_text and ok_pressed:
                with open(keyfile, 'w') as k_file:
                    k_file.write(key_text)
        if not keyfile.exists():
            raise FileNotFoundError('Must have a key file to continue!')

    def edit_already_haves(self):
        """
        Creates the widget to modify already haves.
        """
        self.already_haves = AlreadyHave(self.centralWidget(), self.PATH)
        self.already_haves.open()

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
        already_have = self.get_already_have()
        self.build_string_monitor()
        self.generate_list_but.setEnabled(False)
        file_name = os.path.splitext(self.file_name.text())[0] + '.txt'
        out_dir = Path(self.output_dir.text())
        out_file = out_dir / file_name
        if not out_dir.exists():
            self.status.setText(f'Output dir does not exist! {out_dir}')
            return
        self.shop_thread = QThread()
        sheet_data = self.get_sheet_data(True)
        if self._threaded:
            self.shopping_worker = ShoppingWorker(
                sheet_data, out_file, self.string_io, already_have)
            self.shopping_worker.moveToThread(self.shop_thread)
            self.shopping_worker.finished.connect(self.all_done)
            self.shop_thread.started.connect(self.shopping_worker.run)
            self.shop_thread.start()
        else:
            shopping_list.main(sheet_data, out_file, self.string_io, already_have)
            self.all_done()

    def get_sheet_data(self, ignore_used_days_empty=False):
        """
        Goes through the available sheet names and checks the
        states of their options.

        Parameters
        ----------
        ignore_used_days_empty : bool, optional, default=False
            Will treat an emtpy set of days as requesting
            all days, used mainly for normal shopping.
        """
        with open(self.PATH, 'rb') as y_file:
            yml_dict = yaml.load(y_file, yaml.Loader)
            sheets = yml_dict['sheets']
        fixed_sheets = {}
        for sheet_name, used_days in sheets.items():
            partial_days = set()
            if used_days:
                for day in used_days:
                    #Grab the day from the global dict.
                    partial_days.add(DAYS[day])
            elif ignore_used_days_empty:
                partial_days.update(day for day in DAYS.values())
            fixed_sheets[sheet_name] = partial_days
        #Then update the fixed sheets as the return.
        return fixed_sheets

    def check_config(self):
        """
        Validates the config path.
        """
        if not self.PATH.exists():
            self.create_default_config()

    def get_already_have(self):
        """
        Builds the already_have set from the ini file.

        Returns
        =======
        set
            The already have names that should be ignored.
        """
        already_have = set()
        with open(self.PATH, 'rb') as y_file:
            yml_dict = yaml.load(y_file, yaml.Loader)
        for name, use in yml_dict['names'].items():
            if use:
                already_have.add(name)
        return already_have

    def create_default_config(self):
        """
        Builds the default configuration file.
        """
        default_names = (
            'Chris Food Plan',
            "Melia's Food Plan",
            "Bryn's Food Plan")
        yml_dict = {
            'names': {},
            'sheets' : {name:None for name in default_names},
            'threaded':True,
        }
        with open(self.PATH, 'w') as y_file:
            yaml.dump(yml_dict, y_file)

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
        if self.string_worker:
            self.string_worker.alive = False
        self.mon_thread.quit()
        self.mon_thread.wait()
        self.shop_thread.quit()
        self.shop_thread.wait()
        self.generate_list_but.setEnabled(True)
