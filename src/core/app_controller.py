"""
Controller principale per la logica dell'applicazione (SRP/SoC).
Gestisce l'elaborazione, le licenze, le sessioni e lo stato applicativo.
"""

import logging
import queue
from contextlib import suppress
from datetime import datetime
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, QTimer, Signal

import app_updater
import license_validator
from config_manager import ConfigManager  # Import esplicito per i test
from core.file_service import FileService
from core.processing_worker import ProcessingWorker
from core.rule_service import RuleService
from core.session_manager import SessionManager

logger = logging.getLogger("CONTROLLER")


class AppController(QObject):
    """
    Controller che separa la logica di business dalla GUI.
    Emette segnali per aggiornare la View e coordina i servizi core.
    """

    # Segnali per la View
    log_received = Signal(str, str, bool)  # message, level, replace_last
    progress_updated = Signal(float, str, object)  # value, text, eta_seconds
    license_status_updated = Signal(dict)  # info
    processing_state_changed = Signal(bool)  # is_processing
    rules_updated = Signal()
    session_status_changed = Signal(bool)  # has_session
    unknown_files_found = Signal(list, str)  # files, odc
    stats_updated = Signal(int, int, int, int)  # session_docs, session_pages, global_docs, global_pages

    def __init__(self) -> None:
        """Inizializza il controller e i servizi core associati."""
        super().__init__()
        self.config: dict[str, Any] = {}
        self.rule_service: RuleService | None = None
        self.log_queue: queue.Queue = queue.Queue()
        self._is_processing: bool = False
        self.pdf_files: list[str] = []
        self._current_worker: ProcessingWorker | None = None
        self.session_docs = 0
        self.session_pages = 0

        # Timer per il polling della coda log
        self._log_timer = QTimer()
        self._log_timer.timeout.connect(self.process_log_queue)  # Allineato ai test
        self._log_timer.start(50)

    def load_settings(self) -> None:
        """Carica le impostazioni e inizializza i servizi core."""
        try:
            self.config = ConfigManager.load_config()
            self.rule_service = RuleService(self.config)
            self.rules_updated.emit()
            self.emit_stats()
        except Exception as e:
            logger.exception(f"Errore caricamento settings: {e}")

    def save_settings(self) -> None:
        """Salva le impostazioni correnti nel file di configurazione."""
        try:
            ConfigManager.save_config(self.config)
        except Exception as e:
            logger.exception(f"Errore salvataggio settings: {e}")

    def check_license(self) -> None:
        """Esegue la validazione della licenza locale e notifica i risultati alla View."""
        try:
            payload = license_validator.get_license_info()
            hw_id = license_validator.get_hardware_id()
            config = ConfigManager.load_config()
            last_access = str(config.get("last_access", "N/A"))

            info = {
                "is_valid": payload is not None,
                "cliente": str(payload.get("Cliente", "N/A")).upper() if payload else "UTENTE NON REGISTRATO",
                "scadenza": str(payload.get("Scadenza Licenza", "N/A")) if payload else "---",
                "hwid": hw_id,
                "last_access": last_access,
            }
            self.license_status_updated.emit(info)
        except Exception as e:
            logger.exception(f"Errore check licenza locale: {e}")
            self.license_status_updated.emit({"is_valid": False, "error": str(e)})

    def check_license_online(self, silent: bool = True) -> bool:
        """Esegue un controllo online (run_update) della licenza."""
        try:
            import license_updater
            license_updater.run_update()
            self.check_license()
            return True
        except Exception as e:
            from license_updater import LicenseRevokedError
            if isinstance(e, LicenseRevokedError):
                logger.critical(f"CONTROLLO ONLINE: LICENZA REVOCATA: {e}")
                self.log_received.emit(str(e), "ERROR", False)
                self.license_status_updated.emit({"is_valid": False, "revoked": True, "message": str(e)})
                return False
            if not silent:
                self.log_received.emit(f"Errore aggiornamento licenza: {e}", "WARNING", False)
            return True

    def set_pdf_files(self, paths: list[str]) -> None:
        """Imposta la lista dei file da elaborare trovandoli nei percorsi forniti."""
        all_pdfs = []
        for p in paths:
            all_pdfs.extend(FileService.find_pdfs_in_path(p))

        self.pdf_files = list(set(all_pdfs))
        if self.pdf_files:
            msg = f"{len(self.pdf_files)} file selezionati" if len(self.pdf_files) > 1 else Path(self.pdf_files[0]).name
            self.log_received.emit(f"File pronti per elaborazione: {msg}", "INFO", False)
        else:
            self.log_received.emit("Nessun file PDF trovato nei percorsi indicati", "WARNING", False)

    def start_processing(self, odc: str) -> bool:
        """Avvia il workflow di elaborazione threadata previa verifica licenza."""
        if self._is_processing or not self.pdf_files:
            return False

        self.log_received.emit("Verifica autorizzazioni in corso...", "INFO", False)
        if not self.check_license_online(silent=True):
            return False

        self._is_processing = True
        self.processing_state_changed.emit(True)

        def on_worker_complete(processed_docs: int, processed_pages: int, unknown_files: list[Any]) -> None:
            """Callback invocata al termine dell'elaborazione per aggiornare statistiche e View."""
            self._is_processing = False
            self._current_worker = None
            self.processing_state_changed.emit(False)
            self.session_docs += processed_docs
            self.session_pages += processed_pages
            self.config["global_docs"] = self.config.get("global_docs", 0) + processed_docs
            self.config["global_pages"] = self.config.get("global_pages", 0) + processed_pages
            self.save_settings()
            self.emit_stats()
            if unknown_files:
                self.unknown_files_found.emit(unknown_files, odc)
            self.log_received.emit("ELABORAZIONE COMPLETATA", "HEADER", False)

        self._current_worker = ProcessingWorker(
            pdf_files=self.pdf_files.copy(),
            odc=odc,
            config=self.config,
            log_queue=self.log_queue,
            on_complete=on_worker_complete
        )
        self._current_worker.start()
        return True

    def stop_processing(self) -> None:
        """Richiede l'interruzione immediata dell'elaborazione in corso."""
        if self._current_worker:
            self.log_received.emit("🛑 Richiesta interruzione...", "WARNING", False)
            self._current_worker.stop()

    def process_log_queue(self) -> None:
        """Drena la coda dei messaggi provenienti dal worker e aggiorna la View."""
        try:
            while not self.log_queue.empty():
                item = self.log_queue.get_nowait()
                if isinstance(item, tuple):
                    msg, level = item
                    self.log_received.emit(str(msg), level, False)
                elif isinstance(item, dict):
                    # Gestione progresso (supporta sia il formato 'action' che il nuovo 'page_progress')
                    is_progress = item.get("action") == "update_progress" or item.get("type") == "page_progress"

                    if is_progress:
                        val = item.get("value") or item.get("phase_pct", 0)
                        phase = str(item.get("phase", "Elaborazione")).capitalize()
                        current = item.get("current", 0)
                        total = item.get("total", 0)

                        # Se non c'è un testo esplicito, ne generiamo uno leggibile
                        txt = item.get("text")
                        if not txt and current and total:
                            txt = f"{phase}... ({current}/{total})"
                        elif not txt:
                            txt = f"{phase}..."

                        self.progress_updated.emit(float(val), str(txt), item.get("eta_seconds"))
                    else:
                        self.log_received.emit(str(item.get("text", item)), "INFO", False)
        except queue.Empty:
            pass

    def check_for_restore(self) -> None:
        """Verifica se esiste una sessione salvata e notifica la View."""
        self.session_status_changed.emit(SessionManager.has_session())

    def restore_session(self) -> tuple[list[dict[str, Any]], str] | None:
        """Recupera i dati di una sessione precedentemente interrotta."""
        return SessionManager.load_session() if SessionManager.has_session() else None

    def clear_session(self) -> None:
        """Rimuove definitivamente la sessione salvata."""
        SessionManager.clear_session()
        self.session_status_changed.emit(False)

    def check_roi_signal(self) -> bool:
        """Controlla se l'utility ROI ha inviato un segnale di aggiornamento regole."""
        from shared.constants import SIGNAL_FILE
        signal_path = Path(SIGNAL_FILE)
        if signal_path.exists():
            with suppress(OSError):
                signal_path.unlink()
                self.load_settings()
                return True
        return False

    def check_updates(self, silent: bool = True) -> None:
        """Controlla la presenza di aggiornamenti dell'applicazione."""
        app_updater.check_for_updates(silent=silent, on_confirm=self.save_settings)

    def emit_stats(self) -> None:
        """Emette i segnali con le statistiche aggiornate (globali e sessione)."""
        g_docs = self.config.get("global_docs", 0)
        g_pages = self.config.get("global_pages", 0)
        self.stats_updated.emit(self.session_docs, self.session_pages, g_docs, g_pages)

    def update_last_access(self) -> None:
        """Registra la data e l'ora correnti come ultimo accesso nella configurazione."""
        try:
            self.config["last_access"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            ConfigManager.save_config(self.config)
        except Exception as e:
            logger.exception(f"Impossibile aggiornare last access: {e}")
