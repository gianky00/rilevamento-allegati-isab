"""
Intelleo PDF Splitter - Configuration Manager
Gestisce il caricamento e salvataggio della configurazione JSON.
"""
import json
import os
import sys


def get_config_path():
    """
    Restituisce il percorso del file di configurazione.
    
    Gestisce sia l'esecuzione come script che come eseguibile PyInstaller.
    """
    if getattr(sys, 'frozen', False):
        # Eseguibile PyInstaller
        base_path = os.path.dirname(sys.executable)
    else:
        # Script Python: config.json is in root (one level up from src/)
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, 'config.json')


CONFIG_FILE = get_config_path()


def load_config():
    """
    Carica la configurazione dal file config.json.
    
    Returns:
        dict: Configurazione caricata o dizionario vuoto in caso di errore
    """
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        print(f"[AVVISO] File di configurazione '{CONFIG_FILE}' corrotto")
        try:
            backup_path = CONFIG_FILE + ".bak"
            if os.path.exists(backup_path):
                os.remove(backup_path)
            os.rename(CONFIG_FILE, backup_path)
            print(f"[INFO] File corrotto rinominato in '{backup_path}'")
        except OSError as e:
            print(f"[ERRORE] Impossibile rinominare file corrotto: {e}")
        return {}


def save_config(data):
    """
    Salva la configurazione nel file config.json in modo atomico.
    
    Scrive prima su un file temporaneo, poi lo rinomina per garantire
    l'integrità dei dati in caso di interruzione.
    
    Args:
        data (dict): Dati di configurazione da salvare
        
    Raises:
        Exception: In caso di errore durante il salvataggio
    """
    tmp_file = CONFIG_FILE + ".tmp"
    try:
        with open(tmp_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())

        # Sostituzione atomica
        os.replace(tmp_file, CONFIG_FILE)
    except Exception as e:
        print(f"[ERRORE] Salvataggio configurazione: {e}")
        if os.path.exists(tmp_file):
            try:
                os.remove(tmp_file)
            except:
                pass
        raise e
