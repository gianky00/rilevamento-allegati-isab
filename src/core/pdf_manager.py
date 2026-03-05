"""
Gestione rendering e metadati PDF (SRP).
"""
from typing import Optional, Tuple
import pymupdf as fitz
from PIL import Image

class PdfManager:
    """Gestisce il caricamento e il rendering delle pagine PDF."""

    def __init__(self) -> None:
        self.doc: Optional[fitz.Document] = None
        self.current_path: Optional[str] = None
        self.dpi: int = 150

    def open(self, path: str) -> Tuple[bool, str]:
        """Apre un file PDF e restituisce il successo e un messaggio."""
        try:
            self.doc = fitz.open(path)
            self.current_path = path
            return True, "PDF aperto correttamente"
        except Exception as e:
            return False, str(e)

    def close(self) -> None:
        """Chiude il documento corrente."""
        if self.doc:
            self.doc.close()
            self.doc = None
            self.current_path = None

    def get_page_count(self) -> int:
        """Restituisce il numero totale di pagine."""
        return len(self.doc) if self.doc else 0

    def get_page_size(self, page_index: int) -> Tuple[float, float]:
        """Restituisce le dimensioni della pagina PDF (in punti)."""
        if not self.doc or not (0 <= page_index < len(self.doc)):
            return 0, 0
        page = self.doc[page_index]
        return page.rect.width, page.rect.height

    def render_page(self, page_index: int, zoom: float = 1.0) -> Optional[bytes]:
        """Renderizza una pagina e restituisce i campioni di pixel (samples)."""
        if not self.doc or not (0 <= page_index < len(self.doc)):
            return None
        
        # Fattore di scala basato su DPI standard (72) e DPI desiderato (150)
        scale = (self.dpi * zoom) / 72
        mat = fitz.Matrix(scale, scale)
        pix = self.doc[page_index].get_pixmap(matrix=mat)
        
        samples = pix.samples
        return samples if isinstance(samples, bytes) else None

    def get_pixmap(self, page_index: int, zoom: float = 1.0) -> Optional[fitz.Pixmap]:
        """Restituisce l'oggetto Pixmap di fitz per la pagina."""
        if not self.doc or not (0 <= page_index < len(self.doc)):
            return None
        scale = (self.dpi * zoom) / 72
        mat = fitz.Matrix(scale, scale)
        return self.doc[page_index].get_pixmap(matrix=mat)
