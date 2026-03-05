"""
Servizio per la divisione fisica e il salvataggio dei file PDF (SRP).
Ottimizzato con salvataggio deflate e garbage collection.
"""

import os
import time
from collections.abc import Callable
from typing import Any

import pymupdf as fitz


class PdfSplitter:
    """Gestisce la creazione di nuovi PDF basandosi su gruppi di pagine."""

    @staticmethod
    def split_and_save(
        pdf_doc: fitz.Document,
        page_groups: dict[str, list[int]],
        rules: list[dict[str, Any]],
        output_dir: str,
        odc: str,
        progress_callback: Callable | None = None,
    ) -> list[dict[str, Any]]:
        """Salva i file divisi su disco."""
        generated_files = []

        if progress_callback:
            progress_callback(
                {
                    "type": "page_progress",
                    "phase": "saving",
                    "phase_pct": 95,
                    "current": len(pdf_doc),
                    "total": len(pdf_doc),
                    "eta_seconds": 0,
                },
            )

        # Pre-calcola suffix map per evitare lookup ripetuti
        suffix_map: dict[str, str] = {}
        for rule in rules:
            cat = rule.get("category_name", "")
            suffix_map[cat] = rule.get("filename_suffix") or cat

        for category, pages in page_groups.items():
            if not pages:
                continue

            suffix = suffix_map.get(category, category)
            if category == "sconosciuto":
                # Usa il nome del file originale per evitare collisioni tra più documenti processati
                orig_name = os.path.splitext(os.path.basename(pdf_doc.name))[0]
                filename = f"{odc}_SCONOSCIUTO_{orig_name}.pdf"
            else:
                filename = f"{odc}_{suffix}.pdf"

            path = os.path.join(output_dir, filename)

            new_pdf = fitz.open()
            pages.sort()
            # Raggruppa pagine consecutive per efficienza
            ranges = PdfSplitter._get_ranges(pages)
            for start, end in ranges:
                new_pdf.insert_pdf(pdf_doc, from_page=start, to_page=end)

            if PdfSplitter._safe_save(new_pdf, path):
                generated_files.append({"category": category, "path": os.path.abspath(path)})
            new_pdf.close()

        return generated_files

    @staticmethod
    def _get_ranges(pages: list[int]) -> list[tuple]:
        """Raggruppa una lista di indici di pagina in tuple (start, end) consecutive."""
        if not pages:
            return []
        ranges = []
        start = end = pages[0]
        for p in pages[1:]:
            if p == end + 1:
                end = p
            else:
                ranges.append((start, end))
                start = end = p
        ranges.append((start, end))
        return ranges

    @staticmethod
    def _safe_save(doc: fitz.Document, path: str, retries: int = 3) -> bool:
        """Tenta il salvataggio del PDF con deflate e garbage collection."""
        for _i in range(retries):
            try:
                # deflate=True: compressione stream, garbage=3: rimuove oggetti orfani + compatta xref
                doc.save(path, deflate=True, garbage=3)
                return True
            except PermissionError:
                time.sleep(1.0)
            except Exception:
                break
        return False
