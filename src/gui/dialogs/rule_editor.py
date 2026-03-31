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
    QVBoxLayout,
)

from core.rule_service import RuleService
from gui.theme import COLORS, FONTS
from gui.ui_factory import AnimatedButton


class RuleEditorDialog(QDialog):
    """Dialogo specializzato per l'editing delle regole."""

    def __init__(self, parent: Any, rule_service: RuleService, rule: dict[str, Any] | None = None) -> None:
        """Inizializza l'editor per una regola nuova o esistente."""
        super().__init__(parent)
        self.rule_service = rule_service
        self.rule = rule
        self.chosen_color = rule.get("color", "#0D6EFD") if rule else "#0D6EFD"
        self._final_data: dict[str, Any] | None = None
        self._init_ui()

    def _init_ui(self) -> None:
        """Configura l'interfaccia utente del dialog di editing."""
        self.setWindowTitle("Modifica Regola" if self.rule else "Nuova Regola")
        self.setFixedSize(500, 420)
        self.setModal(True)
        self.setStyleSheet(f"background-color: {COLORS['bg_primary']}; color: {COLORS['text_primary']};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 25, 20, 20)

        grid = QGridLayout()
        grid.setSpacing(10)

        # Categoria
        lbl_cat = QLabel("Nome Categoria:")
        lbl_cat.setStyleSheet(f"color: {COLORS['text_primary']}; font-weight: bold;")
        grid.addWidget(lbl_cat, 0, 0)

        self.cat_entry = QLineEdit(self.rule["category_name"] if self.rule else "")
        self.cat_entry.setStyleSheet(
            f"background-color: {COLORS['bg_primary']}; color: {COLORS['text_primary']}; border: 1px solid {COLORS['border']}; padding: 5px;"
        )
        if self.rule:
            self.cat_entry.setReadOnly(True)
            self.cat_entry.setStyleSheet(
                f"background-color: {COLORS['bg_tertiary']}; color: {COLORS['text_muted']}; border: 1px solid {COLORS['border']}; padding: 5px;"
            )
        grid.addWidget(self.cat_entry, 0, 1, 1, 2)

        # Suffisso
        lbl_suf = QLabel("Suffisso File:")
        lbl_suf.setStyleSheet(f"color: {COLORS['text_primary']}; font-weight: bold;")
        grid.addWidget(lbl_suf, 1, 0)

        self.suffix_entry = QLineEdit(self.rule.get("filename_suffix", "") if self.rule else "")
        self.suffix_entry.setStyleSheet(
            f"background-color: {COLORS['bg_primary']}; color: {COLORS['text_primary']}; border: 1px solid {COLORS['border']}; padding: 5px;"
        )
        grid.addWidget(self.suffix_entry, 1, 1, 1, 2)

        # Keywords
        lbl_kw = QLabel("Keywords:")
        lbl_kw.setStyleSheet(f"color: {COLORS['text_primary']}; font-weight: bold;")
        grid.addWidget(lbl_kw, 2, 0)

        self.kw_entry = QLineEdit(", ".join(self.rule.get("keywords", [])) if self.rule else "")
        self.kw_entry.setStyleSheet(
            f"background-color: {COLORS['bg_primary']}; color: {COLORS['text_primary']}; border: 1px solid {COLORS['border']}; padding: 5px;"
        )
        grid.addWidget(self.kw_entry, 2, 1, 1, 2)

        lbl_hint = QLabel("(separate da virgola)")
        lbl_hint.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 10px;")
        grid.addWidget(lbl_hint, 3, 1)

        # Colore
        lbl_col = QLabel("Colore:")
        lbl_col.setStyleSheet(f"color: {COLORS['text_primary']}; font-weight: bold;")
        grid.addWidget(lbl_col, 4, 0)

        self.color_swatch = QLabel("     ")
        self.color_swatch.setStyleSheet(
            f"background-color: {self.chosen_color}; border: 2px solid {COLORS['text_primary']}; border-radius: 4px;"
        )
        self.color_swatch.setFixedSize(60, 25)
        grid.addWidget(self.color_swatch, 4, 1)

        btn_color = AnimatedButton("Scegli")
        btn_color.clicked.connect(self._choose_color)
        grid.addWidget(btn_color, 4, 2)

        # ROI Info
        lbl_roi = QLabel("Aree ROI:")
        lbl_roi.setStyleSheet(f"color: {COLORS['text_primary']}; font-weight: bold;")
        grid.addWidget(lbl_roi, 5, 0)

        roi_count = len(self.rule.get("rois", [])) if self.rule else 0
        lbl_roi_count = QLabel(f"{roi_count} aree definite")
        lbl_roi_count.setStyleSheet(f"color: {COLORS['accent']};")
        grid.addWidget(lbl_roi_count, 5, 1)

        layout.addLayout(grid)
        layout.addStretch()

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        btn_save = AnimatedButton("Salva", is_primary=True)
        btn_save.setFont(FONTS["body_bold"])
        btn_save.clicked.connect(self._on_save)

        btn_cancel = AnimatedButton("Annulla")
        btn_cancel.clicked.connect(self.reject)

        btn_layout.addWidget(btn_save)
        btn_layout.addWidget(btn_cancel)

        layout.addLayout(btn_layout)

    def _choose_color(self) -> None:
        """Apre il selettore di colore e aggiorna l'anteprima."""
        c = QColorDialog.getColor(QColor(self.chosen_color), self, "Scegli Colore")
        if c.isValid():
            self.chosen_color = c.name()
            self.color_swatch.setStyleSheet(
                f"background-color: {self.chosen_color}; border: 2px solid {COLORS['text_primary']}; border-radius: 4px;"
            )

    def _on_save(self) -> None:
        """Valida i dati inseriti e prepara il salvataggio."""
        category = self.cat_entry.text().strip()
        suffix = self.suffix_entry.text().strip() or category
        keywords = [k.strip() for k in self.kw_entry.text().split(",") if k.strip()]

        if not category or not keywords:
            QMessageBox.critical(self, "Errore", "Nome categoria e almeno una keyword sono obbligatori.")
            return

        self._final_data = {
            "category_name": category,
            "filename_suffix": suffix,
            "keywords": keywords,
            "color": self.chosen_color,
            "rois": self.rule.get("rois", []) if self.rule else [],
        }
        self.accept()

    def get_rule_data(self) -> dict[str, Any]:
        """Restituisce i dati della regola configurata."""
        return self._final_data or {}
