"""
Servizio per la scansione e validazione dei file nel filesystem (SRP).
"""

import os


class FileService:
    """Gestisce la ricerca e la validazione di file PDF."""

    @staticmethod
    def find_pdfs_in_path(path: str) -> list[str]:
        """Trova ricorsivamente tutti i file PDF in un percorso (file o cartella)."""
        found_pdfs: list[str] = []

        if not path or not os.path.exists(path):
            return found_pdfs

        if os.path.isfile(path):
            if path.lower().endswith(".pdf"):
                found_pdfs.append(os.path.abspath(path))
        elif os.path.isdir(path):
            for root, _, files in os.walk(path):
                # Esclude cartelle di sistema o di archiviazione per evitare loop infiniti
                if "ORIGINALI" in root:
                    continue
                for name in files:
                    if name.lower().endswith(".pdf"):
                        found_pdfs.append(os.path.abspath(os.path.join(root, name)))

        return found_pdfs

    @staticmethod
    def is_pdf(filepath: str) -> bool:
        """Verifica se un file è un PDF valido per estensione."""
        return bool(filepath and os.path.isfile(filepath) and filepath.lower().endswith(".pdf"))
