"""
Provides utility functions to maintain the current days in the file.
"""

import datetime as dt

DAYS = {}

def build_days():
    """
    Creates 7 days and adds them to the global
    DAYS dictionary.
    """
    today = dt.date.today()
    for num in range(7):
        day = today + dt.timedelta(days=num)
        DAYS[day.strftime("%A")] = day

build_days()
