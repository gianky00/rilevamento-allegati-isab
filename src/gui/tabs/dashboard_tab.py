"""
Modulo per la Tab Dashboard (SRP).
"""

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from gui.theme import COLORS, FONTS
from gui.ui_factory import UIFactory
from gui.widgets.drop_frame import DropFrame


class DashboardTab(QWidget):
    """Gestisce la costruzione e i widget della tab Dashboard unificata."""

    def __init__(self, parent: QWidget, main_app: Any) -> None:
        """Inizializza la tab dashboard collegandola all'applicazione principale."""
        super().__init__(parent)
        self.main_app = main_app
        self._init_ui()

    def _init_ui(self) -> None:
        """Configura l'interfaccia utente unificata (Dashboard + Elaborazione)."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(8)

        # 1. Header Row
        header = QHBoxLayout()
        header.setSpacing(10)

        self.main_app.spinner_label = QLabel("")
        self.main_app.spinner_label.setFont(QFont("Consolas", 14, QFont.Weight.Bold))
        self.main_app.spinner_label.setStyleSheet(f"color: {COLORS['accent']}; border: none;")
        header.addWidget(self.main_app.spinner_label)

        header.addStretch() # Spinge le notifiche e l'orologio a destra

        if self.main_app.notifier:
            self.main_app.notifier.setup_bell_icon(header)

        self.clock_label = QLabel("")
        self.clock_label.setFont(FONTS["mono_bold"])
        self.clock_label.setStyleSheet(f"color: {COLORS['text_secondary']}; border: none;")
        header.addWidget(self.clock_label)
        layout.addLayout(header)
        # 2. Stat Cards Row
        cards = QHBoxLayout()
        cards.setSpacing(10)
        # CARD 1: VOLUME (COMBINATA)
        (
            card_stats,
            self.main_app.files_count_sess_label,
            self.main_app.files_count_tot_label,
            self.main_app.pages_count_sess_label,
            self.main_app.pages_count_tot_label,
        ) = UIFactory.create_combined_stat_card("VOLUMI")

        # CARD 2: REGOLE
        card_regole, self.main_app.rules_count_label = UIFactory.create_stat_card("REGOLE", "0")

        # CARD 3: LICENZA
        card_licenza, self.main_app.license_status_label, lic_grid = UIFactory.create_license_card("LICENZA")

        self.main_app.license_fields = {}
        fields = [
            ("UTENTE", "cliente", "user.svg", 0, 0),
            ("SCADENZA", "scadenza", "calendar.svg", 0, 1),
            ("HWID", "hwid", "id.svg", 1, 0),
            ("ACCESSO", "last_access", "clock.svg", 1, 1),
        ]
        for label, key, icon, row_idx, col_idx in fields:
            row_widget, v_lab = UIFactory.create_compact_info_row(label, icon)
            self.main_app.license_fields[key] = v_lab
            lic_grid.addWidget(row_widget, row_idx, col_idx)

        cards.addWidget(card_stats, 3)
        cards.addWidget(card_regole, 2)
        cards.addWidget(card_licenza, 5) # Leggermente più largo per le 2 colonne
        layout.addLayout(cards)
        # 3. Comandi Rapidi e Configurazione
        quick_row = QHBoxLayout()
        quick_row.setSpacing(10)
        quick_row.addStretch(1) # Spaziatore a sinistra per centrare il contenuto

        # --- GRUPPO AZIONI (Larghezza Fissa) ---
        actions_group = QGroupBox(" AZIONI ")
        actions_group.setFixedWidth(500) # Ridotto da 620 a 500
        actions_group.setStyleSheet(
            f"QGroupBox {{ font-weight: bold; border: none; background-color: {COLORS['bg_secondary']}; border-radius: 8px; margin-top: 0px; }}",
        )
        act_layout = QHBoxLayout(actions_group)
        act_layout.setContentsMargins(12, 10, 12, 10)
        act_layout.setSpacing(8)

        # Pulsante Avvia (Primario)
        self.main_app.dashboard_start_btn = QPushButton("AVVIA ANALISI")
        self.main_app.dashboard_start_btn.setFont(FONTS["body_bold"])
        self.main_app.dashboard_start_btn.setStyleSheet(
            f"background-color: {COLORS['accent']}; color: white; padding: 5px 15px;",
        )
        self.main_app.dashboard_start_btn.clicked.connect(self.main_app._quick_select_pdf)
        act_layout.addWidget(self.main_app.dashboard_start_btn)

        # Altri comandi
        btn_rules = QPushButton("REGOLE")
        btn_rules.clicked.connect(lambda: self.main_app.notebook.setCurrentWidget(self.main_app.config_tab))
        act_layout.addWidget(btn_rules)

        btn_roi = QPushButton("UTILITY ROI")
        btn_roi.clicked.connect(self.main_app._launch_roi_utility)
        act_layout.addWidget(btn_roi)

        self.main_app.restore_btn = QPushButton("RECUPERA SESSIONE")
        self.main_app.restore_btn.setEnabled(False)
        self.main_app.restore_btn.clicked.connect(self.main_app._restore_session)
        act_layout.addWidget(self.main_app.restore_btn)

        quick_row.addWidget(actions_group)

        # --- GRUPPO CONFIGURAZIONE (Larghezza Fissa) ---
        config_group = QGroupBox(" CONFIGURAZIONE ")
        config_group.setFixedWidth(200) # Dimensione fissa e compatta
        config_group.setStyleSheet(
            f"QGroupBox {{ font-weight: bold; border: none; background-color: {COLORS['bg_secondary']}; border-radius: 8px; margin-top: 0px; }}",
        )
        conf_layout = QHBoxLayout(config_group)
        conf_layout.setContentsMargins(12, 10, 12, 10)
        conf_layout.setSpacing(8)

        conf_layout.addWidget(QLabel("ODC:"))
        self.main_app.odc_entry = QLineEdit("5400")
        self.main_app.odc_entry.setFixedWidth(120)
        self.main_app.odc_entry.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_app.odc_entry.setFont(FONTS["body_bold"])
        conf_layout.addWidget(self.main_app.odc_entry)

        quick_row.addWidget(config_group)
        quick_row.addStretch(1) # Spaziatore a destra per centrare il blocco azioni+config

        layout.addLayout(quick_row)

        # 4. Sezione Elaborazione (Compattata)
        proc_group = QGroupBox(" ELABORAZIONE IN CORSO ")
        proc_group.setStyleSheet(
            f"QGroupBox {{ font-weight: bold; border: none; background-color: {COLORS['bg_secondary']}; border-radius: 8px; }}",
        )
        playout = QVBoxLayout(proc_group)
        playout.setContentsMargins(12, 8, 12, 8)
        playout.setSpacing(4)

        info_row = QHBoxLayout()
        self.main_app.pdf_path_label = QLabel("Nessun file selezionato")
        self.main_app.pdf_path_label.setFont(FONTS["small"])
        self.main_app.pdf_path_label.setStyleSheet(f"color: {COLORS['text_muted']};")
        info_row.addWidget(self.main_app.pdf_path_label)

        self.main_app.progress_label = QLabel("Pronto")
        self.main_app.progress_label.setFont(FONTS["small_bold"])
        self.main_app.progress_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        info_row.addWidget(self.main_app.progress_label, 0, Qt.AlignmentFlag.AlignCenter)

        self.main_app.eta_label = QLabel("")
        self.main_app.eta_label.setFont(FONTS["mono_bold"])
        info_row.addWidget(self.main_app.eta_label, 0, Qt.AlignmentFlag.AlignRight)
        playout.addLayout(info_row)

        # Progress bar e Stop button sulla stessa riga per risparmiare spazio
        prog_row = QHBoxLayout()
        self.main_app.progress_bar = QProgressBar()
        self.main_app.progress_bar.setMaximum(1000)
        self.main_app.progress_bar.setFixedHeight(10)
        prog_row.addWidget(self.main_app.progress_bar, 1)

        self.main_app.stop_btn = QPushButton("ANNULLA")
        self.main_app.stop_btn.setFont(FONTS["small_bold"])
        self.main_app.stop_btn.setStyleSheet(f"background-color: {COLORS['danger']}; color: white; padding: 1px 8px;")
        self.main_app.stop_btn.setVisible(False)
        self.main_app.stop_btn.clicked.connect(self.main_app._stop_processing)
        prog_row.addWidget(self.main_app.stop_btn)
        playout.addLayout(prog_row)

        layout.addWidget(proc_group)

        # 5. Terminale / Log Unificato
        log_group = QGroupBox(" TERMINALE ATTIVITÀ ")
        log_group.setStyleSheet(
            f"QGroupBox {{ font-weight: bold; border: none; background-color: {COLORS['bg_secondary']}; border-radius: 8px; }}",
        )
        log_layout = QVBoxLayout(log_group)
        log_layout.setContentsMargins(10, 8, 10, 8)
        self.main_app.log_area = QTextEdit()  # Usiamo log_area come terminale principale
        self.main_app.log_area.setReadOnly(True)
        self.main_app.log_area.setFont(FONTS["mono"])
        self.main_app.log_area.setStyleSheet("border: none; background: transparent;")
        log_layout.addWidget(self.main_app.log_area)

        # Link recent_log a log_area per compatibilità
        self.main_app.recent_log = self.main_app.log_area

        layout.addWidget(log_group, 1)

        # Aggiungiamo un DropFrame invisibile che copre tutto il layout per facilitare il drag&drop
        self.main_app.drop_frame = DropFrame(self.main_app._on_drop)
        self.main_app.drop_frame.setFixedHeight(35)
        self.main_app.drop_frame.setText("Trascina qui i PDF per iniziare")
        layout.addWidget(self.main_app.drop_frame)
