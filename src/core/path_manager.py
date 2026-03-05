"""
Gestisce la risoluzione dei percorsi di sistema e dell'applicazione (SRP).
"""

import os
import sys


def get_app_base_dir() -> str:
    """Restituisce la directory base dell'applicazione (root del progetto o cartella exe)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)

    current = os.path.dirname(os.path.abspath(__file__))
    # Risale da src/core/ alla root del progetto
    while True:
        if os.path.exists(os.path.join(current, "config.json")) or os.path.exists(os.path.join(current, ".git")):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        current = parent


def get_app_data_dir() -> str:
    """Restituisce il percorso della cartella dati in APPDATA."""
    app_data_root = os.getenv("APPDATA") or os.path.expanduser("~")
    path = os.path.join(app_data_root, "Intelleo PDF Splitter")
    os.makedirs(path, exist_ok=True)
    return path


def get_asset_path(filename: str) -> str:
    """Restituisce il percorso assoluto di un asset (SVG, Icone)."""
    base = get_app_base_dir()
    # Supporto per PyInstaller
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, "assets", filename)
    return os.path.join(base, "assets", filename)


def get_resource_path(filename: str) -> str:
    """Restituisce il percorso di una risorsa interna (es. icon.ico)."""
    base = get_app_base_dir()
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, "src", "resources", filename)
    return os.path.join(base, "src", "resources", filename)
