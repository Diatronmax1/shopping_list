"""
Breaks out the Already Have widgets for organization.
"""
#pylint: disable=unspecified-encoding, invalid-name
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (
    QCheckBox,
    QDialog,
    QInputDialog,
    QGridLayout,
    QMenu,
    QPushButton,
    QWidget,
)
import yaml

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
