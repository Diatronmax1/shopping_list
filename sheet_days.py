"""
Provides widgets for editing days for individual
sheet users.
"""
#pylint: disable=unspecified-encoding
from PyQt5.QtWidgets import (
    QCheckBox,
    QDialog,
    QFormLayout,
    QLabel,
    QPushButton,
)
import yaml

from core import DAYS

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
