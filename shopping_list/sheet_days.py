"""
Provides widgets for editing days for individual
sheet users.
"""
#pylint: disable=unspecified-encoding
import os

from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import (
    QCheckBox,
    QDialog,
    QFormLayout,
    QLabel,
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

def get_sheet_data():
    """
    Goes through the available sheet names and checks the
    states of their options.

    Parameters
    ----------
    ignore_used_days_empty : bool, optional, default=False
        Will treat an emtpy set of days as requesting
        all days, used mainly for normal shopping.
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

def update_all_sheet_data(used_days):
    """
    Casts to the config file all of the used_days, or
    if use All, clears the config data.

    Parameters
    ----------
    used_days : set
        The datetimes of the days to use.
    use_all : bool
        Whether or not all days should be used.
    """
    sheets = get_sheet_data()
    for sheet_name in sheets:
        sheets[sheet_name] = list(used_days)
    #Now convert for writing.
    with open(CFG_PATH, 'r') as y_file:
        yml_dict = yaml.load(y_file, yaml.Loader)
        yml_dict['sheets'] = sheets
    with open(CFG_PATH, 'w') as y_file:
        yaml.dump(yml_dict, y_file, yaml.Dumper)

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
