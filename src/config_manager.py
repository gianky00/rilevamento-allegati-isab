"""
Intelleo PDF Splitter - Configuration Manager
Gestisce il caricamento e salvataggio della configurazione JSON (SRP).
"""

import json
import os
from typing import Any, Dict, Tuple
from core.path_manager import get_app_base_dir, get_app_data_dir

def get_config_details() -> Tuple[str, str]:
    """Determina la directory base e il percorso del file di configurazione."""
    app_data_dir = get_app_data_dir()
    return app_data_dir, os.path.join(app_data_dir, "config.json")

# Esporta costanti globali
CONFIG_DIR, CONFIG_FILE = get_config_details()

def load_config() -> Dict[str, Any]:
    """Carica la configurazione con logica di fallback."""
    config_data: Dict[str, Any] = {}
    
    # 1. Tenta il caricamento da APPDATA
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, encoding="utf-8") as f:
                config_data = json.load(f)
        except (OSError, json.JSONDecodeError):
            try:
                backup_path = CONFIG_FILE + ".bak"
                if os.path.exists(backup_path):
                    os.remove(backup_path)
                os.rename(CONFIG_FILE, backup_path)
            except OSError:
                pass

    # 2. Se vuoto o senza regole, carica dal template locale
    if not config_data.get("classification_rules"):
        try:
            app_base_dir = get_app_base_dir()
            local_config = os.path.join(app_base_dir, "config.json")
            if os.path.exists(local_config) and os.path.abspath(local_config) != os.path.abspath(CONFIG_FILE):
                with open(local_config, encoding="utf-8") as f:
                    local_data = json.load(f)
                    if isinstance(local_data, dict) and local_data.get("classification_rules"):
                        for k, v in local_data.items():
                            if k not in config_data or (k == "classification_rules" and not config_data[k]):
                                config_data[k] = v
        except Exception:
            pass

    return config_data

def save_config(data: Dict[str, Any]) -> None:
    """Salva la configurazione in modo atomico."""
    tmp_file = CONFIG_FILE + ".tmp"
    try:
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_file, CONFIG_FILE)
    except Exception as e:
        if os.path.exists(tmp_file):
            try: os.remove(tmp_file)
            except OSError: pass
        raise e
