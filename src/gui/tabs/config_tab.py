"""
Modulo per la Tab Configurazione (SRP).
"""
from typing import Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox, 
    QLineEdit, QPushButton, QTreeWidget, QTextEdit, QFrame
)
from gui.theme import COLORS, FONTS

class ConfigTab(QWidget):
    """Gestisce la costruzione e i widget della tab Configurazione."""

    def __init__(self, parent: QWidget, main_app: Any) -> None:
        """Inizializza la tab di configurazione collegandola all'applicazione principale."""
        super().__init__(parent)
        self.main_app = main_app
        self._init_ui()

    def _init_ui(self) -> None:
        """Configura l'interfaccia utente, i gruppi e i widget della tab configurazione."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        h = QLabel("Configurazione")
        h.setFont(FONTS["heading"])
        h.setStyleSheet(f"color: {COLORS['accent']};")
        layout.addWidget(h)

        # Tesseract
        tess_group = QGroupBox(" Tesseract OCR ")
        tess_layout = QHBoxLayout(tess_group)
        tess_layout.addWidget(QLabel("Percorso:"))
        
        self.main_app.tesseract_path_entry = QLineEdit()
        self.main_app.tesseract_path_entry.textChanged.connect(self.main_app._on_tesseract_path_change)
        tess_layout.addWidget(self.main_app.tesseract_path_entry, 1)
        
        btn_browse = QPushButton("Sfoglia")
        btn_browse.clicked.connect(self.main_app._browse_tesseract)
        tess_layout.addWidget(btn_browse)
        
        btn_detect = QPushButton("Auto-Rileva")
        btn_detect.clicked.connect(self.main_app._auto_detect_tesseract)
        tess_layout.addWidget(btn_detect)
        layout.addWidget(tess_group)

        # Rules
        rules_group = QGroupBox(" Regole di Classificazione ")
        rlayout = QHBoxLayout(rules_group)

        # Tree
        self.main_app.rules_tree = QTreeWidget()
        self.main_app.rules_tree.setHeaderLabels(["Colore", "Categoria", "Suffisso"])
        self.main_app.rules_tree.setColumnWidth(0, 80)
        self.main_app.rules_tree.setColumnWidth(1, 150)
        self.main_app.rules_tree.setAlternatingRowColors(True)
        self.main_app.rules_tree.itemSelectionChanged.connect(self.main_app._update_rule_details_panel)
        rlayout.addWidget(self.main_app.rules_tree, 2)

        # Details
        det_widget = QWidget()
        det_layout = QVBoxLayout(det_widget)
        det_layout.addWidget(QLabel("Keywords:"))
        self.main_app.keywords_text = QTextEdit()
        self.main_app.keywords_text.setReadOnly(True)
        self.main_app.keywords_text.setFixedHeight(100)
        det_layout.addWidget(self.main_app.keywords_text)
        
        det_layout.addWidget(QLabel("Aree ROI:"))
        self.main_app.roi_details_label = QLabel("")
        self.main_app.roi_details_label.setStyleSheet(f"color: {COLORS['text_muted']};")
        det_layout.addWidget(self.main_app.roi_details_label)
        det_layout.addStretch()
        rlayout.addWidget(det_widget, 2)

        # Buttons
        btns = QVBoxLayout()
        btn_add = QPushButton("Aggiungi")
        btn_add.clicked.connect(self.main_app._add_rule)
        btns.addWidget(btn_add)
        
        btn_mod = QPushButton("Modifica")
        btn_mod.clicked.connect(self.main_app._modify_rule)
        btns.addWidget(btn_mod)
        
        btn_rem = QPushButton("Rimuovi")
        btn_rem.clicked.connect(self.main_app._remove_rule)
        btns.addWidget(btn_rem)
        
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        btns.addWidget(sep)
        
        btn_roi = QPushButton("Utility ROI")
        btn_roi.clicked.connect(self.main_app._launch_roi_utility)
        btns.addWidget(btn_roi)
        
        btns.addStretch()
        rlayout.addLayout(btns)
        layout.addWidget(rules_group, 5)
