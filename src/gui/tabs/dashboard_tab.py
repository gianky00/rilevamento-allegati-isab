"""
Modulo per la Tab Dashboard (SRP).
"""
from typing import Any, Dict, List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox, QGridLayout, 
    QPushButton, QTextEdit, QFrame
)
from PySide6.QtCore import Qt
from gui.theme import COLORS, FONTS
from gui.ui_factory import UIFactory

class DashboardTab(QWidget):
    """Gestisce la costruzione e i widget della tab Dashboard."""

    def __init__(self, parent: QWidget, main_app: Any) -> None:
        super().__init__(parent)
        self.main_app = main_app
        self._init_ui()

    def _init_ui(self) -> None:
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
        card_lic, self.main_app.license_status_label = UIFactory.create_stat_card("STATO LICENZA", "Verificando...")
        card_analizzati, self.main_app.files_count_label = UIFactory.create_stat_card("DOC ANALIZZATI", "0")
        card_pagine, self.main_app.pages_count_label = UIFactory.create_stat_card("PAGINE TOTALI", "0")
        card_regole, self.main_app.rules_count_label = UIFactory.create_stat_card("REGOLE ATTIVE", "0")
        
        cards.addWidget(card_lic, 1)
        cards.addWidget(card_analizzati, 1)
        cards.addWidget(card_pagine, 1)
        cards.addWidget(card_regole, 1)
        layout.addLayout(cards)

        # Middle: License + Actions
        middle = QHBoxLayout()

        # License panel
        license_group = QGroupBox(" PARAMETRI DI AUTENTICAZIONE E SICUREZZA ")
        lic_layout = QGridLayout(license_group)
        self.main_app.license_fields = {}
        fields = [
            ("UTENTE REGISTRATO", "cliente", "👤"),
            ("TERMINE VALIDITÀ", "scadenza", "📅"),
            ("HARDWARE IDENTIFIER", "hwid", "🆔"),
            ("ULTIMO ACCESSO RILEVATO", "last_access", "🕒"),
        ]
        for i, (label, key, icon) in enumerate(fields):
            row, col = divmod(i, 2)
            card, v_lab = UIFactory.create_license_field(label, icon)
            self.main_app.license_fields[key] = v_lab
            lic_layout.addWidget(card, row, col)
        middle.addWidget(license_group, 3)

        # Actions
        actions_group = QGroupBox(" COMANDI RAPIDI ")
        act_layout = QVBoxLayout(actions_group)
        btn_new = QPushButton("NUOVA ANALISI")
        btn_new.setFont(FONTS["body_bold"])
        btn_new.setStyleSheet(f"background-color: {COLORS['accent']}; color: white;")
        btn_new.clicked.connect(self.main_app._quick_select_pdf)
        act_layout.addWidget(btn_new)
        
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
