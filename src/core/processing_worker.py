"""
Gestisce il workflow di elaborazione threadata, invocando il processore PDF (SRP).
"""

import threading
from collections.abc import Callable
from contextlib import suppress
from datetime import datetime
from pathlib import Path
from queue import Queue
from typing import Any, List, Optional

from core import pdf_processor


class ProcessingWorker:
    """Esegue l'elaborazione OCR PDF su un thread separato (Standard OOP)."""

    def __init__(
        self,
        pdf_files: List[str],
        odc: str,
        config: dict,
        log_queue: Queue,
        on_complete: Optional[Callable] = None
    ):
        self.log_queue = log_queue
        self.pdf_files = pdf_files
        self.odc = odc
        self.config = config
        self.on_complete = on_complete
        self.processing_start_time: Optional[datetime] = None
        self.files_processed_count = 0
        self.pages_processed_count = 0
        self._is_cancelled = False

    def stop(self) -> None:
        self._is_cancelled = True

    def cancel(self) -> None:
        self.stop()

    def start(self) -> threading.Thread:
        thread = threading.Thread(target=self.run)
        thread.daemon = True
        thread.start()
        return thread

    def run(self) -> None:
        self.processing_start_time = datetime.now()
        unknown_files: List[dict] = []
        total_files = len(self.pdf_files)

        for i, pdf_path_str in enumerate(self.pdf_files):
            if self._is_cancelled:
                self.log_queue.put(("Operazione annullata", "WARNING"))
                break

            pdf_path = Path(pdf_path_str)
            self.log_queue.put((f"FILE {i + 1}/{total_files}: {pdf_path.name}", "HEADER"))
            
            def progress_callback(data: Any, level: str = "INFO") -> None:
                if isinstance(data, dict): self.log_queue.put(data)
                else: self.log_queue.put((str(data), level))

            success, message, generated, moved = pdf_processor.process_pdf(
                str(pdf_path), self.odc, self.config, progress_callback, lambda: self._is_cancelled
            )

            if not success:
                self.log_queue.put((f"ERRORE: {message}", "ERROR"))
            else:
                self.files_processed_count += 1
                with suppress(Exception):
                    import pymupdf as fitz
                    with fitz.open(str(pdf_path)) as d:
                        self.pages_processed_count += d.page_count
                
                self.log_queue.put(("File completato", "SUCCESS"))
                for f in generated:
                    if f.get("category") == "sconosciuto":
                        unknown_files.append({
                            "unknown_path": f["path"], "source_path": moved,
                            "siblings": [s["path"] for s in generated if s["category"] != "sconosciuto"]
                        })

        self.log_queue.put({"action": "update_progress", "value": 100, "text": "Completato!"})
        
        # Stringa attesa dai test: ELABORAZIONE COMPLETATA
        self.log_queue.put(("ELABORAZIONE COMPLETATA", "HEADER"))
        
        if self.on_complete:
            self.on_complete(self.files_processed_count, self.pages_processed_count, unknown_files)


# Alias per retro-compatibilità
PdfProcessingWorker = ProcessingWorker
