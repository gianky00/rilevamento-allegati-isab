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
        
        with fitz.open(pdf_path) as doc:
            total_pages = doc.page_count
            
        if total_pages == 0:
            return {}

        results: List[Tuple[int, str]] = []
        start_t_analysis = time.time()

        # Determina il numero di worker ottimale (Capped a 3 per evitare di bloccare il PC)
        # Tesseract è già molto pesante di suo, troppi thread saturano IO e CPU.
        max_workers = 3
        workers = min(max_workers, max(1, (os.cpu_count() or 4) // 2))
        
        if workers <= 1 or total_pages <= 1:
            # Percorso sequenziale per test e sistemi piccoli
            for page_num in range(total_pages):
                if cancel_check and cancel_check():
                    raise InterruptedError("Analisi interrotta")
                
                start_page_t = time.time()
                results.append(self._analyze_page_task(pdf_path, page_num))
                
                if progress_callback:
                    elapsed = time.time() - start_t_analysis
                    avg_time = elapsed / (page_num + 1)
                    eta = avg_time * (total_pages - (page_num + 1))
                    
                    progress_callback({
                        "type": "page_progress", "current": page_num + 1,
                        "total": total_pages, "phase": "analysis",
                        "phase_pct": ((page_num + 1) / total_pages) * 100,
                        "eta_seconds": eta
                    })
        else:
            # Percorso parallelo per massime prestazioni
            with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
                future_to_page = {
                    executor.submit(self._analyze_page_task, pdf_path, p): p 
                    for p in range(total_pages)
                }
                for future in concurrent.futures.as_completed(future_to_page):
                    if cancel_check and cancel_check():
                        executor.shutdown(wait=False, cancel_futures=True)
                        raise InterruptedError("Analisi interrotta")
                    try:
                        results.append(future.result())
                        if progress_callback:
                            pages_processed = len(results)
                            elapsed = time.time() - start_t_analysis
                            avg_time = elapsed / pages_processed
                            eta = avg_time * (total_pages - pages_processed)
                            
                            progress_callback({
                                "type": "page_progress", "current": pages_processed,
                                "total": total_pages, "phase": "analysis",
                                "phase_pct": (pages_processed / total_pages) * 100,
                                "eta_seconds": eta
                            })
                    except Exception:
                        results.append((future_to_page[future], "sconosciuto"))

        # Riordina i risultati e raggruppa
        results.sort(key=lambda x: x[0])
        for page_num, category in results:
            page_groups.setdefault(category, []).append(page_num)

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
        Analizza una singola pagina con strategia ottimizzata a tre stadi:
        1. Fast Path (Testo Nativo): istantaneo.
        2. Medium Path (OCR Pagina Intera): una sola chiamata Tesseract.
        3. Robust Path (OCR Trasformato): solo se necessario.
        """
        try:
            pw = float(page.rect.width)
            ph = float(page.rect.height)
        except (AttributeError, TypeError, ValueError):
            pw, ph = 10000.0, 10000.0

        # --- STADIO 1: FAST PATH (Testo Nativo) ---
        for rule in self.rules:
            keywords = [k.lower() for k in rule.get("keywords", [])]
            category = str(rule.get("category_name", "sconosciuto"))
            
            for roi in rule.get("rois", []):
                if len(roi) != 4: continue
                roi_rect = fitz.Rect(roi)
                if roi_rect.x1 > pw or roi_rect.y1 > ph: continue

                try:
                    native_text = page.get_text("text", clip=roi_rect).lower()
                    if any(kw in native_text for kw in keywords):
                        return category
                except Exception: continue

        # --- STADIO 2: OCR OTTIMIZZATO (Single Pass) ---
        # Invece di fare N chiamate OCR per N regole, facciamo una sola chiamata sull'area delle ROI.
        all_rois = []
        for rule in self.rules:
            for roi in rule.get("rois", []):
                if len(roi) == 4:
                    all_rois.append(fitz.Rect(roi))
        
        if not all_rois:
            return "sconosciuto"

        # Bounding box di tutte le ROI
        clip_rect = all_rois[0]
        for r in all_rois[1:]:
            clip_rect |= r
            
        try:
            scale = 300 / 72
            mat = fitz.Matrix(scale, scale)
            pix = page.get_pixmap(matrix=mat, colorspace=fitz.csGRAY, clip=clip_rect)
            img_combined = Image.frombytes("L", (pix.width, pix.height), pix.samples)
            
            # Scansione singola (Standard 0 gradi)
            full_text = self.ocr_engine.scan_image(img_combined)
            
            # Controllo incrociato rapido su tutte le regole
            for rule in self.rules:
                keywords = [k.lower() for k in rule.get("keywords", [])]
                if any(kw in full_text for kw in keywords):
                    return str(rule.get("category_name", "sconosciuto"))
                    
            # --- STADIO 3: ROBUST PATH (Solo se il Medium Path fallisce) ---
            # Se la scansione standard non ha trovato nulla, proviamo le trasformazioni pesanti (rotazioni, contrasto)
            # ma lo facciamo sempre sull'area combinata per minimizzare le chiamate Tesseract.
            found, keyword = self.ocr_engine.robust_scan(img_combined, [k for r in self.rules for k in r.get("keywords", [])])
            if found:
                # Identifica a quale regola appartiene la keyword trovata
                for rule in self.rules:
                    if keyword in [k.lower() for k in rule.get("keywords", [])]:
                        return str(rule.get("category_name", "sconosciuto"))
        except Exception:
            pass

        return "sconosciuto"
