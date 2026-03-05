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
import app_updater
from core.session_manager import SessionManager
from core.processing_worker import PdfProcessingWorker
from core.rule_service import RuleService
from core.file_service import FileService
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
        """Inizializza il controller e i servizi core associati."""
        super().__init__()
        self.config: Dict[str, Any] = {}
        self.rule_service: Optional[RuleService] = None
        self.log_queue: queue.Queue = queue.Queue()
        self._is_processing: bool = False
        self.pdf_files: List[str] = []
        self._current_worker: Optional[PdfProcessingWorker] = None
        
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

    def set_pdf_files(self, paths: List[str]) -> None:
        """Imposta la lista dei file da elaborare trovandoli nei percorsi forniti."""
        all_pdfs = []
        for p in paths:
            all_pdfs.extend(FileService.find_pdfs_in_path(p))
        
        self.pdf_files = list(set(all_pdfs)) # Rimuove duplicati
        if self.pdf_files:
            msg = f"{len(self.pdf_files)} file selezionati" if len(self.pdf_files) > 1 else os.path.basename(self.pdf_files[0])
            self.log_received.emit(f"File pronti per elaborazione: {msg}", "INFO")
        else:
            self.log_received.emit("Nessun file PDF trovato nei percorsi indicati", "WARNING")

    def start_processing(self, odc: str) -> bool:
        """Avvia il workflow di elaborazione threadata."""
        if self._is_processing or not self.pdf_files:
            return False
            
        self._is_processing = True
        self.processing_state_changed.emit(True)
        
        def on_worker_complete(processed_count: int, unknown_files: List[Any]) -> None:
            """Callback invocata al termine del thread di elaborazione PDF."""
            self._is_processing = False
            self._current_worker = None
            self.processing_state_changed.emit(False)
            if unknown_files:
                self.unknown_files_found.emit(unknown_files, odc)
            self.log_received.emit("ELABORAZIONE COMPLETATA", "HEADER")

        # Configura timer per drenaggio log se non attivo
        if not self._log_timer.isActive():
            self._log_timer.start(100)

        self._current_worker = PdfProcessingWorker(
            self.log_queue, 
            list(self.pdf_files), 
            odc, 
            self.config,
            on_worker_complete
        )
        self._current_worker.start()
        return True

    def stop_processing(self) -> None:
        """Richiede l'interruzione immediata del processo di elaborazione."""
        if self._current_worker:
            self.log_received.emit("🛑 Richiesta interruzione in corso...", "WARNING")
            self._current_worker.cancel()

    def _process_log_queue(self) -> None:
        """Drena la coda dei log e converte gli item in segnali."""
        try:
            while not self.log_queue.empty():
                item = self.log_queue.get_nowait()
                if isinstance(item, tuple):
                    # Se è un dizionario di progresso impacchettato in una tupla (da AnalysisService)
                    msg, level = item
                    if isinstance(msg, dict) and msg.get("type") == "page_progress":
                        current = msg.get("current", 0)
                        total = msg.get("total", 0)
                        phase = msg.get("phase", "scansione")
                        pct = msg.get("phase_pct", 0)
                        
                        # Log granulare nel terminale per feedback immediato
                        self.log_received.emit(f"  > Pagina {current}/{total} ({phase})", "PROGRESS")
                        
                        # Aggiorna anche la barra di progresso
                        self.progress_updated.emit(pct, f"Analisi: {current}/{total}", msg.get("eta_seconds"))
                    else:
                        self.log_received.emit(str(msg), level)
                elif isinstance(item, dict):
                    action = item.get("action")
                    if action == "update_progress":
                        self.progress_updated.emit(
                            float(item.get("value", 0)),
                            str(item.get("text", "")),
                            item.get("eta_seconds")
                        )
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

    def check_updates(self, silent: bool = True) -> None:
        """Controlla se ci sono aggiornamenti disponibili."""
        app_updater.check_for_updates(silent=silent, on_confirm=self.save_settings)

    def update_last_access(self) -> None:
        """Aggiorna il timestamp dell'ultimo accesso nel file di configurazione."""
        try:
            self.config["last_access"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            config_manager.save_config(self.config)
        except Exception as e:
            logger.error(f"Impossibile aggiornare l'ultimo accesso: {e}")
