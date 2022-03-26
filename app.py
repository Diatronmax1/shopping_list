"""
Main application window to create shopping lists from.
"""
#pylint: disable=unspecified-encoding, invalid-name
from functools import partial
import os
from pathlib import Path


from PyQt5.QtWidgets import (
    QAction,
    QButtonGroup,
    QCheckBox,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from PyQt5.QtGui import QTextCursor
from PyQt5.QtCore import QThread
import yaml

import shopping_list
from already_have import AlreadyHave
from sheet_days import SheetDay
from core import DAYS
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

    PATH = Path('config.yml')

    def __init__(self, string_io):
        super().__init__()
        self.setWindowTitle('Shopping List Creator')
        self.check_config()
        with open(self.PATH, 'rb') as y_file:
            cfg_dict = yaml.load(y_file, yaml.Loader)
        self._threaded = cfg_dict['threaded']
        self.already_haves = None
        self.make_menu()
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
        file_name = os.path.splitext(self.file_name.text())[0] + '.txt'
        out_dir = Path(self.output_dir.text())
        out_file = out_dir / file_name
        if not out_dir.exists():
            QMessageBox.information(self, 'Open File', f'{out_file} does not exist!')
            return
        os.startfile(out_file)

    def open_dynamic_sheet(self):
        """
        Tries to open the dynamic sheet if one is currently active from a generate sheet
        or possibly loadable from the output text results.
        """
        print('open dynamic sheet')

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
        dialog = SheetDay(self, sheet_name)
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
        ignored = self.get_already_have()
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
                sheet_data, out_file, self.string_io, ignored)
            self.shopping_worker.moveToThread(self.shop_thread)
            self.shopping_worker.finished.connect(self.all_done)
            self.shop_thread.started.connect(self.shopping_worker.run)
            self.shop_thread.start()
        else:
            shopping_list.main(sheet_data, out_file, self.string_io, ignored)
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
