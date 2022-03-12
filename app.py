"""
Main application window to create shopping lists from.
"""
import os
from pathlib import Path

from PyQt5.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QTextEdit,
    QWidget,
)

import shopping_list

class MainWidget(QWidget):
    """
    Primary application entry point.

    Parameters
    ----------
    parent : QObject, optional, default=None
        A parent object, but not neccesary.

    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Shopping List Creator')
        #Checkable days.
        days = ('Sunday',
            'Monday',
            'Tuesday',
            'Wednesday',
            'Thursday',
            'Friday',
            'Saturday')
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

    def make_shopping_list(self):
        """
        Builds the shopping list when geenrate is chosen.
        """
        days = {}
        for button in self.button_group.buttons():
            days[button.text().lower()] = button.isChecked()
        file_name = os.path.splitext(self.file_name.text())[0] + '.txt'
        out_dir = Path(self.output_dir.text())
        out_file = out_dir / file_name
        if not out_dir.exists():
            self.status.setText(f'Output dir does not exist! {out_dir}')
            return
        results = shopping_list.main(days, out_file)
        text = '\n'.join(results)
        self.status.setText(text)

class ShoppingList(QMainWindow):
    """
    Primary entry point.
    """
    def __init__(self):
        super().__init__()
        self.main_widget = MainWidget()
        self.setCentralWidget(self.main_widget)
