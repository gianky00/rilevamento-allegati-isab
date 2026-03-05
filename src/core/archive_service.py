"""
Servizio per l'archiviazione dei file originali elaborati (SRP).
"""

import shutil
import time
from contextlib import suppress
from pathlib import Path


class ArchiveService:
    """Gestisce lo spostamento dei file sorgente nella cartella ORIGINALI."""

    @staticmethod
    def archive_original(filepath: str, retries: int = 3) -> str | None:
        """Sposta il file nella sottocartella ORIGINALI."""
        if not filepath:
            return None
            
        src_path = Path(filepath)
        if not src_path.exists():
            return None

        # Evita loop se siamo già in ORIGINALI
        if src_path.parent.name == "ORIGINALI":
            return str(src_path)

        archive_dir = src_path.parent / "ORIGINALI"
        archive_dir.mkdir(parents=True, exist_ok=True)

        dest_path = archive_dir / src_path.name

        # Rimuove pre-esistente se necessario
        if dest_path.exists():
            with suppress(OSError):
                dest_path.unlink()

        for _i in range(retries):
            try:
                shutil.move(src_path, dest_path)
                return str(dest_path.resolve())
            except (PermissionError, OSError):
                time.sleep(1.0)

        return None
