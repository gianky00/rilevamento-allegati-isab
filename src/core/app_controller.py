"""
Controller principale per la logica dell'applicazione (SRP/SoC).
Gestisce l'elaborazione, le licenze, le sessioni e lo stato applicativo.
"""
import logging
import queue
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable

from PySide6.QtCore import QObject, Signal, QTimer

import config_manager
import license_validator
import license_updater
from core.session_manager import SessionManager
from core.processing_worker import PdfProcessingWorker
from core.rule_service import RuleService
from shared.constants import SIGNAL_FILE

logger = logging.getLogger("CONTROLLER")

class AppController(QObject):
    """
    Controller che separa la logica di business dalla GUI.
    Emette segnali per aggiornare la View.
    """
    
    # Segnali per la View
    log_received = Signal(str, str)  # message, level
    progress_updated = Signal(float, str, object)  # value, text, eta_seconds
    license_status_updated = Signal(dict) # info
    processing_state_changed = Signal(bool) # is_processing
    rules_updated = Signal()
    session_status_changed = Signal(bool) # has_session
    unknown_files_found = Signal(list, str) # files, odc

    def __init__(self) -> None:
        super().__init__()
        self.config: Dict[str, Any] = {}
        self.rule_service: Optional[RuleService] = None
        self.log_queue: queue.Queue = queue.Queue()
        self._is_processing: bool = False
        self.pdf_files: List[str] = []
        
        # Timer per il polling della coda log
        self._log_timer = QTimer()
        self._log_timer.timeout.connect(self._process_log_queue)
        self._log_timer.start(50)

    def load_settings(self) -> None:
        """Carica le impostazioni e inizializza i servizi core."""
        try:
            self.config = config_manager.load_config()
            self.rule_service = RuleService(self.config)
            self.rules_updated.emit()
            self.session_status_changed.emit(SessionManager.has_session())
        except Exception as e:
            logger.error(f"Errore caricamento settings: {e}")

    def save_settings(self) -> None:
        """Salva le impostazioni correnti."""
        try:
            config_manager.save_config(self.config)
        except Exception as e:
            logger.error(f"Errore salvataggio settings: {e}")

    def check_license(self) -> None:
        """Esegue la validazione della licenza e notifica i risultati."""
        try:
            payload = license_validator.get_license_info()
            hw_id = license_validator.get_hardware_id()
            config = config_manager.load_config()
            last_access = str(config.get("last_access", "N/A"))
            
            info = {
                "is_valid": payload is not None,
                "cliente": str(payload.get("Cliente", "N/A")).upper() if payload else "UTENTE NON REGISTRATO",
                "scadenza": str(payload.get("Scadenza Licenza", "N/A")) if payload else "---",
                "hwid": hw_id,
                "last_access": last_access
            }
            self.license_status_updated.emit(info)
        except Exception as e:
            logger.error(f"Errore check licenza: {e}")
            self.license_status_updated.emit({"is_valid": False, "error": str(e)})

    def start_processing(self, pdf_files: List[str], odc: str) -> bool:
        """Avvia il workflow di elaborazione threadata."""
        if self._is_processing:
            return False
            
        self.pdf_files = pdf_files
        self._is_processing = True
        self.processing_state_changed.emit(True)
        
        def on_worker_complete(processed_count: int, unknown_files: List[Any]) -> None:
            self._is_processing = False
            self.processing_state_changed.emit(False)
            if unknown_files:
                self.unknown_files_found.emit(unknown_files, odc)
            self.log_received.emit("ELABORAZIONE COMPLETATA", "HEADER")

        worker = PdfProcessingWorker(
            self.log_queue, 
            list(self.pdf_files), 
            odc, 
            self.config,
            on_worker_complete
        )
        worker.start()
        return True

    def _process_log_queue(self) -> None:
        """Drena la coda dei log e converte gli item in segnali."""
        try:
            while not self.log_queue.empty():
                item = self.log_queue.get_nowait()
                if isinstance(item, tuple):
                    self.log_received.emit(item[0], item[1])
                elif isinstance(item, dict):
                    action = item.get("action")
                    if action == "update_progress":
                        self.progress_updated.emit(
                            float(item.get("value", 0)),
                            str(item.get("text", "")),
                            item.get("eta_seconds")
                        )
                    # Altre azioni possono essere aggiunte qui
        except queue.Empty:
            pass

    def check_for_restore(self) -> None:
        """Verifica se ci sono sessioni da ripristinare."""
        self.session_status_changed.emit(SessionManager.has_session())

    def restore_session(self) -> Optional[tuple]:
        """Carica i dati della sessione salvata."""
        if SessionManager.has_session():
            return SessionManager.load_session()
        return None

    def clear_session(self) -> None:
        """Pulisce la sessione corrente."""
        SessionManager.clear_session()
        self.session_status_changed.emit(False)

    def check_roi_signal(self) -> bool:
        """Verifica se l'utility ROI ha segnalato aggiornamenti."""
        if os.path.exists(SIGNAL_FILE):
            try:
                os.remove(SIGNAL_FILE)
                self.load_settings()
                return True
            except OSError:
                pass
        return False
