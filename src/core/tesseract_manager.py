"""
Gestore Configurazione Tesseract OCR (SRP).
"""

import os
from pathlib import Path


class TesseractManager:
    """Gestisce il rilevamento e la configurazione del percorso Tesseract."""

    @staticmethod
    def auto_detect() -> str | None:
        """Tenta di rilevare automaticamente il percorso di tesseract.exe."""
        search_paths: list[Path] = [
            Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")) / "Tesseract-OCR" / "tesseract.exe",
            Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")) / "Tesseract-OCR" / "tesseract.exe",
            Path(os.environ.get("LOCALAPPDATA", "")) / "Tesseract-OCR" / "tesseract.exe",
        ]
        for p in search_paths:
            if p.exists():
                return str(p)
        return None

    @staticmethod
    def is_valid(path: str) -> bool:
        """Verifica se il percorso fornito è un eseguibile valido."""
        if not path:
            return False
        p = Path(path)
        return p.is_file() and p.suffix.lower() == ".exe"
