from PyQt5 import QtWidgets
import shopping_list
import os

class MainWidget(QtWidgets.QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.button_group = QtWidgets.QButtonGroup()
        self.button_group.setExclusive(False)
        sunday_check = QtWidgets.QCheckBox('Sunday')
        monday_check = QtWidgets.QCheckBox('Monday')
        tuesday_check = QtWidgets.QCheckBox('Tuesday')
        wednesday_check = QtWidgets.QCheckBox('Wednesday')
        thursday_check = QtWidgets.QCheckBox('Thursday')
        friday_check = QtWidgets.QCheckBox('Friday')
        saturday_check = QtWidgets.QCheckBox('Saturday')
        self.file_name = QtWidgets.QLineEdit()
        self.file_name.setText('shopping_list')
        self.generate_list_but = QtWidgets.QPushButton('Generate List')
        self.button_group.addButton(sunday_check)
        self.button_group.addButton(monday_check)
        self.button_group.addButton(tuesday_check)
        self.button_group.addButton(wednesday_check)
        self.button_group.addButton(thursday_check)
        self.button_group.addButton(friday_check)
        self.button_group.addButton(saturday_check)
        self.status = QtWidgets.QTextEdit()
        #Signals
        self.generate_list_but.clicked.connect(self.make_shopping_list)
        #Layout
        days = QtWidgets.QGroupBox('Days')
        layout = QtWidgets.QHBoxLayout(days)
        for button in self.button_group.buttons():
            button.setChecked(True)
            layout.addWidget(button)
        name_line = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(name_line)
        layout.addWidget(self.file_name)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(days)
        layout.addWidget(name_line)
        layout.addWidget(QtWidgets.QLabel('Status'))
        layout.addWidget(self.status)
        layout.addWidget(self.generate_list_but)

    def make_shopping_list(self):
        days = {}
        for button in self.button_group.buttons():
            days[button.text().lower()] = button.isChecked()
        file_name = os.path.splitext(self.file_name.text())[0] + '.txt'
        results = shopping_list.main(days, file_name)
        text = ''
        for result in results:
            text += result + '\n'
        self.status.setText(text)

class ShoppingList(QtWidgets.QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle('Shopping List')
        self.main_widget = MainWidget()
        self.setCentralWidget(self.main_widget)
