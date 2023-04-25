"""
Provides widgets for editing days for individual
sheet users.
"""
#pylint: disable=unspecified-encoding
import os

from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import (
    QAction,
    QCheckBox,
    QDialog,
    QFormLayout,
    QGridLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
)
import yaml

from shopping_list import CFG_PATH, DAYS

def get_sheets():
    """
    Retrieves sheets from the config file.
    """
    with open(CFG_PATH, 'rb') as y_file:
        return yaml.load(y_file, yaml.Loader)['sheets']

def write_sheets(names):
    """
    Writes names dictionary to the yaml.

    Parameters
    ----------
    path : Path
        Path to the config file.
    names : dict
        The new names dictionary.
    """
    with open(CFG_PATH, 'rb') as y_file:
        yml_dict = yaml.load(y_file, yaml.Loader)
        yml_dict['sheets'] = names
    with open(CFG_PATH, 'w') as y_file:
        yaml.dump(yml_dict, y_file, yaml.Dumper)

def get_sheet_data():
    """
    Goes through the available sheet names and checks the
    states of their options.

    Parameters
    ----------
    ignore_used_days_empty : bool, optional, default=False
        Will treat an emtpy set of days as requesting
        all days, used mainly for normal shopping.

    Returns
    -------
    dict
        Names of sheets and used days that match the globals.
    """
    sheets = get_sheets()
    fixed_sheets = {}
    for sheet_name, used_days in sheets.items():
        partial_days = set()
        if used_days:
            for day in used_days:
                #Grab the day from the global dict.
                partial_days.add(DAYS[day])
        fixed_sheets[sheet_name] = partial_days
    #Then update the fixed sheets as the return.
    return fixed_sheets

def sheets_with_daystrings():
    """
    Retrieves the day string for sheets.

    Returns
    -------
    dict
        Sheet names and strings for display.
    """
    day_strings = {}
    for sheet_name, used_days in get_sheet_data().items():
        if len(used_days) == 7:
            day_str = "full week"
        elif len(used_days) == 0:
            day_str = "off"
        else:
            day_str = f" {tuple([day.strftime('%a') for day in sorted(used_days)])}"
        day_strings[sheet_name] = f'{sheet_name} {day_str}'
    return day_strings

def update_named_sheet_data(sheet_name, used_days):
    """Sets an individual sheet to the new used days."""
    sheets = get_sheets()
    sheets[sheet_name] = list(used_days)
    with open(CFG_PATH, 'r') as y_file:
        yml_dict = yaml.load(y_file, yaml.Loader)
        yml_dict['sheets'] = sheets
    with open(CFG_PATH, 'w') as y_file:
        yaml.dump(yml_dict, y_file, yaml.Dumper)

class SheetNames(QDialog):
    """
    Widget that allows manipulation of the underlying
    ini file and can set and remove different names
    to be ignored.

    """

    def __init__(self, parent):
        super().__init__(parent)
        if os.name != 'nt':
            self.setWindowModality(Qt.WindowModal)
        self.setWindowTitle('Sheet Names')
        self.save_and_close = QPushButton('Save and Close')
        modify_act = QAction('Change Name?', self)
        remove_act = QAction('Remove?', self)
        self.cancel_but = QPushButton('Cancel')
        self.create_new = QPushButton('+')
        self.sheet_names = QListWidget()
        self.sheet_names.setContextMenuPolicy(Qt.ActionsContextMenu)
        self.sheet_names.addActions([modify_act, remove_act])
        self.sheet_names.itemDoubleClicked.connect(self.prompt_actions)
        for name in get_sheets():
            new_item = QListWidgetItem()
            new_item.setData(Qt.DisplayRole, name)
            self.sheet_names.addItem(new_item)
        #Signals.
        modify_act.triggered.connect(self.modify)
        remove_act.triggered.connect(self.remove)
        self.create_new.clicked.connect(self.new_item)
        self.save_and_close.clicked.connect(self.accept)
        self.cancel_but.clicked.connect(self.reject)
        #Checkboxes.
        layout = QGridLayout(self)
        msg = 'Add new items to be ignored (case-insensitive)\n'
        msg += 'Check or uncheck items to enable them as ignored\n'
        msg += 'Right click and delete or double click and answer prompt\n'
        layout.addWidget(QLabel(msg),         0, 0, 1, 2)
        layout.addWidget(self.create_new,     1, 1)
        layout.addWidget(self.sheet_names,  2, 0, 1, 2)
        layout.addWidget(self.save_and_close, 3, 0)
        layout.addWidget(self.cancel_but,     3, 1)

    def prompt_actions(self):
        """
        For mobile.
        """
        msg = QMessageBox(self)
        if os.name != 'nt':
            msg.setWindowModality(Qt.WindowModal)
        msg.setText('Modify Item')
        msg.setInformativeText('Name can change or item can be removed.')
        mod_but = msg.addButton('Modify Name', QMessageBox.AcceptRole)
        rem_but = msg.addButton('Remove', QMessageBox.DestructiveRole)
        msg.addButton('Cancel', QMessageBox.RejectRole)
        msg.exec()
        button = msg.clickedButton()
        if button == mod_but:
            self.modify()
        elif button == rem_but:
            self.remove()

    def check_name(self, name):
        """
        Verifies name is not already in list of
        items.
        """
        for row in range(self.sheet_names.count()):
            item = self.sheet_names.item(row)
            if name.lower() == item.data(Qt.DisplayRole).lower():
                QMessageBox.information(self, 'Names', f'{name} already in list!')
                return True
        return False

    def new_item(self):
        """
        Convenience method to add a new check box.

        Parameters
        ----------
        name : str
            Name of the new checkbox.
        val : bool
            Representing the state of the checkbox.
        """
        name, ok_pressed = QInputDialog.getText(self, 'New Item', 'Name: ')
        if name and ok_pressed:
            if self.check_name(name):
                return
            new_item = QListWidgetItem()
            new_item.setData(Qt.DisplayRole, name)
            self.sheet_names.addItem(new_item)

    def modify(self):
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
        item = self.sheet_names.currentItem()
        new_name, ok_pressed = QInputDialog.getText(
            self,
            f'New name for {item.data(Qt.DisplayRole)}',
            'New Name: '
        )
        if new_name and ok_pressed:
            if self.check_name(new_name):
                return
            item.setData(Qt.DisplayRole, new_name)

    def remove(self):
        """
        Removes a name from config.

        Parameters
        ----------
        widget : HaveCheck
            The widget to delete.
        """
        row = self.sheet_names.currentRow()
        item = self.sheet_names.takeItem(row)
        del item

    def accept(self):
        """
        Saves the cfg to the file.
        """
        names = {}
        for row in range(self.sheet_names.count()):
            item = self.sheet_names.item(row)
            name = item.data(Qt.DisplayRole)
            names[name] = []
        write_sheets(names)
        self.parent().reset_sheet_group_layout()
        super().accept()

class SheetDay(QDialog):
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

    update_name = pyqtSignal(str)

    def __init__(self, parent, sheet_name):
        super().__init__(parent)
        self.setWindowTitle(f'Editing {sheet_name}')
        if os.name != 'nt':
            self.setWindowModality(Qt.WindowModal)
        self.sheet_name = sheet_name
        self.sheets = get_sheet_data()
        self.current_sheet = self.sheets[self.sheet_name]
        layout = QFormLayout(self)
        layout.addRow('Editing Sheet', QLabel(sheet_name))
        used_days = {day.strftime("%A") for day in self.current_sheet}
        self._checks = []
        for day in DAYS:
            new_check = QCheckBox(day)
            if day in used_days:
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
        #Clear out the current_sheet to reset it.
        checked_days = [DAYS[check.text()] for check in self._checks if check.isChecked()]
        self.sheets[self.sheet_name] = checked_days
        #Reset the current sheets to names of the days of the week.
        for sheet in self.sheets:
            self.sheets[sheet] = [day.strftime('%A') for day in self.sheets[sheet]]
        with open(CFG_PATH, 'rb') as y_file:
            cur_yml = yaml.load(y_file, yaml.Loader)
            cur_yml['sheets'] = self.sheets
        with open(CFG_PATH, 'w') as y_file:
            yaml.dump(cur_yml, y_file, yaml.Dumper)
        day_strings = sheets_with_daystrings()
        self.update_name.emit(day_strings[self.sheet_name])
        super().accept()
