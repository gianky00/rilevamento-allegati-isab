"""
Gestore Configurazione Tesseract OCR (SRP).
"""
import os
from typing import List, Optional

class TesseractManager:
    """Gestisce il rilevamento e la configurazione del percorso Tesseract."""

    @staticmethod
    def auto_detect() -> Optional[str]:
        """Tenta di rilevare automaticamente il percorso di tesseract.exe."""
        search_paths: List[str] = [
            os.path.join(os.environ.get("PROGRAMFILES", r"C:\Program Files"), "Tesseract-OCR", "tesseract.exe"),
            os.path.join(
                os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"), "Tesseract-OCR", "tesseract.exe"
            ),
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Tesseract-OCR", "tesseract.exe"),
        ]
        for p in search_paths:
            if p and os.path.exists(p):
                return p
        return None

    @staticmethod
    def is_valid(path: str) -> bool:
        """Verifica se il percorso fornito è un eseguibile valido."""
        return os.path.isfile(path) and path.lower().endswith(".exe")
