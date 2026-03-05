"""
Servizio per la scansione e validazione dei file nel filesystem (SRP).
"""

from pathlib import Path


class FileService:
    """Gestisce la ricerca e la validazione di file PDF."""

    @staticmethod
    def find_pdfs_in_path(path: str) -> list[str]:
        """Trova ricorsivamente tutti i file PDF in un percorso (file o cartella)."""
        found_pdfs: list[str] = []

        if not path:
            return found_pdfs
            
        p = Path(path)
        if not p.exists():
            return found_pdfs

        if p.is_file():
            if p.suffix.lower() == ".pdf":
                found_pdfs.append(str(p.resolve()))
        elif p.is_dir():
            # Utilizziamo rglob per una ricerca ricorsiva più pulita con pathlib
            for pdf_file in p.rglob("*.pdf"):
                # Esclude cartelle di sistema o di archiviazione per evitare loop infiniti
                if "ORIGINALI" in pdf_file.parts:
                    continue
                found_pdfs.append(str(pdf_file.resolve()))

        return found_pdfs

    @staticmethod
    def is_pdf(filepath: str) -> bool:
        """Verifica se un file è un PDF valido per estensione."""
        if not filepath:
            return False
        p = Path(filepath)
        return p.is_file() and p.suffix.lower() == ".pdf"
