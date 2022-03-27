"""
Provides utility functions to maintain the current days in the file.
"""
#pylint: disable=unspecified-encoding
import datetime as dt
from pathlib import Path

import yaml


CFG_PATH = Path('config.yml')
DAYS = {}
_sheet_names = (
    'Chris Food Plan',
    "Melia's Food Plan",
    "Bryn's Food Plan"
)
DEFAULTS = {
    'names': {},
    'sheets' : {name:None for name in _sheet_names},
    'threaded':True,
    'filename':'shopping_list',
    'output_dir': '~/Desktop',
}

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
    with open(CFG_PATH, 'w') as y_file:
        yaml.dump(DEFAULTS, y_file)

def check_config():
    """Verifies the config is ok to use."""
    if CFG_PATH.exists():
        with open(CFG_PATH, 'rb') as y_file:
            yml_dict = yaml.load(y_file, yaml.Loader)
        for key, default_val in DEFAULTS.items():
            if key not in yml_dict:
                yml_dict[key] = default_val
        with open(CFG_PATH, 'w') as y_file:
            yaml.dump(yml_dict, y_file, yaml.Dumper)
    else:
        create_default_config()

check_config()
build_days()
