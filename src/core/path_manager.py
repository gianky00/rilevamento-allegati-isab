"""
Gestisce la risoluzione dei percorsi di sistema e dell'applicazione (SRP).
"""

import sys
from pathlib import Path


def get_app_base_dir() -> str:
    """Restituisce la directory base dell'applicazione (root del progetto o cartella exe)."""
    if getattr(sys, "frozen", False):
        return str(Path(sys.executable).parent)

    current = Path(__file__).resolve().parent
    # Risale da src/core/ alla root del progetto
    for _ in range(10): # Limite di sicurezza per evitare loop infiniti
        if (current / "config.json").exists() or (current / ".git").exists():
            return str(current)
        if current.parent == current:
            break
        current = current.parent

    return str(Path(__file__).resolve().parents[2])


def get_app_data_dir() -> str:
    """Restituisce il percorso della cartella dati in APPDATA."""
    import os
    app_data_root = Path(os.getenv("APPDATA") or Path.home())
    path = app_data_root / "Intelleo PDF Splitter"
    path.mkdir(parents=True, exist_ok=True)
    return str(path)


def get_asset_path(filename: str) -> str:
    """Restituisce il percorso assoluto di un asset (SVG, Icone)."""
    # Supporto per PyInstaller
    if hasattr(sys, "_MEIPASS"):
        return str(Path(sys._MEIPASS) / "assets" / filename)

    base = Path(get_app_base_dir())
    return str(base / "assets" / filename)


def get_resource_path(filename: str) -> str:
    """Restituisce il percorso di una risorsa interna (es. icon.ico)."""
    if hasattr(sys, "_MEIPASS"):
        return str(Path(sys._MEIPASS) / "src" / "resources" / filename)

    base = Path(get_app_base_dir())
    return str(base / "src" / "resources" / filename)
