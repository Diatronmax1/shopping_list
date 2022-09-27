#!/usr/bin/env python3
"""
Main entry point for the shopping list application.
"""
import sys
from functools import partial
import os
import subprocess
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication,
    QAction,
    QButtonGroup,
    QCheckBox,
    QDialog,
    QGroupBox,
    QFormLayout,
    QFrame,
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
from shopping_list import (
    already_have,
    builder,
    sheet_days,
    workers,
)
from shopping_list.dynamic_sheet import DynamicSheet

class OptionalDisplay(QDialog):
    """
    If it fails to open with a text editor
    will display this with a scrollable window.
    """

    def __init__(self, parent, text):
        super().__init__(parent)
        if os.name != 'nt':
            self.setWindowModality(Qt.WindowModal)
        text_widget = QTextEdit()
        text_widget.setText(text)
        close_but = QPushButton('Close')
        close_but.clicked.connect(self.accept)
        layout = QVBoxLayout(self)
        layout.addWidget(text_widget)
        layout.addWidget(close_but)
        if shopping_list.get_bool('mobile'):
            self.resize(parent.size())

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

    def __init__(self):
        super().__init__()
        self.setWindowTitle('Shopping List Creator')
        with open(shopping_list.CFG_PATH, 'rb') as y_file:
            cfg_dict = yaml.load(y_file, yaml.Loader)
        self.wid_already_haves = None
        self.wid_sheet_names = None
        self.dynamic_sheet = None
        self._shopping_list = {}
        self._recipes = {}
        self.make_menu(cfg_dict)
        #Create button group for days.
        self.day_buttons = QButtonGroup()
        self.day_buttons.setExclusive(False)
        for day in shopping_list.DAYS.values():
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
        #Signals
        self.generate_list_but.clicked.connect(self.make_shopping_list)
        #Layout
        day_group = QGroupBox('Days')
        if cfg_dict['mobile']:
            layout = QVBoxLayout(day_group)
        else:
            layout = QHBoxLayout(day_group)
        for button in self.day_buttons.buttons():
            button.setChecked(True)
            #Connect its signal after.
            button.stateChanged.connect(self.update_all_sheet_data)
            layout.addWidget(button)
        self.sheet_day_buttons = QButtonGroup()
        self.sheet_day_buttons.setExclusive(False)
        self.sheet_group = QGroupBox('Sheets')
        sheet_layout = QVBoxLayout(self.sheet_group)
        self.create_sheet_widgets(sheet_layout)
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
        layout.addWidget(self.sheet_group)
        layout.addWidget(file_line)
        layout.addWidget(stat_line)
        layout.addWidget(self.status)
        #Set main.
        self.setCentralWidget(central_widget)

    def reset_sheet_group_layout(self):
        """Resets the sheets layout if renamed."""
        sheet_layout = self.sheet_group.layout()
        #Remove all widgets.
        for _ in range(sheet_layout.count()):
            item = sheet_layout.takeAt(0)
            item.widget().setParent(None)
        self.create_sheet_widgets(sheet_layout)

    def create_sheet_widgets(self, sheet_layout):
        """Builds the widgets for each sheet from the cfg file.

        Returns
        -------
        QGroupBox
            The widget to add to the layout.
        """
        for sheet_name, button_name in sheet_days.sheets_with_daystrings().items():
            new_button = QPushButton(button_name)
            on_off_but = QPushButton('On/Off')
            on_off_but.setCheckable(True)
            if 'full' in button_name:
                on_off_but.setChecked(True)
            on_off_but.setObjectName(button_name)
            on_off_but.clicked.connect(partial(self.update_full_sheet, sheet_name, on_off_but))
            new_button.clicked.connect(partial(self.edit_sheet_data, new_button, sheet_name))
            new_button.sheet_name = sheet_name
            self.sheet_day_buttons.addButton(new_button)
            but_wid = QWidget()
            button_layout = QHBoxLayout(but_wid)
            button_layout.addWidget(new_button)
            button_layout.addWidget(on_off_but)
            sheet_layout.addWidget(but_wid)

    def make_menu(self, cfg_dict):
        """
        Creates menus.

        Parameters
        ----------
        cfg_dict : dict
            The configuration settings.
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
        sheet_act = QAction('Sheets', self)
        edit_menu.addAction(sheet_act)
        #Developer Options
        threaded_act = QAction('Threaded', self)
        threaded_act.setCheckable(True)
        threaded_act.setChecked(cfg_dict['threaded'])
        mobile_act = QAction('Mobile', self)
        mobile_act.setCheckable(True)
        mobile_act.setChecked(cfg_dict['mobile'])
        dev_menu = self.menuBar().addMenu('Developer Options')
        dev_menu.addAction(threaded_act)
        dev_menu.addAction(mobile_act)
        #Tie signals.
        open_sheet_act.triggered.connect(self.open_shopping_list)
        open_dynamic_sheet_act.triggered.connect(self.open_dynamic_sheet)
        already_have_act.triggered.connect(self.edit_already_haves)
        sheet_act.triggered.connect(self.edit_sheets)
        threaded_act.toggled.connect(partial(shopping_list.change_bool, 'threaded', threaded_act))
        mobile_act.toggled.connect(partial(shopping_list.change_bool, 'mobile', mobile_act))

    def open_shopping_list(self):
        """
        Tries to open the shopping list if the path exists.
        """
        shop_file = self.get_outfile()
        if not shop_file.exists():
            QMessageBox.information(self, 'Open File', f'{shop_file} does not exist!')
            return
        try:
            if os.name == 'nt':
                os.startfile(shop_file)
            else:
                subprocess.Popen(['open', '-W', shop_file])
        except Exception as exc:
            print(exc)
            with open(shop_file, 'r') as s_file:
                shop_text = s_file.read()
            dialog = OptionalDisplay(self, shop_text)
            dialog.open()

    def open_dynamic_sheet(self):
        """
        Tries to open the dynamic sheet if one is currently active from a generate sheet
        or possibly loadable from the output text results.
        """
        if not any(self._shopping_list):
            generate_but = QPushButton('Generate')
            generate_but.clicked.connect(self.make_shopping_list)
            msg = 'Must have generated a sheet, generate one now?'
            result = QMessageBox.information(self,
                'Dynamic Sheet',
                msg,
                QMessageBox.Yes | QMessageBox.Cancel)
            if result == QMessageBox.Yes:
                self.make_shopping_list(self.open_dynamic_sheet)
            return
        self.dynamic_sheet = DynamicSheet(
            self,
            self._shopping_list,
            self._recipes)
        self.dynamic_sheet.open()

    def edit_sheet_data(self, button, sheet_name):
        """
        Called when a button is pressed in the GUI spawns
        the sheet editor.
        """
        dialog = sheet_days.SheetDay(self, sheet_name)
        dialog.update_name.connect(button.setText)
        dialog.open()

    def update_full_sheet(self, sheet_name, check_button):
        """When a reset button is pressed, set the sheet state to the new state."""
        if check_button.isChecked():
            used_days = set([day.strftime('%A') for day in shopping_list.DAYS.values()])
        else:
            used_days = set()
        sheet_days.update_named_sheet_data(sheet_name, used_days)
        day_strings = sheet_days.sheets_with_daystrings()
        for button in self.sheet_day_buttons.buttons():
            button.setText(day_strings[button.sheet_name])

    def update_all_sheet_data(self):
        """
        Casts all data from the main gui to each sheet name in the
        configuration.
        """
        #Find the relevant buttons by button name.
        fmt_days = {day.strftime('%A (%m/%d)'):day.strftime("%A") for day in shopping_list.DAYS.values()}
        update_days = set()
        for button in self.day_buttons.buttons():
            if button.isChecked():
                update_days.add(fmt_days[button.text()])
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
        if not shopping_list.check_keyfile():
            key_text, ok_pressed = QInputDialog.getText(self,
                'No Key File detected, create new',
                'Key:')
            if key_text and ok_pressed:
                shopping_list.change_keyfile(key_text)
        #Now if it still doesn't exist, crash.
        if not shopping_list.check_keyfile():
            raise FileNotFoundError('Must have a key file to continue!')

    def edit_already_haves(self):
        """
        Creates the widget to modify already haves.
        """
        self.wid_already_haves = already_have.AlreadyHave(self)
        self.wid_already_haves.open()

    def edit_sheets(self):
        """Creates a widget to modify sheet names."""
        self.wid_sheet_names = sheet_days.SheetNames(self)
        self.wid_sheet_names.open()

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
            with open(shopping_list.CFG_PATH, 'rb') as y_file:
                yml_dict = yaml.load(y_file, yaml.Loader)
                yml_dict['filename'] = file_name.name
                yml_dict['output_dir'] = out_dir.as_posix()
            with open(shopping_list.CFG_PATH, 'w') as y_file:
                yaml.dump(yml_dict, y_file, yaml.Dumper)
        return out_dir / file_name

    def make_shopping_list(self, fn_callback=None):
        """
        Builds the shopping list when geenrate is chosen.

        Parameters
        ----------
        fn_callback : func
            If provided, will be called at the end of making
            the shopping list.
        """
        with open(shopping_list.CFG_PATH, 'rb') as y_file:
            cfg_dict = yaml.load(y_file, yaml.Loader)
        ignored = already_have.get_ignored()
        self.build_string_monitor()
        self.generate_list_but.setEnabled(False)
        out_file = self.get_outfile(save_cfg=True)
        if not out_file.parent.exists():
            self.status.setText(f'Output dir {out_file.parent} does not exist!')
            return
        self.shop_thread = QThread()
        sheet_data = sheet_days.get_sheet_data()
        if cfg_dict['threaded']:
            self.shopping_worker = workers.ShoppingWorker(
                sheet_data, out_file, ignored, fn_callback)
            self.shopping_worker.moveToThread(self.shop_thread)
            self.shopping_worker.finished.connect(self.all_done)
            self.shop_thread.started.connect(self.shopping_worker.run)
            self.shop_thread.start()
        else:
            food_items, recipes = builder.build(sheet_data, out_file, ignored)
            self.all_done(food_items, recipes, fn_callback)

    def build_string_monitor(self):
        """
        Creates the thread for the string worker
        and sets it to the log string.
        """
        self.mon_thread = QThread()
        self.string_worker = workers.StringMonitor()
        self.string_worker.moveToThread(self.mon_thread)
        self.mon_thread.started.connect(self.string_worker.run)
        self.string_worker.string_changed.connect(self.update_status)
        self.mon_thread.start()

    def all_done(self, food_items, recipes, fn_callback=None):
        """
        Close the string monitor and re-enable the list
        generator.

        Parameters
        ----------
        food_items : dict
            Dictionary of food items.
        recipes : dict
            Recipes.
        fn_callback : func, optional, default=None
            If provided will be the last thing called.
        """
        self._shopping_list = food_items
        self._recipes = recipes
        if self.string_worker:
            self.string_worker.alive = False
        self.mon_thread.quit()
        self.mon_thread.wait()
        self.shop_thread.quit()
        self.shop_thread.wait()
        self.generate_list_but.setEnabled(True)
        if fn_callback:
            fn_callback()

def main():
    """
    Will create the application then
    return the exit status.

    Parameters
    ----------
    log_capture_string : io.StringIO
        A dynamic string that will contain
        the logging output.

    Returns
    -------
    int
        Exit code.
    """
    main_app = QApplication(sys.argv)
    window = MainWidget()
    window.show()
    window.check_for_keyfile()
    ret_code = main_app.exec_()
    shopping_list.LOG_STRING.close()
    return ret_code

if __name__ == '__main__':
    main()
