"""
Intelleo PDF Splitter - Orchestratore Elaborazione
Coordina i servizi di analisi, divisione e archiviazione (SRP).
Ottimizzato: eliminata riapertura doppia del documento PDF.
"""

import os
from collections.abc import Callable
from typing import Any

import pymupdf as fitz

from core.analysis_service import AnalysisService
from core.archive_service import ArchiveService
from core.ocr_engine import OcrEngine
from core.pdf_splitter import PdfSplitter


def process_pdf(
    pdf_path: str,
    odc: str,
    config: dict[str, Any],
    progress_callback: Callable | None = None,
    cancel_check: Callable[[], bool] | None = None,
) -> tuple[bool, str, list[dict[str, Any]], str | None]:
    """Coordina l'intero workflow di elaborazione di un PDF."""

    def _log(msg: str, lvl: str = "INFO"):
        """Invia un messaggio di log tramite la callback di progresso."""
        if progress_callback:
            progress_callback(msg, lvl)

    try:
        if cancel_check and cancel_check():
            return False, "Annullato", [], None

        tesseract_path = config.get("tesseract_path")
        if not (tesseract_path and os.path.isfile(tesseract_path)):
            return False, "Percorso Tesseract non valido", [], None

        _log(f"📄 Elaborazione: {os.path.basename(pdf_path)}")

        # 1. Inizializzazione servizi
        ocr_engine = OcrEngine(tesseract_path)
        analyzer = AnalysisService(config.get("classification_rules", []), ocr_engine)

        # 2. Analisi (il documento viene aperto/chiuso internamente)
        _log("🔍 Analisi Smart in parallelo...")
        page_groups = analyzer.analyze_pdf(pdf_path, progress_callback, cancel_check)

        # 3. Divisione e Salvataggio — apre il documento una sola volta per lo split
        doc = fitz.open(pdf_path)
        _log("💾 Salvataggio file divisi...")
        base_dir = os.path.dirname(pdf_path)
        generated = PdfSplitter.split_and_save(doc, page_groups, analyzer.rules, base_dir, odc, progress_callback)
        doc.close()

        # 4. Archiviazione
        _log("📦 Spostamento in ORIGINALI...")
        moved_path = ArchiveService.archive_original(pdf_path)

        _log("✅ Completato", "SUCCESS")
        return True, "Successo", generated, moved_path

    except Exception as e:
        return False, str(e), [], None
