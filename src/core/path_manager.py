"""
Gestisce la risoluzione dei percorsi di sistema e dell'applicazione (SRP).
"""

import sys
from pathlib import Path


class PathManager:
    """Classe per la gestione dei percorsi (Standard OOP)."""

    @staticmethod
    def get_app_base_dir() -> str:
        """Restituisce la directory base dell'applicazione."""
        if getattr(sys, "frozen", False):
            return str(Path(sys.executable).parent)

        current = Path(__file__).resolve().parent
        for _ in range(10):
            if (current / "config.json").exists() or (current / ".git").exists():
                return str(current)
            if current.parent == current:
                break
            current = current.parent
        return str(Path(__file__).resolve().parents[2])

    @staticmethod
    def get_app_data_dir() -> str:
        """Restituisce il percorso della cartella dati in APPDATA."""
        import os
        app_data_root = Path(os.getenv("APPDATA") or Path.home())
        path = app_data_root / "Intelleo PDF Splitter"
        path.mkdir(parents=True, exist_ok=True)
        return str(path)

    @staticmethod
    def get_asset_path(filename: str) -> str:
        """Restituisce il percorso assoluto di un asset."""
        if hasattr(sys, "_MEIPASS"):
            return str(Path(sys._MEIPASS) / "assets" / filename)
        base = Path(PathManager.get_app_base_dir())
        return str(base / "assets" / filename)

    @staticmethod
    def get_resource_path(filename: str) -> str:
        """Restituisce il percorso di una risorsa interna."""
        if hasattr(sys, "_MEIPASS"):
            return str(Path(sys._MEIPASS) / "src" / "resources" / filename)
        base = Path(PathManager.get_app_base_dir())
        return str(base / "src" / "resources" / filename)


# Alias per retro-compatibilità
get_app_base_dir = PathManager.get_app_base_dir
get_app_data_dir = PathManager.get_app_data_dir
get_asset_path = PathManager.get_asset_path
get_resource_path = PathManager.get_resource_path
