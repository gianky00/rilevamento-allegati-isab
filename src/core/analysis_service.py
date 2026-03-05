"""
Servizio per l'analisi e la classificazione delle pagine PDF (SRP).
Utilizza OcrEngine e DocumentClassifier.
"""
import time
import os
import concurrent.futures
from typing import Any, Callable, Dict, List, Optional, Tuple
import pymupdf as fitz
from PIL import Image
from core.ocr_engine import OcrEngine
from core.classifier import DocumentClassifier

class AnalysisService:
    """Gestisce la logica di scansione intelligente delle pagine con supporto al parallelismo."""

    def __init__(self, rules: List[Dict[str, Any]], ocr_engine: OcrEngine):
        """Configura il servizio di analisi con le regole e il motore OCR."""
        self.rules = rules
        self.ocr_engine = ocr_engine
        self.classifier = DocumentClassifier(rules)
        self._page_cache: Dict[int, Image.Image] = {}

    def analyze_pdf(self, pdf_path: str, progress_callback: Optional[Callable] = None, cancel_check: Optional[Callable[[], bool]] = None) -> Dict[str, List[int]]:
        """
        Scansiona tutte le pagine in parallelo e restituisce i gruppi di pagine per categoria.
        Ottimizzato per massimizzare la velocità senza perdere precisione.
        """
        page_groups: Dict[str, List[int]] = {}
        
        # Determina il numero di worker ottimale
        # Per ora disabilitiamo il parallelismo per debuggare i test
        workers = 1
        total_pages = 0
        doc = fitz.open(pdf_path)
        total_pages = doc.page_count
        doc.close()
            
        if total_pages == 0:
            return {}

        results: List[Tuple[int, str]] = []
        
        # Sequenziale
        for page_num in range(total_pages):
            if cancel_check and cancel_check():
                raise InterruptedError("Analisi interrotta")
            res = self._analyze_page_task(pdf_path, page_num)
            results.append(res)
            if progress_callback:
                progress_callback({
                    "type": "page_progress", "current": page_num + 1,
                    "total": total_pages, "phase": "analysis",
                    "phase_pct": ((page_num + 1) / total_pages) * 100,
                })

        # Riordina i risultati (as_completed non garantisce l'ordine)
        results.sort(key=lambda x: x[0])

        page_groups = {}
        for page_num, category in results:
            if category not in page_groups:
                page_groups[category] = []
            page_groups[category].append(page_num)

        return page_groups

    def _analyze_page_task(self, pdf_path: str, page_num: int) -> Tuple[int, str]:
        """
        Task atomico per l'analisi di una singola pagina in un thread separato.
        Apre un handle locale al PDF per garantire la thread-safety.
        """
        # Ogni thread deve aprire il proprio handle del documento per sicurezza
        with fitz.open(pdf_path) as doc:
            page = doc.load_page(page_num)
            category = self._analyze_single_page(page)
            return page_num, category

    def _analyze_single_page(self, page: fitz.Page) -> str:
        """
        Analizza una singola pagina con strategia a due stadi:
        1. Controllo veloce di TUTTE le ROI con testo nativo.
        2. Solo se fallisce, controllo robusto con OCR su ROI selezionate (rendering ottimizzato).
        """
        page_rect = page.rect
        
        # --- STADIO 1: FAST PATH (Testo Nativo) ---
        for rule in self.rules:
            keywords = [k.lower() for k in rule.get("keywords", [])]
            category = str(rule.get("category_name", "sconosciuto"))
            
            for roi in rule.get("rois", []):
                if len(roi) != 4: continue
                roi_rect = fitz.Rect(roi)
                if roi_rect.x1 > page_rect.width or roi_rect.y1 > page_rect.height: continue

                try:
                    native_text = page.get_text("text", clip=roi_rect).lower()
                    if any(kw in native_text for kw in keywords):
                        return category
                except Exception: continue

        # --- STADIO 2: ROBUST PATH (OCR) ---
        # Ottimizzazione: identifichiamo tutte le ROI per renderizzare solo l'area necessaria
        all_rois = []
        for rule in self.rules:
            for roi in rule.get("rois", []):
                if len(roi) == 4:
                    all_rois.append(fitz.Rect(roi))
        
        if not all_rois:
            return "sconosciuto"

        # Rettangolo che racchiude tutte le ROI (bounding box)
        clip_rect = all_rois[0]
        for r in all_rois[1:]:
            clip_rect |= r
            
        try:
            # Renderizziamo solo l'area interessata per risparmiare memoria e tempo di CPU
            mat = fitz.Matrix(300 / 72, 300 / 72)
            pix = page.get_pixmap(matrix=mat, colorspace=fitz.csGRAY, clip=clip_rect)
            img_full = Image.frombytes("L", (pix.width, pix.height), pix.samples)
            
            # Calcolo offset e scala per mappare le ROI sulla porzione di immagine renderizzata
            scale = 300 / 72
            off_x = clip_rect.x0 * scale
            off_y = clip_rect.y0 * scale
        except Exception:
            return "sconosciuto"

        for rule in self.rules:
            category = str(rule.get("category_name", "sconosciuto"))
            keywords = rule.get("keywords", [])
            
            for roi in rule.get("rois", []):
                if len(roi) != 4: continue
                roi_rect = fitz.Rect(roi)
                
                # Crop dell'immagine pre-renderizzata con offset del clip_rect
                crop_box = (
                    int(roi_rect.x0 * scale - off_x),
                    int(roi_rect.y0 * scale - off_y),
                    int(roi_rect.x1 * scale - off_x),
                    int(roi_rect.y1 * scale - off_y)
                )
                
                # Validazione crop box
                if crop_box[2] <= crop_box[0] or crop_box[3] <= crop_box[1]: continue
                
                try:
                    # Se il crop esce dai bordi dell'immagine renderizzata (per errori di floating point), clamp
                    left = max(0, crop_box[0])
                    top = max(0, crop_box[1])
                    right = min(img_full.width, crop_box[2])
                    bottom = min(img_full.height, crop_box[3])
                    
                    if right <= left or bottom <= top: continue
                    
                    img_roi = img_full.crop((left, top, right, bottom))
                    found, _ = self.ocr_engine.robust_scan(img_roi, keywords)
                    if found: return category
                except Exception: continue

        return "sconosciuto"
