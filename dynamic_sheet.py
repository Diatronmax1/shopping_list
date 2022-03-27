
"""
Provides a dynamic view of the shopping list with
some tied in features.
"""
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QDialog,
    QHeaderView,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QTableWidget,
    QTableWidgetItem,
)

from already_have import write_names, get_names
from shopping_list import build_groups

class DynamicSheet(QDialog):
    """
    Opens the Food Items from the created shopping
    list and presents them in a GUI. Allows some features
    like 'Add to AlreadyHaves' which will update the already
    haves with items to be ignored.
    """

    def __init__(self, parent, food_items):
        super().__init__(parent)
        self.setWindowTitle('Dynamic Sheet')
        self._scroll = QScrollArea()
        self.food_items = food_items
        self.shopping_groups = build_groups(self.food_items)
        num_rows = len(self.food_items) + len(self.shopping_groups)
        self.table_widget = QTableWidget(num_rows, 2)
        row = 0
        for group_name, group in self.shopping_groups.items():
            new_item = QTableWidgetItem(group_name)
            new_item.setBackground(QColor('green'))
            blank = QTableWidgetItem()
            blank.setBackground(QColor('green'))
            self.table_widget.setItem(row, 0, new_item)
            self.table_widget.setItem(row, 1, blank)
            row += 1
            for food in group:
                name_item = QTableWidgetItem(food.name)
                button_item = QTableWidgetItem('Add to Already Have')
                button_item.setData(Qt.UserRole, food)
                button_item.setCheckState(Qt.Unchecked)
                self.table_widget.setItem(row, 0, name_item)
                self.table_widget.setItem(row, 1, button_item)
                row += 1
        #Add the groups to the scroll area and set as the main widget.
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.table_widget)
        close_but = QPushButton('Close')
        close_but.clicked.connect(self.accept)
        main_layout.addWidget(close_but)
        self.resize(self.parent().size())
        #Set the table to stretch the first column.
        hoz_head = self.table_widget.horizontalHeader()
        hoz_head.setSectionResizeMode(0, QHeaderView.Stretch)
        hoz_head.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table_widget.cellClicked.connect(self.ignore_food)

    def ignore_food(self, row, col):
        """
        Should try to ignore this food for the user.
        """
        if col != 1:
            return
        cell = self.table_widget.item(row, col)
        if cell and cell.checkState() == Qt.Checked:
            return
        food = cell.data(Qt.UserRole)
        cell.setCheckState(Qt.Checked)
        names = get_names()
        names[food.name.lower()] = True
        write_names(names)
        self.parent()._shopping_list.pop(food.name)
