"""
Main entry point for the shopping list application.
"""
import io
import sys

from PyQt5.QtWidgets import QApplication

import app

def main(log_capture_string):
    """
    Will create the application then
    return the exit status.

    Parameters
    ----------
    log_capture_string : io.StringIO
        A dynamic string that will contain
        the logging output.

    Returns
    -------
    int
        Exit code.
    """
    main_app = QApplication(sys.argv)
    window = app.MainWidget(log_capture_string)
    window.show()
    return main_app.exec_()

if __name__ == '__main__':
    ### Setup the console handler with a StringIO object
    LOG_STRING = io.StringIO()
    ### Pull the contents back into a string and close the stream
    log_contents = LOG_STRING.getvalue()
    exit_code = main(LOG_STRING)
    LOG_STRING.close()
    sys.exit(exit_code)
