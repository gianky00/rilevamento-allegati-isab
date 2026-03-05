"""
Intelleo PDF Splitter - Configuration Manager
Gestisce il caricamento e salvataggio della configurazione JSON.
"""

import builtins
import contextlib
import json
import os
import sys


def get_config_details():
    """
    Determina la directory base e il percorso del file di configurazione.

    Logica:
    1. Se esiste in APPDATA, usa quello per lettura e scrittura.
    2. Se esiste solo nella cartella dell'app, usalo per caricare i default,
       ma imposta il salvataggio in APPDATA.
    3. Altrimenti, usa APPDATA come default assoluto.
    """
    if getattr(sys, "frozen", False):
        app_dir = os.path.dirname(sys.executable)
    else:
        app_dir = os.path.dirname(os.path.abspath(__file__))

    local_config = os.path.join(app_dir, "config.json")

    app_data_root = os.getenv("APPDATA")
    if not app_data_root:
        app_data_root = os.path.expanduser("~")

    app_data_dir = os.path.join(app_data_root, "Intelleo PDF Splitter")
    appdata_config = os.path.join(app_data_dir, "config.json")

    # 1. Priorità assoluta: se esiste in APPDATA, è il file dell'utente.
    if os.path.exists(appdata_config):
        return app_data_dir, appdata_config

    # 2. Se esiste in locale ma non in APPDATA, usalo come sorgente iniziale.
    if os.path.exists(local_config):
        with contextlib.suppress(builtins.BaseException):
            os.makedirs(app_data_dir, exist_ok=True)
        return app_data_dir, appdata_config

    # 3. Default: usa APPDATA
    try:
        os.makedirs(app_data_dir, exist_ok=True)
    except Exception:
        return app_dir, local_config

    return app_data_dir, appdata_config


# Esporta costanti globali
CONFIG_DIR, CONFIG_FILE = get_config_details()


def load_config():
    """
    Carica la configurazione. Cerca prima nel percorso predefinito (CONFIG_FILE),
    se non esiste o è corrotto prova a leggere quello locale (template).
    """
    # 1. Tenta il caricamento dal file principale (solitamente APPDATA)
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, encoding="utf-8") as f:
                return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"[AVVISO] File di configurazione '{CONFIG_FILE}' corrotto o inaccessibile: {e}")
        try:
            backup_path = CONFIG_FILE + ".bak"
            if os.path.exists(backup_path):
                os.remove(backup_path)
            os.rename(CONFIG_FILE, backup_path)
            print(f"[INFO] File problematico rinominato in '{backup_path}'")
        except OSError:
            pass

    # 2. Se non trovato o corrotto, prova a leggere il template locale dalla cartella dell'app
    try:
        if getattr(sys, "frozen", False):
            app_dir = os.path.dirname(sys.executable)
        else:
            app_dir = os.path.dirname(os.path.abspath(__file__))

        local_config = os.path.join(app_dir, "config.json")
        if os.path.exists(local_config):
            with open(local_config, encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"[ERRORE] Impossibile caricare configurazione locale: {e}")

    return {}


def save_config(data):
    """
    Salva la configurazione nel file config.json in modo atomico.
    """
    tmp_file = CONFIG_FILE + ".tmp"
    try:
        # Assicurati che la cartella esista se specificata
        dir_name = os.path.dirname(CONFIG_FILE)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)

        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())

        # Sostituzione atomica
        os.replace(tmp_file, CONFIG_FILE)
    except Exception as e:
        print(f"[ERRORE] Salvataggio configurazione in '{CONFIG_FILE}': {e}")
        if os.path.exists(tmp_file):
            with contextlib.suppress(builtins.BaseException):
                os.remove(tmp_file)
        raise e
