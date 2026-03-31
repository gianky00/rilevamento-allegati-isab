"""
Intelleo PDF Splitter - Applicazione Principale (View)
Gestisce l'interfaccia grafica e coordina l'interazione tra utente e controller.
"""

import logging
import queue
import sys
from contextlib import suppress
from datetime import datetime
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtGui import QCloseEvent, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
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

import app_updater
import roi_utility
import version
from core.app_controller import AppController
from core.notification_manager import NotificationManager
from gui.animations import UIAnimations
from gui.dialogs.rule_editor import RuleEditorDialog
from gui.dialogs.unknown_review import UnknownFilesReviewDialog
from gui.tabs.config_tab import ConfigTab
from gui.tabs.dashboard_tab import DashboardTab
from gui.tabs.help_tab import HelpTab
from gui.theme import COLORS, GLOBAL_QSS

logger = logging.getLogger("MAIN")


class MainApp(QMainWindow):
    """Finestra principale dell'applicazione Intelleo PDF Splitter."""

    def __init__(self, auto_file_path: str | None = None) -> None:
        super().__init__()
        self.setWindowTitle(f"Intelleo PDF Splitter v{version.__version__}")
        self.setMinimumSize(1100, 800)
        self.setStyleSheet(GLOBAL_QSS)

        # Stato interno
        self.log_queue: queue.Queue = queue.Queue()
        self._target_progress: float = 0.0
        self._is_processing: bool = False
        self._roi_window: Any = None

        # Controller e Notifiche
        self.controller = AppController()
        self.notifier = NotificationManager(self)
        self._connect_controller_signals()

        # —————— UI SHARED ELEMENTS (Requisiti dai Tab) ——————
        self.rules_count_label = QLabel("0")
        self.spinner_label = QLabel("")
        self.odc_entry = QLineEdit("")
        self.pdf_path_label = QLabel("Nessun file")
        self.progress_label = QLabel("Pronto")
        self.eta_label = QLabel("")
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(1000)
        self.stop_btn = QPushButton("STOP")
        self.restore_btn = QPushButton("RECUPERA")
        self.tesseract_path_entry = QLineEdit()
        self.rules_tree = QTreeWidget()
        self.keywords_text = QTextEdit()
        self.roi_details_label = QLabel("")
        
        # Footer Licenza
        self.license_status_label = QLabel("VERIFICA...")
        self.license_fields: dict[str, QLabel] = {}

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        main_layout = QVBoxLayout(self.central_widget)

        self.notebook = QTabWidget()
        self.notebook.currentChanged.connect(self._on_tab_changed)
        main_layout.addWidget(self.notebook)
        
        # Alias per i test
        self.tabs = self.notebook

        # —————— Tab Initialization ——————
        if not getattr(sys, "_testing", False):
            self.dashboard_tab = DashboardTab(self.notebook, self)
            self.config_tab = ConfigTab(self.notebook, self)
            self.help_tab = HelpTab(self.notebook, self)
            self.notebook.addTab(self.dashboard_tab, "Dashboard")
            self.notebook.addTab(self.config_tab, "Configurazione")
            self.notebook.addTab(self.help_tab, "Guida")
        
        # Startup logic
        self.controller.load_settings()
        self.controller.check_license()
        self._refresh_ui_from_config()
        
        if auto_file_path:
            self.controller.set_pdf_files([auto_file_path])

        # Heartbeat per controllo licenza (ogni 4 ore)
        self._license_timer = QTimer(self)
        self._license_timer.timeout.connect(lambda: self.controller.check_license_online(silent=True))
        self._license_timer.start(4 * 60 * 60 * 1000)

    # —————— EVENTI GUI ——————

    def _refresh_ui_from_config(self) -> None:
        """Sincronizza la UI con la configurazione caricata."""
        self.tesseract_path_entry.setText(self.controller.config.get("tesseract_path", ""))
        self._refresh_rules_tree()

    @Slot(int)
    def _on_tab_changed(self, index: int) -> None:
        if not hasattr(self, "_prev_tab_index"): self._prev_tab_index = 0
        new_widget = self.notebook.widget(index)
        old_widget = self.notebook.widget(self._prev_tab_index)
        if new_widget and old_widget and index != self._prev_tab_index:
            UIAnimations.slide_fade_transition(old_widget, new_widget, "right" if index > self._prev_tab_index else "left")
        self._prev_tab_index = index

    def _on_drop(self, files: list[str]) -> None:
        self.controller.set_pdf_files(files)

    def _select_pdf(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(self, "Seleziona PDF", "", "PDF Files (*.pdf)")
        if files:
            self.controller.set_pdf_files(files)

    def _quick_select_pdf(self) -> None:
        odc = self.odc_entry.text().strip()
        if not odc:
            QMessageBox.warning(self, "Attenzione", "Inserisci un codice ODC prima di iniziare.")
            self.odc_entry.setFocus()
            return
        if not self.controller.pdf_files:
            self._select_pdf()
        if self.controller.pdf_files:
            self.controller.start_processing(odc)

    def _launch_roi_utility(self) -> None:
        try:
            from roi_utility import ROIDrawingApp
            self._roi_window = ROIDrawingApp()
            self._roi_window.show()
        except Exception as e:
            logger.exception(f"Errore lancio ROI Utility: {e}")

    def _restore_session(self) -> None:
        session_data = self.controller.restore_session()
        if session_data:
            tasks, odc = session_data
            self.odc_entry.setText(odc)
            self.on_unknown_files_found(tasks, odc)

    def _stop_processing(self) -> None:
        self.controller.stop_processing()

    # —————— CONFIGURAZIONE REGOLE ——————

    def _add_rule(self) -> None:
        dialog = RuleEditorDialog(self)
        if dialog.exec():
            new_rule = dialog.get_rule_data()
            if self.controller.rule_service.add_rule(new_rule):
                self.controller.save_settings()
                self._refresh_rules_tree()

    def _modify_rule(self) -> None:
        selected = self.rules_tree.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Attenzione", "Seleziona una regola da modificare.")
            return
        
        category = selected[0].text(1)
        rule = self.controller.rule_service.get_rule_by_category(category)
        if rule:
            dialog = RuleEditorDialog(self, rule)
            if dialog.exec():
                updated_rule = dialog.get_rule_data()
                if self.controller.rule_service.update_rule(category, updated_rule):
                    self.controller.save_settings()
                    self._refresh_rules_tree()

    def _remove_rule(self) -> None:
        selected = self.rules_tree.selectedItems()
        if not selected: return
        
        category = selected[0].text(1)
        reply = QMessageBox.question(self, "Conferma", f"Eliminare la regola '{category}'?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            if self.controller.rule_service.remove_rule(category):
                self.controller.save_settings()
                self._refresh_rules_tree()

    # —————— TESSERACT ——————

    def _on_tesseract_path_change(self, path: str) -> None:
        self.controller.config["tesseract_path"] = path
        self.controller.save_settings()

    def _browse_tesseract(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Seleziona Tesseract.exe", "", "Executable (*.exe)")
        if path:
            self.tesseract_path_entry.setText(path)

    def _auto_detect_tesseract(self) -> None:
        from core.tesseract_manager import TesseractManager
        path = TesseractManager.auto_detect()
        if path:
            self.tesseract_path_entry.setText(path)
            QMessageBox.information(self, "Trovato", f"Tesseract rilevato in:\n{path}")
        else:
            QMessageBox.warning(self, "Non trovato", "Impossibile rilevare Tesseract automaticamente.")

    def _update_rule_details_panel(self) -> None:
        selected = self.rules_tree.selectedItems()
        if not selected:
            self.keywords_text.clear()
            self.roi_details_label.setText("")
            return
        
        category = selected[0].text(1)
        rule = self.controller.rule_service.get_rule_by_category(category)
        if rule:
            self.keywords_text.setText(", ".join(rule.get("keywords", [])))
            roi_count = len(rule.get("rois", []))
            self.roi_details_label.setText(f"{roi_count} aree definite")

    # —————— SEGNALI CONTROLLER ——————

    def _connect_controller_signals(self) -> None:
        self.controller.log_received.connect(self.add_log_message)
        self.controller.progress_updated.connect(self._on_progress_update)
        self.controller.processing_state_changed.connect(self.on_processing_state_changed)
        self.controller.stats_updated.connect(self.on_stats_updated)
        self.controller.session_status_changed.connect(self._update_restore_button_state)
        self.controller.unknown_files_found.connect(self.on_unknown_files_found)
        self.controller.rules_updated.connect(self._refresh_rules_tree)
        self.controller.license_status_updated.connect(self.on_license_status_updated)

    def add_log_message(self, message: str, level: str = "INFO", replace_last: bool = False) -> None:
        if hasattr(self, "log_area"):
            # DashboardTab imposta self.main_app.log_area durante l'inizializzazione
            self.log_area.append(f"[{level}] {message}")

    def on_processing_state_changed(self, is_processing: bool) -> None:
        self._is_processing = is_processing
        self.dashboard_start_btn.setEnabled(not is_processing)
        if hasattr(self, "proc_group"):
            self.proc_group.setVisible(is_processing)
            self.stop_btn.setVisible(is_processing)

    def on_stats_updated(self, s_docs: int, s_pages: int, g_docs: int, g_pages: int) -> None:
        if hasattr(self, "files_count_sess_label"):
            self.files_count_sess_label.setText(str(s_docs))
        if hasattr(self, "files_count_tot_label"):
            self.files_count_tot_label.setText(str(g_docs))
        if hasattr(self, "pages_count_sess_label"):
            self.pages_count_sess_label.setText(str(s_pages))
        if hasattr(self, "pages_count_tot_label"):
            self.pages_count_tot_label.setText(str(g_pages))

    def on_license_status_updated(self, info: dict) -> None:
        """Aggiorna lo stato della licenza nel footer."""
        for key, value in info.items():
            if key in self.license_fields:
                self.license_fields[key].setText(str(value))
        
        if info.get("is_valid"):
            self.license_status_label.setText("SISTEMA ATTIVO")
            self.license_status_label.setStyleSheet(f"color: {COLORS['success']}; font-weight: bold;")
        else:
            self.license_status_label.setText("LICENZA NON VALIDA")
            self.license_status_label.setStyleSheet(f"color: {COLORS['danger']}; font-weight: bold;")

    def _update_restore_button_state(self, has_session: bool) -> None:
        self.restore_btn.setEnabled(has_session)

    def _refresh_rules_tree(self) -> None:
        self.rules_tree.clear()
        rules = self.controller.config.get("classification_rules", [])
        self.rules_count_label.setText(str(len(rules)))
        for r in rules:
            item = QTreeWidgetItem([r.get("color", "#CCC"), r.get("category_name", "N/A"), r.get("suffix", "")])
            self.rules_tree.addTopLevelItem(item)

    def on_unknown_files_found(self, files: list, odc: str) -> None:
        from gui.dialogs.unknown_review import UnknownFilesReviewDialog
        dialog = UnknownFilesReviewDialog(self, files, odc)
        dialog.finished_review.connect(self.controller.clear_session)
        dialog.exec()

    def _on_progress_update(self, value: float, text: str, eta: Any = None) -> None:
        self.progress_bar.setValue(int(value * 10))
        self.progress_label.setText(text)
        if eta: self.eta_label.setText(f"ETA: {eta}s")

    def closeEvent(self, event: QCloseEvent) -> None:
        app_updater.run_pending_installer()
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainApp()
    window.show()
    sys.exit(app.exec())
