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
    except json.JSONDecodeError:
        print(f"Errore: Il file di configurazione '{CONFIG_FILE}' è corrotto.")
        try:
            backup_path = CONFIG_FILE + ".bak"
            if os.path.exists(backup_path):
                os.remove(backup_path)
            os.rename(CONFIG_FILE, backup_path)
            print(f"Il file corrotto è stato rinominato in '{backup_path}'. Verrà creata una nuova configurazione.")
        except OSError as e:
            print(f"Impossibile rinominare il file di configurazione corrotto: {e}")
        return {}

def save_config(data):
    """
    Saves the configuration to the config.json file.
    """
    with open(CONFIG_FILE, 'w') as f:
        json.dump(data, f, indent=4)
