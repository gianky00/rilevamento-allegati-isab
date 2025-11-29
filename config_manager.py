import json
import os
import sys

def get_config_path():
    if getattr(sys, 'frozen', False):
        # If the application is run as a bundle, the PyInstaller bootloader
        # extends the sys module by a flag frozen=True and sets the app
        # path into variable _MEIPASS'.
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, 'config.json')

CONFIG_FILE = get_config_path()

def load_config():
    """
    Loads the configuration from the config.json file.
    Returns a dictionary with the configuration.
    """
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_config(data):
    """
    Saves the configuration to the config.json file.
    """
    with open(CONFIG_FILE, 'w') as f:
        json.dump(data, f, indent=4)
