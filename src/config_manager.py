"""
Intelleo PDF Splitter - Configuration Manager
Gestisce il caricamento e salvataggio della configurazione JSON (SRP).
"""

import json
import os
from contextlib import suppress
from pathlib import Path
from typing import Any

from core.path_manager import get_app_base_dir, get_app_data_dir


def get_config_details() -> tuple[str, str]:
    """Determina la directory base e il percorso del file di configurazione."""
    app_data_dir = Path(get_app_data_dir())
    return str(app_data_dir), str(app_data_dir / "config.json")


# Esporta costanti globali per retro-compatibilità
CONFIG_DIR, CONFIG_FILE = get_config_details()


class ConfigManager:
    """Classe per la gestione della configurazione (Standard OOP)."""

    @staticmethod
    def load_config() -> dict[str, Any]:
        """Carica la configurazione con logica di fallback."""
        config_data: dict[str, Any] = {}
        config_path = Path(CONFIG_FILE)

        # 1. Tenta il caricamento da APPDATA
        if config_path.exists():
            try:
                with config_path.open(encoding="utf-8") as f:
                    config_data = json.load(f)
            except (OSError, json.JSONDecodeError):
                with suppress(OSError):
                    backup_path = config_path.with_suffix(config_path.suffix + ".bak")
                    if backup_path.exists():
                        backup_path.unlink()
                    config_path.rename(backup_path)

        # 2. Se vuoto o senza regole, carica dal template locale
        if not config_data.get("classification_rules"):
            with suppress(Exception):
                app_base_dir = Path(get_app_base_dir())
                local_config = app_base_dir / "config.json"
                if local_config.exists() and local_config.resolve() != config_path.resolve():
                    with local_config.open(encoding="utf-8") as f:
                        local_data = json.load(f)
                        if isinstance(local_data, dict) and local_data.get("classification_rules"):
                            for k, v in local_data.items():
                                if k not in config_data or (k == "classification_rules" and not config_data[k]):
                                    config_data[k] = v

        return config_data

    @staticmethod
    def save_config(data: dict[str, Any]) -> None:
        """Salva la configurazione in modo atomico."""
        config_path = Path(CONFIG_FILE)
        tmp_file = config_path.with_suffix(config_path.suffix + ".tmp")
        try:
            config_path.parent.mkdir(parents=True, exist_ok=True)
            with tmp_file.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            tmp_file.replace(config_path)
        except Exception:
            if tmp_file.exists():
                with suppress(OSError):
                    tmp_file.unlink()
            raise


# Alias per retro-compatibilità procedurale
load_config = ConfigManager.load_config
save_config = ConfigManager.save_config
