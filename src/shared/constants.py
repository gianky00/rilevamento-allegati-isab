"""
Intelleo PDF Splitter — Costanti Globali
Percorsi, signal file e costanti condivise tra tutti i layer.
"""
import os
import config_manager

# Segnale per comunicazione tra utility ROI e app principale
SIGNAL_FILE = ".update_signal"

# Costanti per la gestione della sessione
APP_DATA_DIR = config_manager.CONFIG_DIR
SESSION_FILE = os.path.join(APP_DATA_DIR, "session.json")
