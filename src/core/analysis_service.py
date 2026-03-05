"""
Servizio per l'analisi e la classificazione delle pagine PDF (SRP).
Utilizza OcrEngine e DocumentClassifier.
Ottimizzato con ThreadPoolExecutor, pre-compilazione regole, OCR per-ROI con early-exit.
"""

import concurrent.futures
import operator
import os
import time
from collections.abc import Callable
from typing import Any

import pymupdf as fitz
from PIL import Image

from core.classifier import DocumentClassifier
from core.ocr_engine import OcrEngine


def _analyze_single_page_standalone(
    page: fitz.Page,
    rules: list[dict[str, Any]],
    ocr_engine: OcrEngine,
) -> str:
    """
    Analizza una singola pagina con strategia ottimizzata a tre stadi.

    1. Fast Path (Testo Nativo): istantaneo.
    2. Medium Path (OCR per-ROI): una chiamata Tesseract per ROI, con early-exit.
    3. Robust Path (OCR Trasformato): solo se necessario, per-ROI.
    """
    try:
        pw = float(page.rect.width)
        ph = float(page.rect.height)
    except (AttributeError, TypeError, ValueError):
        pw, ph = 10000.0, 10000.0

    # Pre-compila keywords per ogni regola (evita .lower() ripetuti)
    compiled_rules: list[tuple[str, list[str], list[fitz.Rect]]] = []
    for rule in rules:
        keywords = [k.lower() for k in rule.get("keywords", [])]
        category = str(rule.get("category_name", "sconosciuto"))
        valid_rois = []
        for roi in rule.get("rois", []):
            if len(roi) != 4:
                continue
            roi_rect = fitz.Rect(roi)
            if roi_rect.x1 <= pw and roi_rect.y1 <= ph:
                valid_rois.append(roi_rect)
        compiled_rules.append((category, keywords, valid_rois))

    # --- STADIO 1: FAST PATH (Testo Nativo) ---
    for category, keywords, rois in compiled_rules:
        for roi_rect in rois:
            try:
                native_text = page.get_text("text", clip=roi_rect).lower()
                if any(kw in native_text for kw in keywords):
                    return category
            except Exception:
                continue

    # --- STADIO 2: OCR PER-ROI (Medium Path) ---
    # OCR su ciascuna ROI individualmente per massima precisione.
    # Early-exit appena troviamo un match.
    scale = 300 / 72
    mat = fitz.Matrix(scale, scale)

    for category, keywords, rois in compiled_rules:
        for roi_rect in rois:
            try:
                pix = page.get_pixmap(matrix=mat, colorspace=fitz.csGRAY, clip=roi_rect)
                if 0 in (pix.width, pix.height):
                    continue
                img = Image.frombytes("L", (pix.width, pix.height), pix.samples)

                text = ocr_engine.scan_image(img)
                if any(kw in text for kw in keywords):
                    return category
            except Exception:
                continue

    # --- STADIO 3: ROBUST PATH (Solo se il Medium Path fallisce) ---
    # Tentativo con trasformazioni (rotazioni, contrasto, binarizzazione) per-ROI.
    for category, keywords, rois in compiled_rules:
        for roi_rect in rois:
            try:
                pix = page.get_pixmap(matrix=mat, colorspace=fitz.csGRAY, clip=roi_rect)
                if 0 in (pix.width, pix.height):
                    continue
                img = Image.frombytes("L", (pix.width, pix.height), pix.samples)

                found, _keyword = ocr_engine.robust_scan(img, keywords)
                if found:
                    return category
            except Exception:
                continue

    return "sconosciuto"


class AnalysisService:
    """Gestisce la logica di scansione intelligente delle pagine con supporto al parallelismo."""

    def __init__(self, rules: list[dict[str, Any]], ocr_engine: OcrEngine):
        """Configura il servizio di analisi con le regole e il motore OCR."""
        self.rules = rules
        self.ocr_engine = ocr_engine
        self.classifier = DocumentClassifier(rules)
        self._page_cache: dict[int, Image.Image] = {}

    def analyze_pdf(
        self, pdf_path: str, progress_callback: Callable | None = None, cancel_check: Callable[[], bool] | None = None,
    ) -> dict[str, list[int]]:
        """
        Scansiona tutte le pagine e restituisce i gruppi di pagine per categoria.
        Usa ThreadPoolExecutor (pytesseract rilascia il GIL durante le chiamate subprocess).
        """
        page_groups: dict[str, list[int]] = {}

        with fitz.open(pdf_path) as doc:
            total_pages = doc.page_count

        if total_pages == 0:
            return {}

        results: list[tuple[int, str]] = []
        start_t_analysis = time.time()

        # Workers: cap a 4 (Tesseract è CPU-intensive, ma rilascia il GIL via subprocess)
        max_workers = min(os.cpu_count() or 4, 4)
        workers = min(max_workers, max(1, total_pages))

        if workers <= 1 or total_pages <= 1:
            # Percorso sequenziale per test e sistemi piccoli — riusa lo stesso doc handle
            with fitz.open(pdf_path) as doc:
                for page_num in range(total_pages):
                    if cancel_check and cancel_check():
                        msg = "Analisi interrotta"
                        raise InterruptedError(msg)

                    page = doc.load_page(page_num)
                    category = _analyze_single_page_standalone(page, self.rules, self.ocr_engine)
                    results.append((page_num, category))

                    if progress_callback:
                        elapsed = time.time() - start_t_analysis
                        avg_time = elapsed / (page_num + 1)
                        eta = avg_time * (total_pages - (page_num + 1))

                        progress_callback(
                            {
                                "type": "page_progress",
                                "current": page_num + 1,
                                "total": total_pages,
                                "phase": "analysis",
                                "phase_pct": ((page_num + 1) / total_pages) * 100,
                                "eta_seconds": eta,
                            },
                        )
        else:
            # Percorso parallelo — ogni thread apre il proprio handle del PDF (thread-safety)
            with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
                future_to_page = {executor.submit(self._analyze_page_task, pdf_path, p): p for p in range(total_pages)}
                for future in concurrent.futures.as_completed(future_to_page):
                    if cancel_check and cancel_check():
                        executor.shutdown(wait=False, cancel_futures=True)
                        msg = "Analisi interrotta"
                        raise InterruptedError(msg)
                    try:
                        results.append(future.result())
                        if progress_callback:
                            pages_processed = len(results)
                            elapsed = time.time() - start_t_analysis
                            avg_time = elapsed / pages_processed
                            eta = avg_time * (total_pages - pages_processed)

                            progress_callback(
                                {
                                    "type": "page_progress",
                                    "current": pages_processed,
                                    "total": total_pages,
                                    "phase": "analysis",
                                    "phase_pct": (pages_processed / total_pages) * 100,
                                    "eta_seconds": eta,
                                },
                            )
                    except Exception:
                        results.append((future_to_page[future], "sconosciuto"))

        # Riordina i risultati e raggruppa
        results.sort(key=operator.itemgetter(0))
        for page_num, category in results:
            page_groups.setdefault(category, []).append(page_num)

        return page_groups

    def _analyze_page_task(self, pdf_path: str, page_num: int) -> tuple[int, str]:
        """
        Task atomico per l'analisi di una singola pagina in un thread separato.
        Apre un handle locale al PDF per garantire la thread-safety.
        """
        with fitz.open(pdf_path) as doc:
            page = doc.load_page(page_num)
            category = _analyze_single_page_standalone(page, self.rules, self.ocr_engine)
            return page_num, category

    def _analyze_single_page(self, page: fitz.Page) -> str:
        """Wrapper per compatibilità — delega alla funzione standalone."""
        return _analyze_single_page_standalone(page, self.rules, self.ocr_engine)
