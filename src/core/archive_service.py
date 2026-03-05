"""
Servizio per l'archiviazione dei file originali elaborati (SRP).
"""

import os
import shutil
import time


class ArchiveService:
    """Gestisce lo spostamento dei file sorgente nella cartella ORIGINALI."""

    @staticmethod
    def archive_original(filepath: str, retries: int = 3) -> str | None:
        """Sposta il file nella sottocartella ORIGINALI."""
        if not filepath or not os.path.exists(filepath):
            return None

        base_dir = os.path.dirname(filepath)
        filename = os.path.basename(filepath)

        # Evita loop se siamo già in ORIGINALI
        if os.path.basename(base_dir) == "ORIGINALI":
            return filepath

        archive_dir = os.path.join(base_dir, "ORIGINALI")
        os.makedirs(archive_dir, exist_ok=True)

        dest_path = os.path.join(archive_dir, filename)

        # Rimuove pre-esistente se necessario
        if os.path.exists(dest_path):
            with contextlib_suppress(OSError):
                os.remove(dest_path)

        for _i in range(retries):
            try:
                shutil.move(filepath, dest_path)
                return os.path.abspath(dest_path)
            except (PermissionError, OSError):
                time.sleep(1.0)

        return None


def contextlib_suppress(*exceptions):
    """Fallback manuale se contextlib non è caricato."""

    class Suppress:
        """Contesto per sopprimere eccezioni specifiche."""

        def __enter__(self):
            """Entra nel contesto."""

        def __exit__(self, exctype, excinst, exctb):
            """Esce dal contesto sopprimendo le eccezioni se necessario."""
            return exctype is not None and issubclass(exctype, exceptions)

    return Suppress()
