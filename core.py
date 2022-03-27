"""
Provides utility functions to maintain the current days in the file.
"""
#pylint: disable=unspecified-encoding
import datetime as dt
from pathlib import Path

from oauth2client.service_account import ServiceAccountCredentials as sac

import yaml


CFG_PATH = Path('config.yml')
KEY_PATH = Path.home() / 'shopping_list_key.json'
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

def check_keyfile():
    """
    Verifies the existence of the keyfile.

    Returns
    -------
    bool
    """
    return KEY_PATH.exists()

def change_keyfile(key_text):
    """
    Updates and creates a keyfile.
    """
    with open(KEY_PATH, 'w') as k_file:
        k_file.write(key_text)

def get_credentials():
    """
    Retrieves the google api credentials.

    Returns
    -------
    ServiceAccountCredentials
    """
    scope = ['https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive']
    credentials = sac.from_json_keyfile_name(KEY_PATH, scope)
    return credentials

check_config()
build_days()
