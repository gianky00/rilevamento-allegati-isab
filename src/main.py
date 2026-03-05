"""
Intelleo PDF Splitter - Applicazione Principale (View)
Gestisce l'interfaccia grafica e coordina l'interazione tra utente e controller.
"""

import logging

logger = logging.getLogger("MAIN")

# Ora importa il resto
try:
    logger.info("Importazione moduli PySide6...")
    from PySide6.QtCore import QTimer
    from PySide6.QtGui import QBrush, QColor, QIcon
    from PySide6.QtWidgets import (
        QFileDialog,
        QInputDialog,
        QLabel,
        QLineEdit,
        QMainWindow,
        QMessageBox,
        QProgressBar,
        QPushButton,
        QTabWidget,
        QTextEdit,
        QTreeWidget,
        QTreeWidgetItem,
        QVBoxLayout,
        QWidget,
    )

    logger.info("Importazione moduli applicazione...")
    import os
    import queue
    import sys

    import version

    logger.info("Importazione PyMuPDF...")
    from datetime import datetime
    from typing import Any

    import roi_utility
    from core.app_controller import AppController

    # Core Managers (SRP)
    from core.tesseract_manager import TesseractManager
    from gui.dialogs.rule_editor import RuleEditorDialog
    from gui.dialogs.unknown_review import UnknownFilesReviewDialog
    from gui.tabs.config_tab import ConfigTab
    from gui.tabs.dashboard_tab import DashboardTab
    from gui.tabs.help_tab import HelpTab

    # Moduli estratti
    from gui.theme import COLORS, GLOBAL_QSS

    logger.info("Tutti i moduli importati con successo")
except Exception as e:
    logger.critical(f"Errore durante l'importazione dei moduli: {e}", exc_info=True)


class MainApp(QMainWindow):
    """Finestra principale dell'applicazione Intelleo PDF Splitter."""

    def __init__(self, auto_file_path: str | None = None) -> None:
        """
        Inizializza la finestra principale, carica i parametri e configura la GUI.

        Args:
            auto_file_path: Percorso di un file PDF da elaborare all'avvio.
        """
        super().__init__()
        logger.info("Inizializzazione MainApp...")
        self.setWindowTitle(f"Intelleo PDF Splitter v{version.__version__}")
        self.resize(1100, 800)
        self.setStyleSheet(GLOBAL_QSS)
        self.setup_icon()

        self.config: dict[str, Any] = {}
        self.pdf_files: list[str] = []
        self.log_queue: queue.Queue = queue.Queue()
        self.processing_start_time: datetime | None = None
        self.files_processed_count: int = 0
        self.pages_processed_count: int = 0
        self._target_progress: float = 0.0
        self._current_progress: float = 0.0
        self._spinner_frames: list[str] = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self._spinner_idx: int = 0
        self._is_processing: bool = False
        self._pending_completion_data: dict[str, Any] | None = None
        self._is_initial_session_check: bool = True
        self._roi_window: roi_utility.ROIDrawingApp | None = None
        self._remaining_eta: float = 0.0

        # Widget UI (Inizializzati dalle Tab)
        self.dashboard: Any = None
        self.processing: Any = None
        self.config_panel: Any = None
        self.help_panel: Any = None
        self.license_status_label: QLabel
        self.license_fields: dict[str, QLabel] = {}
        self.files_count_sess_label: QLabel
        self.files_count_tot_label: QLabel
        self.pages_count_sess_label: QLabel
        self.pages_count_tot_label: QLabel
        self.rules_count_label: QLabel
        self.recent_log: QTextEdit
        self.log_area: QTextEdit
        self.odc_entry: QLineEdit
        self.pdf_path_label: QLabel
        self.progress_label: QLabel
        self.eta_label: QLabel
        self.progress_bar: QProgressBar
        self.spinner_label: QLabel
        self.rules_tree: QTreeWidget
        self.keywords_text: QTextEdit
        self.roi_details_label: QLabel
        self.tesseract_path_entry: QLineEdit
        self.restore_btn: QPushButton

        # Controller e Notifiche
        self.controller = AppController()
        self.notifier: Any | None = None
        try:
            from core import notification_manager

            self.notifier = notification_manager.NotificationManager(self)
        except Exception as e:
            logger.error(f"Errore inizializzazione notifiche: {e}")

        self._connect_controller_signals()

        logger.info("Configurazione UI...")
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(15, 15, 15, 15)

        self.notebook = QTabWidget()
        main_layout.addWidget(self.notebook)

        # —————— Tab Initialization ——————
        self.dashboard = DashboardTab(self.notebook, self)
        self.config_panel = ConfigTab(self.notebook, self)
        self.help_panel = HelpTab(self.notebook, self)

        self.dashboard_tab = self.dashboard
        self.processing_tab = self.dashboard # Puntiamo alla dashboard per compatibilità
        self.config_tab = self.config_panel
        self.help_tab = self.help_panel

        self.notebook.addTab(self.dashboard, "Dashboard")
        self.notebook.addTab(self.config_panel, "Configurazione")
        self.notebook.addTab(self.help_panel, "Guida")

        # —————— Final Initialization ——————
        self.load_settings()
        self._display_license_info()
        self._populate_rules_tree()
        self.update_last_access()

        # Timers (Solo quelli UI-only)
        self._update_timer = QTimer(self)
        self._update_timer.timeout.connect(self._check_for_updates)
        self._update_timer.start(150)

        self._progress_timer = QTimer(self)
        self._progress_timer.timeout.connect(self._smooth_progress_tick)
        self._progress_timer.start(30)

        self._spinner_timer = QTimer(self)
        self._spinner_timer.timeout.connect(self._spinner_tick)
        self._spinner_timer.start(100)

        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._update_clock)
        self._clock_timer.start(1000)

        QTimer.singleShot(500, self.controller.check_for_restore)
        QTimer.singleShot(3000, lambda: self.controller.check_updates(silent=True))

        if auto_file_path and os.path.exists(auto_file_path):
            QTimer.singleShot(500, lambda: self._handle_cli_start(auto_file_path))
        logger.info("MainApp inizializzata con successo")

    def _connect_controller_signals(self) -> None:
        """Collega i segnali del controller agli slot della UI."""
        self.controller.log_received.connect(self._add_log_message)
        self.controller.progress_updated.connect(self._on_progress_update)
        self.controller.license_status_updated.connect(self._on_license_updated)
        self.controller.processing_state_changed.connect(self._on_processing_state_changed)
        self.controller.rules_updated.connect(self._on_rules_updated)
        self.controller.session_status_changed.connect(self._update_restore_button_state)
        self.controller.unknown_files_found.connect(self._show_unknown_dialog)
        self.controller.stats_updated.connect(self._on_stats_updated)

    def _on_stats_updated(self, session_docs: int, session_pages: int, global_docs: int, global_pages: int) -> None:
        """Aggiorna le card statistiche nella dashboard con valori di sessione e globali."""
        if hasattr(self, "files_count_sess_label"):
            self.files_count_sess_label.setText(str(session_docs))
        if hasattr(self, "files_count_tot_label"):
            self.files_count_tot_label.setText(str(global_docs))

        if hasattr(self, "pages_count_sess_label"):
            self.pages_count_sess_label.setText(str(session_pages))
        if hasattr(self, "pages_count_tot_label"):
            self.pages_count_tot_label.setText(str(global_pages))

    def _on_rules_updated(self) -> None:
        """Aggiorna l'interfaccia utente quando le regole di classificazione cambiano."""
        rs = self.controller.rule_service
        if not rs:
            return
        self._populate_rules_tree()
        if hasattr(self, "rules_count_label"):
            self.rules_count_label.setText(str(len(rs.get_rules())))

    def _on_processing_state_changed(self, is_processing: bool) -> None:
        """Aggiorna lo stato interno di elaborazione e la visibilità dei controlli."""
        self._is_processing = is_processing

        # Gestione visibilità/abilitazione bottoni
        if hasattr(self, "stop_btn"):
            self.stop_btn.setVisible(is_processing)

        if hasattr(self, "dashboard_start_btn"):
            self.dashboard_start_btn.setEnabled(not is_processing)

        if hasattr(self, "select_pdf_btn"):
            self.select_pdf_btn.setEnabled(not is_processing)

        if hasattr(self, "select_folder_btn"):
            self.select_folder_btn.setEnabled(not is_processing)

        if hasattr(self, "odc_entry"):
            self.odc_entry.setEnabled(not is_processing)

        # UI updates if needed
        if not is_processing:
            self._finalize_processing()

    def _on_license_updated(self, info: dict[str, Any]) -> None:
        """Aggiorna i widget della licenza con le informazioni ricevute dal controller."""
        if info.get("is_valid"):
            self.license_status_label.setText("✓ SISTEMA ATTIVO")
            self.license_status_label.setStyleSheet(f"color: {COLORS['success']}; border: none;")
        else:
            self.license_status_label.setText("⚠ NON LICENZIATO")
            self.license_status_label.setStyleSheet(f"color: {COLORS['warning']}; border: none;")

        self.license_fields["cliente"].setText(info.get("cliente", "---"))
        self.license_fields["scadenza"].setText(info.get("scadenza", "---"))
        self.license_fields["hwid"].setText(info.get("hwid", "---"))
        self.license_fields["last_access"].setText(info.get("last_access", "---"))

    def _on_progress_update(self, value: float, text: str, eta_seconds: int | None) -> None:
        """Aggiorna i widget di progresso durante l'elaborazione."""
        self._target_progress = value
        self.progress_label.setText(text)

        if eta_seconds is not None:
            new_eta = float(eta_seconds)

            # Se siamo nelle fasi finali ma ancora in elaborazione, garantiamo un minimo di 1s
            if self._target_progress > 90.0 and new_eta < 1.0 and self._is_processing:
                new_eta = 1.0

            # Smoothing asimmetrico: molto lento a salire, reattivo a scendere
            if self._remaining_eta <= 0 or self._current_progress <= 1.0:
                self._remaining_eta = new_eta
            else:
                if new_eta > self._remaining_eta:
                    # Sale molto lentamente (pesa solo il 5% il nuovo valore)
                    self._remaining_eta = (0.05 * new_eta) + (0.95 * self._remaining_eta)
                else:
                    # Scende normalmente (pesa il 20%)
                    self._remaining_eta = (0.2 * new_eta) + (0.80 * self._remaining_eta)

            self._refresh_eta_label()

    def _refresh_eta_label(self) -> None:
        """Aggiorna graficamente la label dell'ETA basandosi sul valore interno."""
        if self._is_processing:
            # Garantiamo che il tempo sia almeno 1s finché non finisce
            display_eta = max(1, int(self._remaining_eta))
            m, s = divmod(display_eta, 60)
            self.eta_label.setText(f"Tempo stimato: {m}m {s}s" if m > 0 else f"Tempo stimato: {s}s")
            self.eta_label.setStyleSheet(f"color: {COLORS['accent']};")
        else:
            self.eta_label.setText("")

    def setup_icon(self) -> None:
        """Configura l'icona della finestra."""
        try:
            icon_path = os.path.join(os.path.dirname(__file__), "resources", "icon.ico")
            if hasattr(sys, "_MEIPASS"):
                icon_path = os.path.join(sys._MEIPASS, "resources", "icon.ico")
            if os.path.exists(icon_path):
                self.setWindowIcon(QIcon(icon_path))
        except Exception as e:
            logger.warning(f"Impossibile caricare icona: {e}")

    # ======== DASHBOARD ========
    def _update_clock(self) -> None:
        """Aggiorna l'orologio della dashboard e decrementa l'ETA se attivo."""
        now = datetime.now()
        if hasattr(self, "dashboard"):
            self.dashboard.clock_label.setText(now.strftime("%d %b %Y | %H:%M:%S"))

        # Gestione decremento ETA ogni secondo
        if self._is_processing and self._remaining_eta > 0:
            self._remaining_eta = max(0, self._remaining_eta - 1)
            self._refresh_eta_label()

    def _quick_select_pdf(self) -> None:
        """Apre una scelta rapida tra file o cartella direttamente dalla dashboard."""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Nuova Analisi")
        msg_box.setText("Cosa desideri elaborare?")
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel)
        msg_box.button(QMessageBox.StandardButton.Yes).setText("File PDF")
        msg_box.button(QMessageBox.StandardButton.No).setText("Intera Cartella")
        msg_box.button(QMessageBox.StandardButton.Cancel).setText("Annulla")
        
        reply = msg_box.exec()
        
        if reply == QMessageBox.StandardButton.Yes:
            self._select_pdf()
        elif reply == QMessageBox.StandardButton.No:
            self._select_folder()

    # ======== COMMON UI HELPERS (STUBS) ========
    def _update_ui_file_selection(self) -> None:
        """Aggiorna le label basandosi sullo stato del controller."""
        count = len(self.controller.pdf_files)
        if count == 0:
            self.pdf_path_label.setText("Nessun file selezionato")
        elif count == 1:
            self.pdf_path_label.setText(os.path.basename(self.controller.pdf_files[0]))
        else:
            self.pdf_path_label.setText(f"{count} file selezionati")

    def _select_pdf(self) -> None:
        """Apre il selettore di file PDF."""
        paths, _ = QFileDialog.getOpenFileNames(self, "Seleziona file PDF", "", "PDF Files (*.pdf)")
        if paths:
            self.controller.set_pdf_files(paths.copy())
            self._update_ui_file_selection()
            self._start_processing()

    def _select_folder(self) -> None:
        """Apre il selettore di cartelle per trovare file PDF."""
        folder = QFileDialog.getExistingDirectory(self, "Seleziona Cartella")
        if folder:
            self.controller.set_pdf_files([folder])
            self._update_ui_file_selection()
            self.notebook.setCurrentWidget(self.processing_tab)
            self._start_processing()

    def _on_drop(self, files: list[str]) -> None:
        """Gestisce il drag-and-drop di file sulla GUI."""
        if files:
            self.controller.set_pdf_files(files)
            self._update_ui_file_selection()
            self.notebook.setCurrentWidget(self.processing_tab)
            self._start_processing()

    def _handle_cli_start(self, path: str) -> None:
        """Inizializza l'elaborazione se un file viene passato come argomento CLI."""
        self.controller.set_pdf_files([path])
        if not self.controller.pdf_files:
            QMessageBox.critical(self, "Errore", "Nessun file PDF trovato nel percorso indicato.")
            return

        self._update_ui_file_selection()
        odc, ok = QInputDialog.getText(self, "Input ODC", "Inserisci il codice ODC:")
        if ok and odc:
            self.odc_entry.setText(odc)
            self.notebook.setCurrentWidget(self.processing_tab)
            self._start_processing()

    # ======== BUSINESS LOGIC ========
    def _display_license_info(self) -> None:
        """Delega il controllo licenza al controller."""
        self.controller.check_license()

    def _add_log_message(self, message: str, level: str = "INFO", replace_last: bool = False) -> None:
        """Aggiunge (o sostituisce) un messaggio al terminale e al log di elaborazione."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        color_map = {
            "ERROR": COLORS["danger"],
            "WARNING": "#E67E22",
            "SUCCESS": COLORS["success"],
            "PROGRESS": COLORS["accent"],
            "HEADER": COLORS["accent"],
        }
        prefix_map = {"ERROR": "[X] ", "WARNING": "[!] ", "SUCCESS": "[OK] ", "HEADER": "=== "}
        prefix = prefix_map.get(level, "")
        color = color_map.get(level, COLORS["text_primary"])
        formatted_message = f'<span style="color:{color}">[{timestamp}] {prefix}{message}</span>'

        if replace_last:
            # Sostituisce l'ultima riga (utile per PROGRESS continui)
            cursor = self.log_area.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            cursor.select(cursor.SelectionType.BlockUnderCursor)
            cursor.removeSelectedText()
            self.log_area.append(formatted_message)
        else:
            self.log_area.append(formatted_message)

        if level in ("SUCCESS", "ERROR", "WARNING"):
            self.recent_log.append(f'<span style="color:{color}">[{timestamp}] {message}</span>')

    def _smooth_progress_tick(self) -> None:
        """Aggiorna la barra di progresso con un'animazione fluida."""
        # Se siamo già quasi al target, settiamo direttamente per evitare oscillazioni o rallentamenti
        if abs(self._current_progress - self._target_progress) < 0.1:
            if self._current_progress != self._target_progress:
                self._current_progress = self._target_progress
                self.progress_bar.setValue(int(self._current_progress * 10))
            return

        # Animazione più veloce (0.3 invece di 0.2)
        step = (self._target_progress - self._current_progress) * 0.3
        self._current_progress += step
        self.progress_bar.setValue(int(self._current_progress * 10))

    def _finalize_processing(self) -> None:
        """Completa le operazioni post-elaborazione."""
        self._is_processing = False
        self._current_progress = 100.0
        self._remaining_eta = 0.0
        self.progress_bar.setValue(1000)
        self._refresh_eta_label()

    def _spinner_tick(self) -> None:
        """Aggiorna lo spinner di caricamento."""
        if self._is_processing:
            self._spinner_idx = (self._spinner_idx + 1) % len(self._spinner_frames)
            self.spinner_label.setText(self._spinner_frames[self._spinner_idx])
        else:
            self.spinner_label.setText("")

    def _check_for_updates(self) -> None:
        """Controlla segnali esterni tramite il controller."""
        if self.controller.check_roi_signal():
            self._add_log_message("Configurazione sincronizzata", "SUCCESS")

    def update_last_access(self) -> None:
        """Delega l'aggiornamento dell'ultimo accesso al controller."""
        self.controller.update_last_access()

    def _update_restore_button_state(self, has_session: bool) -> None:
        """Aggiorna lo stato del pulsante di ripristino sessione."""
        self.restore_btn.setEnabled(has_session)
        if self._is_initial_session_check and has_session:
            self._is_initial_session_check = False
            reply = QMessageBox.question(
                self,
                "Ripristino Sessione",
                "Trovata una sessione precedente non completata.\nVuoi ripristinare i file da revisionare?",
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._restore_session()
            else:
                logger.info("Utente ha rifiutato il ripristino sessione. Pulizia in corso...")
                self.controller.clear_session()
        elif self._is_initial_session_check:
            self._is_initial_session_check = False

    def _clear_session(self) -> None:
        """Delega cancellazione sessione."""
        self.controller.clear_session()

    def _restore_session(self) -> None:
        """Ripristina sessione tramite controller."""
        data = self.controller.restore_session()
        if data:
            self._show_unknown_dialog(data[0], data[1])
        else:
            self._add_log_message("Nessuna sessione da ripristinare", "WARNING")

    def _start_processing(self) -> None:
        """Avvia elaborazione tramite controller."""
        odc = self.odc_entry.text().strip()
        if not odc or not self.controller.pdf_files:
            QMessageBox.warning(self, "Errore", "Verificare ODC e file selezionati.")
            return

        self.log_area.clear()
        self.processing_start_time = datetime.now()

        # Reset progress state
        self._target_progress = 0.0
        self._current_progress = 0.0
        self.progress_bar.setValue(0)
        self.progress_label.setText("Inizializzazione...")
        self.eta_label.setText("")

        self.controller.start_processing(odc)

    def _stop_processing(self) -> None:
        """Interrompe l'elaborazione corrente via controller."""
        reply = QMessageBox.question(
            self,
            "Conferma Stop",
            "Sei sicuro di voler interrompere l'elaborazione corrente?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.controller.stop_processing()

    def _show_unknown_dialog(self, files: list[Any], odc: str) -> None:
        """Visualizza il dialog di revisione per i file non classificati."""
        if not files:
            return

        def on_close() -> None:
            """Callback eseguita alla chiusura positiva del dialog."""
            self._add_log_message("Revisione file sconosciuti completata", "SUCCESS")
            QTimer.singleShot(100, self._update_restore_button_state)

        def on_dialog_closed() -> None:
            """Callback eseguita alla chiusura (anche annullamento) del dialog."""
            QTimer.singleShot(100, self._update_restore_button_state)

        dlg = UnknownFilesReviewDialog(self, files, on_finish=on_close, odc=odc, on_close_callback=on_dialog_closed)
        dlg.exec()

    def load_settings(self) -> None:
        """Delega caricamento al controller."""
        self.controller.load_settings()
        if hasattr(self, "tesseract_path_entry"):
            self.tesseract_path_entry.setText(self.controller.config.get("tesseract_path", ""))
        self._populate_rules_tree()

    def _auto_save_settings(self) -> None:
        """Salva tramite controller."""
        self.controller.save_settings()

    def _populate_rules_tree(self) -> None:
        """Popola l'albero delle regole nella UI."""
        rs = self.controller.rule_service
        if not hasattr(self, "rules_tree") or not rs:
            return
        self.keywords_text.clear()
        self.roi_details_label.setText("")
        self.rules_tree.clear()

        for rule in rs.get_rules():
            # Assicura tipi corretti per la view
            color = str(rule.get("color", "#FFFFFF"))
            category = str(rule.get("category_name", "N/A"))
            suffix = str(rule.get("filename_suffix", category))

            item = QTreeWidgetItem([color, category, suffix])
            item.setBackground(0, QBrush(QColor(color)))

            # Contrasto testo
            h = color.lstrip("#")
            try:
                rgb = tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))
                brightness = (rgb[0] * 299 + rgb[1] * 587 + rgb[2] * 114) / 1000
                item.setForeground(0, QBrush(QColor("black" if brightness > 128 else "white")))
            except Exception:
                pass
            self.rules_tree.addTopLevelItem(item)

    def _update_rule_details_panel(self) -> None:
        """Aggiorna il pannello laterale con i dettagli della regola selezionata."""
        if not self.controller.rule_service:
            return
        items = self.rules_tree.selectedItems()
        if not items:
            self.keywords_text.clear()
            self.roi_details_label.setText("")
            return

        category_name = items[0].text(1)
        rule = self.controller.rule_service.get_rule_by_category(category_name)

        if rule:
            self.keywords_text.setPlainText(", ".join(rule.get("keywords", [])))
            self.roi_details_label.setText(f"{len(rule.get('rois', []))} aree ROI definite")

    def _on_tesseract_path_change(self) -> None:
        """Salva il nuovo percorso Tesseract se valido."""
        path = self.tesseract_path_entry.text()
        self.controller.config["tesseract_path"] = path
        self._auto_save_settings()

        from core.tesseract_manager import TesseractManager

        if path and not TesseractManager.is_valid(path):
            self._add_log_message("Percorso Tesseract indicato potrebbe non essere valido", "WARNING")

    def _browse_tesseract(self) -> None:
        """Apre il selettore file per l'eseguibile Tesseract."""
        path, _ = QFileDialog.getOpenFileName(self, "Seleziona Tesseract", "", "Executable (*.exe)")
        if path:
            self.tesseract_path_entry.setText(path)

    def _auto_detect_tesseract(self) -> None:
        """Utilizza TesseractManager per rilevare automaticamente l'eseguibile."""
        path = TesseractManager.auto_detect()
        if path:
            self.tesseract_path_entry.setText(path)
            QMessageBox.information(self, "Trovato", f"Tesseract trovato:\n{path}")
        else:
            QMessageBox.warning(self, "Non Trovato", "Tesseract non trovato automaticamente.\nIndicalo manualmente.")

    def _add_rule(self) -> None:
        """Apre l'editor per aggiungere una nuova regola."""
        self._show_rule_editor()

    def _modify_rule(self) -> None:
        """Apre l'editor per modificare la regola selezionata."""
        if not self.controller.rule_service:
            return
        items = self.rules_tree.selectedItems()
        if not items:
            QMessageBox.warning(self, "Selezione", "Selezionare una regola da modificare.")
            return

        category_name = items[0].text(1)
        rule = self.controller.rule_service.get_rule_by_category(category_name)
        if rule:
            self._show_rule_editor(rule)

    def _remove_rule(self) -> None:
        """Rimuove la regola selezionata."""
        items = self.rules_tree.selectedItems()
        if not items:
            QMessageBox.warning(self, "Selezione", "Selezionare una regola da rimuovere.")
            return

        cat = items[0].text(1)
        reply = QMessageBox.question(self, "Conferma", f"Rimuovere la regola '{cat}'?")

        rs = self.controller.rule_service
        if reply == QMessageBox.StandardButton.Yes and rs and rs.remove_rule(cat):
            self._populate_rules_tree()
            self._auto_save_settings()
            self.rules_count_label.setText(str(len(rs.get_rules())))

    def _show_rule_editor(self, rule: dict[str, Any] | None = None) -> None:
        """Apre l'editor delle regole delegando al controller se disponibile."""
        if not self.controller.rule_service:
            return
        dlg = RuleEditorDialog(self, self.controller.rule_service, rule)
        if dlg.exec():
            self.controller.rule_service.save()
            self._populate_rules_tree()
            self.rules_count_label.setText(str(len(self.controller.rule_service.get_rules())))

    def _launch_roi_utility(self) -> None:
        """Avvia o visualizza l'utility per la definizione delle ROI (Singleton)."""
        try:
            # Se la finestra non esiste o è stata chiusa (distrutta), creala
            if self._roi_window is None:
                self._roi_window = roi_utility.ROIDrawingApp()
                self._roi_window.showMaximized()
                self._add_log_message("Utility ROI avviata", "SUCCESS")
            else:
                # Se esiste, portala in primo piano
                if self._roi_window.isHidden():
                    self._roi_window.showMaximized()
                self._roi_window.raise_()
                self._roi_window.activateWindow()
                self._add_log_message("Utility ROI già attiva, portata in primo piano", "INFO")
        except Exception as e:
            logger.error(f"Errore durante l'avvio dell'utility ROI: {e}")
            QMessageBox.critical(self, "Errore", f"Impossibile avviare l'utility ROI:\n{e}")
