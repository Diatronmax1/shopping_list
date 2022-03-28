
"""
Provides a dynamic view of the shopping list with
some tied in features.
"""
from functools import partial
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAction,
    QDialog,
    QGroupBox,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from already_have import write_names, get_names
from shopping_list import build_groups

class DynamicSheet(QDialog):
    """
    Opens the Food Items from the created shopping
    list and presents them in a GUI. Allows some features
    like 'Add to AlreadyHaves' which will update the already
    haves with items to be ignored.

    Parameters
    ----------
    parent : QWidget
        The parent widget that can be updated.
    food_items : set
        The food list back from the shopping list.
    recipes : list
        List of recipes in the food sheet.
    """

    def __init__(self, parent, food_items, recipes):
        super().__init__(parent)
        self.setWindowTitle('Dynamic Sheet')
        self._scroll = QScrollArea()
        self.food_items = food_items
        self.recipes = recipes
        self.cur_group = None
        self.shopping_groups = build_groups(self.food_items)
        self.recipe_list = QListWidget()
        ignore_recipe_act = QAction('Add to Already Have', self)
        ignore_recipe_act.triggered.connect(self.ignore_recipe)
        ignore_food_act = QAction('Add to Already Have', self)
        ignore_food_act.triggered.connect(self.ignore_food)
        #Build the recipe group.
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        recipe_group = QGroupBox('Recipes')
        layout = QVBoxLayout(recipe_group)
        layout.addWidget(self.recipe_list)
        list_policy = QSizePolicy(
            QSizePolicy.MinimumExpanding,
            QSizePolicy.MinimumExpanding)
        for recipe in self.recipes.values():
            recipe_item = QListWidgetItem()
            recipe_item.setData(Qt.DisplayRole, recipe.name)
            recipe_item.setData(Qt.UserRole, recipe)
            self.recipe_list.addItem(recipe_item)
            self.recipe_list.horizontalScrollBar().setStyleSheet("QScrollBar {height:0px;}")
            self.recipe_list.setSizePolicy(list_policy)
        self.recipe_list.setContextMenuPolicy(Qt.ActionsContextMenu)
        self.recipe_list.addAction(ignore_recipe_act)
        self.recipe_list.itemDoubleClicked.connect(self.double_click_recipe)
        main_layout.addWidget(recipe_group)
        self.food_lists = {}
        for group_name, food_items in self.shopping_groups.items():
            food_group = QGroupBox(group_name)
            layout = QVBoxLayout(food_group)
            food_list = QListWidget()
            layout.addWidget(food_list)
            self.food_lists[group_name] = food_list
            for food_item in food_items:
                new_item = QListWidgetItem()
                new_item.setData(Qt.DisplayRole, food_item.name)
                new_item.setData(Qt.UserRole, food_item)
                food_list.addItem(new_item)
            food_list.setContextMenuPolicy(Qt.ActionsContextMenu)
            food_list.pressed.connect(partial(self.set_current_group, group_name))
            food_list.addAction(ignore_food_act)
            food_list.horizontalScrollBar().setStyleSheet("QScrollBar {height:0px;}")
            food_list.setSizePolicy(list_policy)
            food_list.itemDoubleClicked.connect(self.double_click_food)
            main_layout.addWidget(food_group)
        main_widget.setSizePolicy(list_policy)
        self._scroll.setWidgetResizable(True)
        self._scroll.setWidget(main_widget)
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self._scroll)
        close_but = QPushButton('Close')
        close_but.clicked.connect(self.accept)
        main_layout.addWidget(close_but)

    def double_click_recipe(self, item):
        recipe = item.data(Qt.UserRole)
        if recipe.name not in self.parent()._recipes:
            return
        result = QMessageBox.information(
            self,
            item.data(Qt.DisplayRole),
            'Add to Already Have?',
            QMessageBox.Yes | QMessageBox.No)
        if result == QMessageBox.Yes:
            self.add_to_already_haves(item)
            self.parent()._recipes.pop(recipe.name)

    def double_click_food(self, item):
        food = item.data(Qt.UserRole)
        if food.name not in self.parent()._shopping_list:
            return
        result = QMessageBox.information(
            self,
            item.data(Qt.DisplayRole),
            'Add to Already Have?',
            QMessageBox.Yes | QMessageBox.No)
        if result == QMessageBox.Yes:
            self.add_to_already_haves(item)
            self.parent()._shopping_list.pop(food.name)

    def add_to_already_haves(self, item):
        """
        Updates the item in already haves and turns the background
        grey.

        Parameters
        ----------
        item : QListWidgetItem
            The item with the food or recipe.
        """
        food = item.data(Qt.UserRole)
        names = get_names()
        names[food.name.lower()] = True
        write_names(names)
        item.setData(Qt.DisplayRole, f'ignored - {food.name}')

    def ignore_recipe(self):
        """
        Grabs the currently selected item and removes
        it from parent recipes and adds it to already haves.
        """
        item = self.recipe_list.currentItem()
        recipe = item.data(Qt.UserRole)
        if recipe.name not in self.parent()._recipes:
            return
        self.add_to_already_haves(item)
        self.parent()._recipes.pop(recipe.name)

    def ignore_food(self):
        """
        Should try to ignore this food for the user.
        """
        item = self.food_lists[self.cur_group].currentItem()
        food = item.data(Qt.UserRole)
        if food.name not in self.parent()._shopping_list:
            return
        self.add_to_already_haves(item)
        self.parent()._shopping_list.pop(food.name)

    def set_current_group(self, group_name):
        """When context menu requested, sets the current group its from."""
        self.cur_group = group_name
