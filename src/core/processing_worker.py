"""
Gestisce il workflow di elaborazione threadata, invocando il processore PDF (SRP).
"""

import threading
from collections.abc import Callable
from contextlib import suppress
from datetime import datetime
from pathlib import Path
from queue import Queue
from typing import Any

from core import pdf_processor


class ProcessingWorker:
    """
    Esegue l'elaborazione OCR PDF su un thread separato (Standard OOP).
    Coordina il processore PDF e riporta i progressi tramite una coda log.
    """

    def __init__(
        self,
        pdf_files: list[str],
        odc: str,
        config: dict[str, Any],
        log_queue: Queue,
        on_complete: Callable[[int, int, list[dict[str, Any]]], None] | None = None
    ) -> None:
        """
        Inizializza il worker con la lista dei file e i parametri di elaborazione.

        Args:
            pdf_files (list[str]): Percorsi dei file PDF da processare.
            odc (str): Codice ODC da utilizzare per la denominazione.
            config (dict[str, Any]): Configurazione dell'applicazione.
            log_queue (Queue): Coda per l'invio dei log e dei progressi alla UI.
            on_complete (Callable | None): Callback invocata al termine del lavoro.
        """
        self.log_queue = log_queue
        self.pdf_files = pdf_files
        self.odc = odc
        self.config = config
        self.on_complete = on_complete
        self.processing_start_time: datetime | None = None
        self.files_processed_count = 0
        self.pages_processed_count = 0
        self._is_cancelled = False

    def stop(self) -> None:
        """Richiede l'interruzione immediata del thread di lavoro."""
        self._is_cancelled = True

    def cancel(self) -> None:
        """Alias per stop() richiesto per compatibilità."""
        self.stop()

    def start(self) -> threading.Thread:
        """Avvia il thread di elaborazione e lo restituisce."""
        thread = threading.Thread(target=self.run)
        thread.daemon = True
        thread.start()
        return thread

    def run(self) -> None:
        """Esegue il ciclo di elaborazione principale sui file PDF."""
        self.processing_start_time = datetime.now()
        unknown_files: list[dict[str, Any]] = []
        total_files = len(self.pdf_files)

        for i, pdf_path_str in enumerate(self.pdf_files):
            if self._is_cancelled:
                self.log_queue.put(("Operazione annullata", "WARNING"))
                break

            pdf_path = Path(pdf_path_str)
            self.log_queue.put((f"FILE {i + 1}/{total_files}: {pdf_path.name}", "HEADER"))

            def progress_callback(data: Any, level: str = "INFO") -> None:
                """Invia i progressi dell'elaborazione alla coda log della UI."""
                if isinstance(data, dict):
                    self.log_queue.put(data)
                else:
                    self.log_queue.put((str(data), level))

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
