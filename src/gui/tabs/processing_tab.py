"""
Modulo per la Tab Elaborazione (SRP).
"""
from typing import Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox, 
    QLineEdit, QPushButton, QTextEdit, QProgressBar
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from gui.theme import COLORS, FONTS
from gui.widgets.drop_frame import DropFrame

class ProcessingTab(QWidget):
    """Gestisce la costruzione e i widget della tab Elaborazione."""

    def __init__(self, parent: QWidget, main_app: Any) -> None:
        """Inizializza la tab di elaborazione collegandola all'applicazione principale."""
        super().__init__(parent)
        self.main_app = main_app
        self._init_ui()

    def _init_ui(self) -> None:
        """Configura l'interfaccia utente, la log area e i widget di controllo elaborazione."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        header = QHBoxLayout()
        h_lbl = QLabel("Elaborazione PDF")
        h_lbl.setFont(FONTS["heading"])
        h_lbl.setStyleSheet(f"color: {COLORS['accent']};")
        header.addWidget(h_lbl)
        
        self.main_app.spinner_label = QLabel("")
        self.main_app.spinner_label.setFont(QFont("Consolas", 14, QFont.Weight.Bold))
        self.main_app.spinner_label.setStyleSheet(f"color: {COLORS['accent']};")
        header.addWidget(self.main_app.spinner_label)
        header.addStretch()
        layout.addLayout(header)

        # Input
        input_group = QGroupBox(" Input ")
        ilayout = QVBoxLayout(input_group)
        
        odc_row = QHBoxLayout()
        odc_row.addWidget(QLabel("Codice ODC (default):"))
        self.main_app.odc_entry = QLineEdit("5400")
        self.main_app.odc_entry.setFixedWidth(200)
        odc_row.addWidget(self.main_app.odc_entry)
        odc_row.addStretch()
        ilayout.addLayout(odc_row)

        file_row = QHBoxLayout()
        self.main_app.select_pdf_btn = QPushButton("Seleziona PDF...")
        self.main_app.select_pdf_btn.clicked.connect(self.main_app._select_pdf)
        file_row.addWidget(self.main_app.select_pdf_btn)
        
        self.main_app.select_folder_btn = QPushButton("Seleziona Cartella...")
        self.main_app.select_folder_btn.clicked.connect(self.main_app._select_folder)
        file_row.addWidget(self.main_app.select_folder_btn)
        
        self.main_app.pdf_path_label = QLabel("Nessun file selezionato")
        self.main_app.pdf_path_label.setFont(FONTS["body"])
        self.main_app.pdf_path_label.setStyleSheet(f"color: {COLORS['text_muted']};")
        file_row.addWidget(self.main_app.pdf_path_label)
        file_row.addStretch()
        ilayout.addLayout(file_row)

        self.main_app.drop_frame = DropFrame(self.main_app._on_drop)
        ilayout.addWidget(self.main_app.drop_frame)
        layout.addWidget(input_group, 2)

        # Progress
        prog_group = QGroupBox(" Progresso ")
        playout = QVBoxLayout(prog_group)
        
        info_row = QHBoxLayout()
        self.main_app.progress_label = QLabel("Pronto")
        self.main_app.progress_label.setFont(FONTS["body_bold"])
        self.main_app.progress_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        info_row.addWidget(self.main_app.progress_label)
        
        self.main_app.eta_label = QLabel("--:--")
        self.main_app.eta_label.setFont(FONTS["mono_bold"])
        self.main_app.eta_label.setStyleSheet(f"color: {COLORS['text_muted']};")
        info_row.addWidget(self.main_app.eta_label, 0, Qt.AlignmentFlag.AlignRight)
        playout.addLayout(info_row)
        
        self.main_app.progress_bar = QProgressBar()
        self.main_app.progress_bar.setMaximum(1000)
        self.main_app.progress_bar.setValue(0)
        playout.addWidget(self.main_app.progress_bar)

        # Control Buttons (Stop)
        ctrl_layout = QHBoxLayout()
        ctrl_layout.addStretch()
        self.main_app.stop_btn = QPushButton("STOP ELABORAZIONE")
        self.main_app.stop_btn.setFont(FONTS["body_bold"])
        self.main_app.stop_btn.setStyleSheet(f"background-color: {COLORS['danger']}; color: white; padding: 8px 20px;")
        self.main_app.stop_btn.setVisible(False)
        self.main_app.stop_btn.clicked.connect(self.main_app._stop_processing)
        ctrl_layout.addWidget(self.main_app.stop_btn)
        playout.addLayout(ctrl_layout)

        layout.addWidget(prog_group)

        # Log
        log_group = QGroupBox(" Log Elaborazione ")
        llayout = QVBoxLayout(log_group)
        self.main_app.log_area = QTextEdit()
        self.main_app.log_area.setFont(FONTS["mono"])
        llayout.addWidget(self.main_app.log_area)
        layout.addWidget(log_group, 3)
