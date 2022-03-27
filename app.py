"""
Main application window to create shopping lists from.
"""
#pylint: disable=unspecified-encoding, invalid-name
from functools import partial
import os
import subprocess
from pathlib import Path

from PyQt5.QtWidgets import (
    QAction,
    QButtonGroup,
    QCheckBox,
    QGroupBox,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from PyQt5.QtGui import QTextCursor
from PyQt5.QtCore import QThread
import yaml

import shopping_list
import already_have
from dynamic_sheet import DynamicSheet
import sheet_days
from core import DAYS, CFG_PATH, check_keyfile, change_keyfile
from workers import StringMonitor, ShoppingWorker

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

    def __init__(self, string_io):
        super().__init__()
        self.setWindowTitle('Shopping List Creator')
        with open(CFG_PATH, 'rb') as y_file:
            cfg_dict = yaml.load(y_file, yaml.Loader)
        self._threaded = cfg_dict['threaded']
        self.already_haves = None
        self.dynamic_sheet = None
        self._shopping_list = {}
        self.string_io = string_io
        self.make_menu()
        #Create button group for days.
        self.day_buttons = QButtonGroup()
        self.day_buttons.setExclusive(False)
        for day in DAYS.values():
            new_check = QCheckBox(day.strftime('%A (%m/%d)'), self)
            self.day_buttons.addButton(new_check)
        #Name of the file.
        self.file_name = QLineEdit()
        self.file_name.setText(cfg_dict['filename'])
        #Output directory.
        def_path = Path(cfg_dict['output_dir']).expanduser()
        self.output_dir = QLineEdit()
        self.output_dir.setText(def_path.as_posix())
        self.status = QTextEdit()
        #Setup the string monitor.
        self.shop_thread = None
        self.shopping_worker = None
        self.mon_thread = None
        self.string_worker = None
        #Contains sheet names and sets.
        self.generate_list_but = QPushButton('Generate List')
        self.generate_list_but.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        apply_all_but = QPushButton('Apply To All Sheets')
        #Signals
        self.generate_list_but.clicked.connect(self.make_shopping_list)
        apply_all_but.clicked.connect(self.update_all_sheet_data)
        #Layout
        day_group = QGroupBox('Days')
        layout = QHBoxLayout(day_group)
        for button in self.day_buttons.buttons():
            button.setChecked(True)
            layout.addWidget(button)
        layout.addWidget(apply_all_but)
        sheet_group = QGroupBox('Sheets')
        layout = QVBoxLayout(sheet_group)
        self.sheet_day_buttons = QButtonGroup()
        self.sheet_day_buttons.setExclusive(False)
        for sheet_name, button_name in sheet_days.sheets_with_daystrings().items():
            new_button = QPushButton(button_name)
            #For now just manually settting it, bad practice maybe.
            new_button.sheet_name = sheet_name
            new_button.clicked.connect(partial(self.edit_sheet_data, new_button, sheet_name))
            self.sheet_day_buttons.addButton(new_button)
            layout.addWidget(new_button)
        #Main
        stat_line = QWidget()
        s_layout = QHBoxLayout(stat_line)
        s_layout.addWidget(QLabel('Status'))
        s_layout.addWidget(self.generate_list_but)
        file_line = QWidget()
        layout = QFormLayout(file_line)
        layout.addRow('File name', self.file_name)
        layout.addRow('Output Directory', self.output_dir)
        #Main Layout
        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)
        layout.addWidget(day_group)
        layout.addWidget(sheet_group)
        layout.addWidget(file_line)
        layout.addWidget(stat_line)
        layout.addWidget(self.status)
        #Set main.
        self.setCentralWidget(central_widget)

    def make_menu(self):
        """
        Creates menus.
        """
        #File Menu
        open_sheet_act = QAction('Open Shopping List', self)
        open_dynamic_sheet_act = QAction('Open Dynamic Shopping List', self)
        file_menu = self.menuBar().addMenu('File')
        file_menu.addAction(open_sheet_act)
        file_menu.addAction(open_dynamic_sheet_act)
        #Edit Menu
        already_have_act = QAction('Already Haves', self)
        edit_menu = self.menuBar().addMenu('Edit')
        edit_menu.addAction(already_have_act)
        #Developer Options
        threaded_act = QAction('Threaded', self)
        threaded_act.setCheckable(True)
        threaded_act.setChecked(self._threaded)
        dev_menu = self.menuBar().addMenu('Developer Options')
        dev_menu.addAction(threaded_act)
        #Tie signals.
        open_sheet_act.triggered.connect(self.open_shopping_list)
        open_dynamic_sheet_act.triggered.connect(self.open_dynamic_sheet)
        already_have_act.triggered.connect(self.edit_already_haves)
        threaded_act.toggled.connect(self.change_threaded_state)

    def open_shopping_list(self):
        """
        Tries to open the shopping list if the path exists.
        """
        shop_file = self.get_outfile()
        if not shop_file.exists():
            QMessageBox.information(self, 'Open File', f'{shop_file} does not exist!')
            return
        if os.name == 'nt':
            os.startfile(shop_file)
        else:
            subprocess.Popen(['open', '-W', shop_file])

    def open_dynamic_sheet(self):
        """
        Tries to open the dynamic sheet if one is currently active from a generate sheet
        or possibly loadable from the output text results.
        """
        if not any(self._shopping_list):
            QMessageBox.information(self,
                'Dynamic Sheet',
                'Must have an active sheet back from generate list',)
            return
        self.dynamic_sheet = DynamicSheet(self, self._shopping_list)
        self.dynamic_sheet.open()

    def change_threaded_state(self, state):
        """
        Modifies the threaded state.
        """
        self._threaded = state
        with open(CFG_PATH, 'rb') as y_file:
            yaml_dict = yaml.load(y_file, yaml.Loader)
            yaml_dict['threaded'] = self._threaded
        with open(CFG_PATH, 'w') as y_file:
            yaml_dict = yaml.dump(yaml_dict, y_file, yaml.Dumper)

    def edit_sheet_data(self, button, sheet_name):
        """
        Called when a button is pressed in the GUI spawns
        the sheet editor.
        """
        dialog = sheet_days.SheetDay(self, sheet_name)
        dialog.update_name.connect(button.setText)
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
        #Find the relevant buttons by button name.
        fmt_days = {day.strftime('%A (%m/%d)'):day.strftime("%A") for day in DAYS.values()}
        update_days = set()
        use_all = True
        for button in self.day_buttons.buttons():
            if button.isChecked():
                update_days.add(fmt_days[button.text()])
            else:
                use_all = False
        if use_all:
            update_days.clear()
        #Now go over each sheet and reset their data.
        sheet_days.update_all_sheet_data(update_days)
        #Then go update all the button names.
        day_strings = sheet_days.sheets_with_daystrings()
        for button in self.sheet_day_buttons.buttons():
            button.setText(day_strings[button.sheet_name])

    def check_for_keyfile(self):
        """
        Validates there is a key to connect to sheets.

        Raises
        ------
        FileNotFoundError
            When the keyfile isn't setup correctly.
        """
        if not check_keyfile():
            key_text, ok_pressed = QInputDialog.getText(self,
                'No Key File detected, create new',
                'Key:')
            if key_text and ok_pressed:
                change_keyfile(key_text)
        #Now if it still doesn't exist, crash.
        if not check_keyfile():
            raise FileNotFoundError('Must have a key file to continue!')

    def edit_already_haves(self):
        """
        Creates the widget to modify already haves.
        """
        self.already_haves = already_have.AlreadyHave(self)
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

    def get_outfile(self, save_cfg=False):
        """
        Retrieves the output file path.

        Parameters
        ----------
        save_cfg : bool, optional, default=False
            If true, will write the current filename
            and output_dir to the config file.
        """
        file_name = Path(self.file_name.text()).with_suffix('.txt')
        out_dir = Path(self.output_dir.text())
        if save_cfg:
            with open(CFG_PATH, 'rb') as y_file:
                yml_dict = yaml.load(y_file, yaml.Loader)
                yml_dict['filename'] = file_name.name
                yml_dict['output_dir'] = out_dir.as_posix()
            with open(CFG_PATH, 'w') as y_file:
                yaml.dump(yml_dict, y_file, yaml.Dumper)
        return out_dir / file_name

    def make_shopping_list(self):
        """
        Builds the shopping list when geenrate is chosen.
        """
        ignored = already_have.get_ignored()
        self.build_string_monitor()
        self.generate_list_but.setEnabled(False)
        out_file = self.get_outfile(save_cfg=True)
        if not out_file.parent.exists():
            self.status.setText(f'Output dir {out_file.parent} does not exist!')
            return
        self.shop_thread = QThread()
        sheet_data = sheet_days.get_sheet_data(True)
        if self._threaded:
            self.shopping_worker = ShoppingWorker(
                sheet_data, out_file, self.string_io, ignored)
            self.shopping_worker.moveToThread(self.shop_thread)
            self.shopping_worker.finished.connect(self.all_done)
            self.shop_thread.started.connect(self.shopping_worker.run)
            self.shop_thread.start()
        else:
            food_items, recipes = shopping_list.main(sheet_data, out_file, self.string_io, ignored)
            self.all_done(food_items, recipes)

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

    def all_done(self, food_items, recipes):
        """
        Close the string monitor and re-enable the list
        generator.
        """
        self._shopping_list = food_items
        if self.string_worker:
            self.string_worker.alive = False
        self.mon_thread.quit()
        self.mon_thread.wait()
        self.shop_thread.quit()
        self.shop_thread.wait()
        self.generate_list_but.setEnabled(True)
