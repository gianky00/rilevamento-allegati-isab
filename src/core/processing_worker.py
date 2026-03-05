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


class PdfProcessingWorker:
    """Esegue l'elaborazione OCR PDF su un thread separato comunicando via coda thread-safe."""

    def __init__(
        self,
        log_queue: Queue,
        pdf_files: list[str],
        odc: str,
        config: dict[str, Any],
        on_complete: Callable[[int, int, list[dict[str, Any]]], None],
    ):
        """Inizializza il worker con la coda dei log, i file da elaborare e la callback di completamento."""
        self.log_queue = log_queue
        self.pdf_files = pdf_files
        self.odc = odc
        self.config = config
        self.on_complete = on_complete
        self.processing_start_time: datetime | None = None
        self.files_processed_count = 0
        self.pages_processed_count = 0
        self._is_cancelled = False

    def cancel(self) -> None:
        """Richiede l'annullamento dell'elaborazione."""
        self._is_cancelled = True

    def is_cancelled(self) -> bool:
        """Verifica se l'elaborazione è stata annullata."""
        return self._is_cancelled

    def start(self) -> threading.Thread:
        """Avvia il thread in background."""
        thread = threading.Thread(target=self._run)
        thread.daemon = True
        thread.start()
        return thread

    def _run(self) -> None:
        """Loop di elaborazione logico isolato dal front-end GUI."""
        unknown_files: list[dict[str, Any]] = []
        total_files = len(self.pdf_files)

        for i, pdf_path_str in enumerate(self.pdf_files):
            if self._is_cancelled:
                self.log_queue.put(("Operazione annullata dall'utente", "WARNING"))
                break

            def progress_callback(
                message: str, level: str = "INFO", current_idx: int = i, total: int = total_files,
            ) -> None:
                """Gestisce i messaggi di log standard durante l'elaborazione."""
                self.log_queue.put((message, level))
                if "Elaborazione pagina" in message:
                    with suppress(Exception):
                        parts = message.split()
                        for p in parts:
                            if "/" in p:
                                current_page, total_p = p.split("/")
                                page_progress = int(current_page) / int(total_p) * 100
                                file_progress = (current_idx / total) * 100
                                combined = file_progress + (page_progress / total)
                                self.log_queue.put(
                                    {
                                        "action": "update_progress",
                                        "value": combined,
                                        "text": f"File {current_idx + 1}/{total} - Pagina {current_page}/{total_p}",
                                        "eta_seconds": None,
                                    },
                                )
                                break

            def advanced_progress_callback(
                data: Any, level: str = "INFO", current_idx: int = i, total: int = total_files,
            ) -> None:
                """Gestisce messaggi di progresso strutturati (percentuali, ETA) per aggiornare la barra di progresso."""
                if isinstance(data, dict) and data.get("type") == "page_progress":
                    current_page = data.get("current", 0)
                    total_p = data.get("total", 1)
                    eta = data.get("eta_seconds", 0)
                    phase_pct = data.get("phase_pct", 0)
                    phase = data.get("phase", "analysis")

                    # Log granulare per feedback immediato (sostituisce riga per evitare spam)
                    self.log_queue.put(
                        {"text": f"  > Pagina {current_page}/{total_p}", "level": "PROGRESS", "replace_last": True},
                    )

                    file_internal_progress = phase_pct if phase_pct > 0 else (current_page / total_p) * 100
                    base_pct = (current_idx / total) * 100
                    combined = base_pct + (file_internal_progress * (1.0 / total))
                    status_text = f"File {current_idx + 1}/{total}"
                    status_text += " - Salvataggio..." if phase == "saving" else f" - Analisi {current_page}/{total_p}"

                    self.log_queue.put(
                        {"action": "update_progress", "value": combined, "text": status_text, "eta_seconds": eta},
                    )
                elif isinstance(data, dict):
                    self.log_queue.put(data)
                else:
                    progress_callback(str(data), level)

            pdf_path = Path(pdf_path_str)
            self.log_queue.put((f"=== FILE {i + 1}/{total_files}: {pdf_path.name} ===", "HEADER"))
            success, message, generated, moved = pdf_processor.process_pdf(
                str(pdf_path), self.odc, self.config, advanced_progress_callback, self.is_cancelled,
            )

            if not success:
                self.log_queue.put((f"Errore: {message}", "ERROR"))
            else:
                self.files_processed_count += 1
                with suppress(Exception):
                    import pymupdf as fitz

                    with fitz.open(str(pdf_path)) as d:
                        self.pages_processed_count += d.page_count
                self.log_queue.put(("File completato con successo", "SUCCESS"))
                if any(f["category"] == "sconosciuto" for f in generated):
                    unknown_paths = [f["path"] for f in generated if f["category"] == "sconosciuto"]
                    siblings = [f["path"] for f in generated if f["category"] != "sconosciuto"]
                    for u_path in unknown_paths:
                        unknown_files.append({"unknown_path": u_path, "source_path": moved, "siblings": siblings})

        self.log_queue.put({"action": "update_progress", "value": 100, "text": "Completato!"})
        if self.processing_start_time:
            elapsed = datetime.now() - self.processing_start_time
            elapsed_str = str(elapsed).split(".")[0]
        else:
            elapsed_str = "N/A"

        self.log_queue.put(("-" * 60, "INFO"))
        self.log_queue.put((f"ELABORAZIONE COMPLETATA in {elapsed_str}", "HEADER"))
        self.log_queue.put((f"File elaborati: {total_files}", "SUCCESS"))

        # Invia il trigger di fine processo al main thread (GUI)
        self.on_complete(self.files_processed_count, self.pages_processed_count, unknown_files)
