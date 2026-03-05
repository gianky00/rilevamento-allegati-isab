"""
Dialogo per la selezione della categoria e il salvataggio della ROI (SRP).
"""
from typing import List, Any
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

class RoiSelectorDialog(QDialog):
    """Dialog per associare una ROI a una categoria."""

    def __init__(self, parent: Any, categories: List[str], roi_coords: List[int], colors: dict) -> None:
        """Inizializza il dialog per l'associazione di una ROI a una categoria specifica."""
        super().__init__(parent)
        self.categories = categories
        self.roi_coords = roi_coords
        self.colors = colors
        self._init_ui()

    def _init_ui(self) -> None:
        """Configura l'interfaccia utente del dialog di selezione categoria."""
        self.setWindowTitle("Salva Nuova ROI")
        self.setFixedSize(550, 250)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        title = QLabel("Associa ROI alla categoria:")
        title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        self.category_combo = QComboBox()
        self.category_combo.setFont(QFont("Segoe UI", 10))
        self.category_combo.addItems(self.categories)
        layout.addWidget(self.category_combo)

        coords_text = f"Coordinate PDF: ({self.roi_coords[0]}, {self.roi_coords[1]}) -> ({self.roi_coords[2]}, {self.roi_coords[3]})"
        coords_label = QLabel(coords_text)
        coords_label.setFont(QFont("Segoe UI", 9))
        coords_label.setStyleSheet(f"color: {self.colors['text_secondary']};")
        coords_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(coords_label)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_save = QPushButton("Salva ROI")
        self.btn_save.setFont(QFont("Segoe UI", 10))
        self.btn_save.clicked.connect(self.accept)
        btn_layout.addWidget(self.btn_save)

        btn_cancel = QPushButton("Annulla")
        btn_cancel.setFont(QFont("Segoe UI", 10))
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def get_selected_category(self) -> str:
        """Restituisce il nome della categoria selezionata nel menu a tendina."""
        return self.category_combo.currentText()
