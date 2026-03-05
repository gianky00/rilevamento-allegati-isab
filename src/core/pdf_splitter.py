"""
Servizio per la divisione fisica e il salvataggio dei file PDF (SRP).
"""
import os
import time
from typing import Any, Dict, List, Optional, Callable
import pymupdf as fitz

class PdfSplitter:
    """Gestisce la creazione di nuovi PDF basandosi su gruppi di pagine."""

    @staticmethod
    def split_and_save(
        pdf_doc: fitz.Document,
        page_groups: Dict[str, List[int]],
        rules: List[Dict[str, Any]],
        output_dir: str,
        odc: str,
        progress_callback: Optional[Callable] = None
    ) -> List[Dict[str, Any]]:
        """Salva i file divisi su disco."""
        generated_files = []
        
        if progress_callback:
            progress_callback({
                "type": "page_progress", "phase": "saving", "phase_pct": 95,
                "current": len(pdf_doc), "total": len(pdf_doc), "eta_seconds": 0
            })

        for category, pages in page_groups.items():
            if not pages: continue
            
            suffix = PdfSplitter._get_suffix(category, rules)
            filename = f"{odc}_.pdf" if category == "sconosciuto" else f"{odc}_{suffix}.pdf"
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
    def _get_suffix(category: str, rules: List[Dict[str, Any]]) -> str:
        """Determina il suffisso del file basandosi sulla categoria e sulle regole."""
        if category == "sconosciuto": return ""
        for r in rules:
            if r.get("category_name") == category:
                return r.get("filename_suffix") or category
        return category

    @staticmethod
    def _get_ranges(pages: List[int]) -> List[tuple]:
        """Raggruppa una lista di indici di pagina in tuple (start, end) consecutive."""
        if not pages: return []
        ranges = []
        start = end = pages[0]
        for p in pages[1:]:
            if p == end + 1: end = p
            else:
                ranges.append((start, end))
                start = end = p
        ranges.append((start, end))
        return ranges

    @staticmethod
    def _safe_save(doc: fitz.Document, path: str, retries: int = 3) -> bool:
        """Tenta il salvataggio del PDF con gestione dei tentativi in caso di file bloccato."""
        for i in range(retries):
            try:
                doc.save(path)
                return True
            except PermissionError:
                time.sleep(1.0)
            except Exception:
                break
        return False
