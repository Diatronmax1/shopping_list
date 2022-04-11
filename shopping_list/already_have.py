"""
Breaks out the Already Have widgets for organization.
"""
#pylint: disable=unspecified-encoding, invalid-name
import os

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAction,
    QDialog,
    QGridLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
)
import yaml

from shopping_list import CFG_PATH

def write_names(names):
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
        yml_dict['names'] = names
    with open(CFG_PATH, 'w') as y_file:
        yaml.dump(yml_dict, y_file, yaml.Dumper)

def get_names():
    """
    Retrieves names from the config file.
    """
    with open(CFG_PATH, 'rb') as y_file:
        return yaml.load(y_file, yaml.Loader)['names']

def get_ignored():
    """
    Builds the ignored set from the config file.
    Case insensitive is preserved by always loading
    the names in as lowercase.

    Returns
    =======
    set
        The already have names that should be ignored.
    """
    return set([name.lower() for name, use in get_names().items() if use])

class AlreadyHave(QDialog):
    """
    Widget that allows manipulation of the underlying
    ini file and can set and remove different names
    to be ignored.

    """

    def __init__(self, parent):
        super().__init__(parent)
        if os.name != 'nt':
            self.setWindowModality(Qt.WindowModal)
        self.setWindowTitle('Already Haves')
        self.save_and_close = QPushButton('Save and Close')
        modify_act = QAction('Change Name?', self)
        remove_act = QAction('Remove?', self)
        self.cancel_but = QPushButton('Cancel')
        self.create_new = QPushButton('+')
        self.already_haves = QListWidget()
        self.already_haves.setContextMenuPolicy(Qt.ActionsContextMenu)
        self.already_haves.addActions([modify_act, remove_act])
        self.already_haves.itemDoubleClicked.connect(self.prompt_actions)
        for name, used in get_names().items():
            new_item = QListWidgetItem()
            new_item.setData(Qt.DisplayRole, name)
            if used:
                new_item.setData(Qt.CheckStateRole, Qt.Checked)
            else:
                new_item.setData(Qt.CheckStateRole, Qt.Unchecked)
            self.already_haves.addItem(new_item)
        #Signals.
        modify_act.triggered.connect(self.modify_name)
        remove_act.triggered.connect(self.remove_name)
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
        layout.addWidget(self.already_haves,  2, 0, 1, 2)
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
            self.modify_name()
        elif button == rem_but:
            self.remove_name()

    def check_name(self, name):
        """
        Verifies name is not already in list of
        items.
        """
        for row in range(self.already_haves.count()):
            item = self.already_haves.item(row)
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
        name, ok_pressed = QInputDialog.getText(self,
            'New Item',
            'Name: ')
        if name and ok_pressed:
            if self.check_name(name):
                return
            new_item = QListWidgetItem()
            new_item.setData(Qt.DisplayRole, name)
            new_item.setData(Qt.CheckStateRole, Qt.Checked)
            self.already_haves.addItem(new_item)

    def modify_name(self):
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
        item = self.already_haves.currentItem()
        new_name, ok_pressed = QInputDialog.getText(self,
            f'New name for {item.data(Qt.DisplayRole)}',
            'New Name: ')
        if new_name and ok_pressed:
            if self.check_name(new_name):
                return
            item.setData(Qt.DisplayRole, new_name)

    def remove_name(self):
        """
        Removes a name from config.

        Parameters
        ----------
        widget : HaveCheck
            The widget to delete.
        """
        row = self.already_haves.currentRow()
        item = self.already_haves.takeItem(row)
        del item

    def accept(self):
        """
        Saves the cfg to the file.
        """
        names = {}
        for row in range(self.already_haves.count()):
            item = self.already_haves.item(row)
            name = item.data(Qt.DisplayRole)
            checked = item.data(Qt.CheckStateRole) == Qt.Checked
            names[name] = checked
        write_names(names)
        super().accept()
