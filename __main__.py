import app
from PyQt5.QtWidgets import QApplication
import sys

def main():
    main_app = QApplication(sys.argv)
    a = app.MainWidget()
    a.show()
    sys.exit(main_app.exec_())


if __name__ == '__main__':
    main()