"""
Modulo per la Tab Dashboard (SRP).
"""
from typing import Any, Dict, List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox, 
    QPushButton, QTextEdit, QFrame
)
from PySide6.QtCore import Qt
from gui.theme import COLORS, FONTS
from gui.ui_factory import UIFactory

class DashboardTab(QWidget):
    """Gestisce la costruzione e i widget della tab Dashboard."""

    def __init__(self, parent: QWidget, main_app: Any) -> None:
        """Inizializza la tab dashboard collegandola all'applicazione principale."""
        super().__init__(parent)
        self.main_app = main_app
        self._init_ui()

    def _init_ui(self) -> None:
        """Configura l'interfaccia utente, le card statistiche e il log rapido."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)

        # Header
        header = QHBoxLayout()
        h_label = QLabel("SISTEMA DI ELABORAZIONE INTELLIGENTE")
        h_label.setFont(FONTS["heading"])
        h_label.setStyleSheet(f"color: {COLORS['accent']};")
        header.addWidget(h_label)
        
        if self.main_app.notifier:
            self.main_app.notifier.setup_bell_icon(header)
            
        self.clock_label = QLabel("")
        self.clock_label.setFont(FONTS["mono_bold"])
        self.clock_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        header.addWidget(self.clock_label)
        layout.addLayout(header)

        # Stat cards
        cards = QHBoxLayout()
        card_analizzati, self.main_app.files_count_label = UIFactory.create_stat_card("DOC ANALIZZATI", "0 / 0")
        card_pagine, self.main_app.pages_count_label = UIFactory.create_stat_card("PAGINE TOTALI", "0 / 0")
        card_regole, self.main_app.rules_count_label = UIFactory.create_stat_card("REGOLE ATTIVE", "0")
        
        cards.addWidget(card_analizzati, 1)
        cards.addWidget(card_pagine, 1)
        cards.addWidget(card_regole, 1)
        layout.addLayout(cards)

        # Middle: License + Actions
        middle = QHBoxLayout()

        # License panel (Compact Version)
        lic_group = QGroupBox(" STATO LICENZA E INFORMAZIONI ")
        lic_group.setStyleSheet(f"QGroupBox {{ font-weight: bold; border: 1px solid {COLORS['border']}; border-radius: 6px; margin-top: 10px; }}")
        lic_layout = QVBoxLayout(lic_group)
        lic_layout.setContentsMargins(15, 15, 15, 10)
        lic_layout.setSpacing(4)
        
        # Stato Licenza Primario
        self.main_app.license_status_label = QLabel("Verificando...")
        from PySide6.QtGui import QFont
        self.main_app.license_status_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.main_app.license_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_app.license_status_label.setStyleSheet(f"color: {COLORS['text_muted']}; border: none; padding-bottom: 8px;")
        lic_layout.addWidget(self.main_app.license_status_label)
        
        sep_line = QFrame()
        sep_line.setFrameShape(QFrame.Shape.HLine)
        sep_line.setStyleSheet(f"border-top: 1px solid {COLORS['border']}; margin-bottom: 5px;")
        lic_layout.addWidget(sep_line)

        self.main_app.license_fields = {}
        fields = [
            ("UTENTE", "cliente", "user.svg"),
            ("SCADENZA", "scadenza", "calendar.svg"),
            ("HWID", "hwid", "id.svg"),
            ("ACCESSO", "last_access", "clock.svg"),
        ]
        for label, key, icon in fields:
            row, v_lab = UIFactory.create_compact_info_row(label, icon)
            self.main_app.license_fields[key] = v_lab
            lic_layout.addWidget(row)
        
        
        lic_layout.addStretch()
        middle.addWidget(lic_group, 2)

        # Actions
        actions_group = QGroupBox(" COMANDI RAPIDI ")
        act_layout = QVBoxLayout(actions_group)
        self.main_app.dashboard_start_btn = QPushButton("NUOVA ANALISI")
        self.main_app.dashboard_start_btn.setFont(FONTS["body_bold"])
        self.main_app.dashboard_start_btn.setStyleSheet(f"background-color: {COLORS['accent']}; color: white;")
        self.main_app.dashboard_start_btn.clicked.connect(self.main_app._quick_select_pdf)
        act_layout.addWidget(self.main_app.dashboard_start_btn)
        
        btn_rules = QPushButton("GESTISCI REGOLE")
        btn_rules.clicked.connect(lambda: self.main_app.notebook.setCurrentWidget(self.main_app.config_tab))
        act_layout.addWidget(btn_rules)
        
        btn_roi = QPushButton("UTILITY ROI")
        btn_roi.clicked.connect(self.main_app._launch_roi_utility)
        act_layout.addWidget(btn_roi)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        act_layout.addWidget(sep)

        self.main_app.restore_btn = QPushButton("RECUPERO SESSIONE")
        self.main_app.restore_btn.setEnabled(False)
        self.main_app.restore_btn.clicked.connect(self.main_app._restore_session)
        act_layout.addWidget(self.main_app.restore_btn)
        act_layout.addStretch()
        
        middle.addWidget(actions_group, 1)
        layout.addLayout(middle, 1)

        # Activity log
        log_group = QGroupBox(" TERMINALE ATTIVITÀ ")
        log_layout = QVBoxLayout(log_group)
        self.main_app.recent_log = QTextEdit()
        self.main_app.recent_log.setReadOnly(True)
        self.main_app.recent_log.setMinimumHeight(150)
        self.main_app.recent_log.setFont(FONTS["mono"])
        log_layout.addWidget(self.main_app.recent_log)
        layout.addWidget(log_group, 2)
