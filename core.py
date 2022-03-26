"""
Provides utility functions to maintain the current days in the file.
"""
import datetime as dt
from pathlib import Path

import yaml


CFG_PATH = Path('config.yml')
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

def create_default_config():
    """
    Builds the default configuration file.
    """
    default_names = (
        'Chris Food Plan',
        "Melia's Food Plan",
        "Bryn's Food Plan")
    yml_dict = {
        'names': {},
        'sheets' : {name:None for name in default_names},
        'threaded':True,
    }
    with open(CFG_PATH, 'w') as y_file:
        yaml.dump(yml_dict, y_file)

def check_config():
    """Verifies the config is ok to use."""
    if not CFG_PATH.exists():
        create_default_config()

check_config()
build_days()
