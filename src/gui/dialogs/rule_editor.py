"""
Dialogo per la creazione e modifica delle regole di classificazione (SRP).
"""

from typing import Any

from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QColorDialog,
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from core.rule_service import RuleService


class RuleEditorDialog(QDialog):
    """Dialogo specializzato per l'editing delle regole."""

    def __init__(self, parent: Any, rule_service: RuleService, rule: dict[str, Any] | None = None) -> None:
        """Inizializza l'editor per una regola nuova o esistente."""
        super().__init__(parent)
        self.rule_service = rule_service
        self.rule = rule
        self.chosen_color = rule.get("color", "#0D6EFD") if rule else "#0D6EFD"
        self._init_ui()

    def _init_ui(self) -> None:
        """Configura l'interfaccia utente del dialog di editing."""
        self.setWindowTitle("Modifica Regola" if self.rule else "Nuova Regola")
        self.setFixedSize(500, 400)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        grid = QGridLayout()

        # Categoria
        grid.addWidget(QLabel("Nome Categoria:"), 0, 0)
        self.cat_entry = QLineEdit(self.rule["category_name"] if self.rule else "")
        if self.rule:
            self.cat_entry.setReadOnly(True)
        grid.addWidget(self.cat_entry, 0, 1, 1, 2)

        # Suffisso
        grid.addWidget(QLabel("Suffisso File:"), 1, 0)
        self.suffix_entry = QLineEdit(self.rule.get("filename_suffix", "") if self.rule else "")
        grid.addWidget(self.suffix_entry, 1, 1, 1, 2)

        # Keywords
        grid.addWidget(QLabel("Keywords:"), 2, 0)
        self.kw_entry = QLineEdit(", ".join(self.rule.get("keywords", [])) if self.rule else "")
        grid.addWidget(self.kw_entry, 2, 1, 1, 2)
        grid.addWidget(QLabel("(separate da virgola)"), 3, 1)

        # Colore
        grid.addWidget(QLabel("Colore:"), 4, 0)
        self.color_swatch = QLabel("     ")
        self.color_swatch.setStyleSheet(f"background-color: {self.chosen_color}; border: 1px solid black;")
        self.color_swatch.setFixedSize(60, 25)
        grid.addWidget(self.color_swatch, 4, 1)

        btn_color = QPushButton("Scegli")
        btn_color.clicked.connect(self._choose_color)
        grid.addWidget(btn_color, 4, 2)

        # ROI Info
        grid.addWidget(QLabel("Aree ROI:"), 5, 0)
        roi_count = len(self.rule.get("rois", [])) if self.rule else 0
        grid.addWidget(QLabel(f"{roi_count} aree definite"), 5, 1)

        layout.addLayout(grid)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_save = QPushButton("Salva")
        btn_save.clicked.connect(self._on_save)
        btn_cancel = QPushButton("Annulla")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_save)
        btn_layout.addWidget(btn_cancel)

        layout.addLayout(btn_layout)

    def _choose_color(self) -> None:
        """Apre il selettore di colore e aggiorna l'anteprima."""
        c = QColorDialog.getColor(QColor(self.chosen_color), self, "Scegli Colore")
        if c.isValid():
            self.chosen_color = c.name()
            self.color_swatch.setStyleSheet(f"background-color: {self.chosen_color}; border: 1px solid black;")

    def _on_save(self) -> None:
        """Valida i dati inseriti e salva la regola nel RuleService."""
        category = self.cat_entry.text().strip()
        suffix = self.suffix_entry.text().strip() or category
        keywords = [k.strip() for k in self.kw_entry.text().split(",") if k.strip()]

        if not category or not keywords:
            QMessageBox.critical(self, "Errore", "Nome categoria e almeno una keyword sono obbligatori.")
            return

        new_data = {
            "category_name": category,
            "filename_suffix": suffix,
            "keywords": keywords,
            "color": self.chosen_color,
            "rois": self.rule.get("rois", []) if self.rule else [],
        }

        success = False
        if self.rule:
            success = self.rule_service.update_rule(self.rule["category_name"], new_data)
        else:
            success = self.rule_service.add_rule(new_data)

        if success:
            self.accept()
        else:
            QMessageBox.critical(self, "Errore", "Impossibile salvare la regola (nome duplicato?).")
