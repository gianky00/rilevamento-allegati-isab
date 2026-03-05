"""
Servizio per l'analisi e la classificazione delle pagine PDF (SRP).
Utilizza OcrEngine e DocumentClassifier.
"""
import time
from typing import Any, Callable, Dict, List, Optional
import pymupdf as fitz
from PIL import Image
from core.ocr_engine import OcrEngine
from core.classifier import DocumentClassifier

class AnalysisService:
    """Gestisce la logica di scansione intelligente delle pagine."""

    def __init__(self, rules: List[Dict[str, Any]], ocr_engine: OcrEngine):
        """Configura il servizio di analisi con le regole e il motore OCR."""
        self.rules = rules
        self.ocr_engine = ocr_engine
        self.classifier = DocumentClassifier(rules)

    def analyze_pdf(self, pdf_doc: fitz.Document, progress_callback: Optional[Callable] = None) -> Dict[str, List[int]]:
        """Scansiona tutte le pagine e restituisce i gruppi di pagine per categoria."""
        page_groups: Dict[str, List[int]] = {}
        total_pages = len(pdf_doc)
        avg_time_per_page = 0.0
        alpha = 0.3

        for i, page in enumerate(pdf_doc):
            start_t = time.time()
            
            # Notifica progresso
            if progress_callback:
                eta = (total_pages - i) * avg_time_per_page if i > 0 else 0
                progress_callback({
                    "type": "page_progress",
                    "current": i + 1,
                    "total": total_pages,
                    "eta_seconds": eta,
                    "phase": "analysis",
                    "phase_pct": ((i + 1) / total_pages) * 90,
                })

            category = self._analyze_single_page(page)
            page_groups.setdefault(category, []).append(i)

            # Aggiorna stima tempo
            this_page_time = time.time() - start_t
            avg_time_per_page = this_page_time if i == 0 else (alpha * this_page_time) + ((1 - alpha) * avg_time_per_page)

        return page_groups

    def _analyze_single_page(self, page: fitz.Page) -> str:
        """Analizza una singola pagina tentando match veloce e poi OCR."""
        page_rect = page.rect
        for rule in self.rules:
            category = str(rule.get("category_name", "sconosciuto"))
            keywords = rule.get("keywords", [])
            
            for roi in rule.get("rois", []):
                if len(roi) != 4: continue
                roi_rect = fitz.Rect(roi)
                if roi_rect.x1 > page_rect.width or roi_rect.y1 > page_rect.height: continue

                # 1. Match veloce (Testo nativo)
                try:
                    native_text = page.get_text("text", clip=roi_rect)
                    if self.classifier.classify_text(native_text) == category:
                        return category
                except Exception: pass

                # 2. Match Robusto (OCR)
                try:
                    mat = fitz.Matrix(300 / 72, 300 / 72)
                    pix = page.get_pixmap(matrix=mat, clip=roi_rect, colorspace=fitz.csGRAY)
                    if pix.width < 1 or pix.height < 1: continue
                    
                    img = Image.frombytes("L", (pix.width, pix.height), pix.samples)
                    found, _ = self.ocr_engine.robust_scan(img, keywords)
                    if found: return category
                except Exception: pass

        return "sconosciuto"
