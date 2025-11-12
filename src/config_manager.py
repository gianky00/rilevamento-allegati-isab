import json
import os

CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'config.json')

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
