"""
Fabbrica per i componenti dell'interfaccia utente (SRP).
Riduce il boilerplate in MainApp gestendo la creazione di layout complessi.
"""

from PySide6.QtCore import Property, QPropertyAnimation, Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout

from core.path_manager import get_asset_path
from gui.theme import COLORS, FONTS
from gui.animations import UIAnimations


class AnimatedButton(QPushButton):
    """Pulsante con animazioni fluide per hover e pressione."""

    def __init__(self, text: str, parent=None, is_primary=False):
        super().__init__(text, parent)
        self.is_primary = is_primary
        self._bg_color = QColor(COLORS["accent"] if is_primary else COLORS["bg_secondary"])
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_style()

    def _update_style(self):
        color = self._bg_color.name()
        text_color = "white" if self.is_primary else COLORS["text_primary"]
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: {text_color};
                border: none;
                border-radius: 5px;
                padding: 8px 15px;
            }}
        """)

    def enterEvent(self, event):
        self.animate_color(COLORS["accent_hover"] if self.is_primary else COLORS["bg_tertiary"])
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.animate_color(COLORS["accent"] if self.is_primary else COLORS["bg_secondary"])
        super().leaveEvent(event)

    def animate_color(self, target_color_hex):
        self._anim = QPropertyAnimation(self, b"background_color")
        self._anim.setDuration(200)
        self._anim.setEndValue(QColor(target_color_hex))
        self._anim.start()

    def get_bg_color(self):
        return self._bg_color

    def set_bg_color(self, color):
        self._bg_color = color
        self._update_style()

    background_color = Property(QColor, get_bg_color, set_bg_color)


class UIFactory:
    """Collezione di metodi statici per la creazione di componenti UI standardizzati."""

    @staticmethod
    def create_svg_icon(filename: str, size: int = 20) -> QSvgWidget:
        """Crea un widget SVG caricando il file specificato."""
        path = get_asset_path(filename)
        svg = QSvgWidget(path)
        svg.setFixedSize(size, size)
        return svg

    @staticmethod
    def create_stat_card(title: str, initial_value: str) -> tuple[QFrame, QLabel]:
        """Crea una scheda statistica stilizzata con font uniforme."""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS["bg_secondary"]};
                border: none;
                border-radius: 6px;
                padding: 4px 8px;
            }}
        """)
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout = QVBoxLayout(card)
        layout.setSpacing(2)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        t_label = QLabel(title)
        t_label.setFont(FONTS["small_bold"])
        t_label.setStyleSheet(f"color: {COLORS['text_secondary']}; border: none;")
        t_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        v_label = QLabel(initial_value)
        v_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        v_label.setStyleSheet(f"color: {COLORS['accent']}; border: none;")
        v_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(t_label)
        layout.addWidget(v_label)

        return card, v_label

    @staticmethod
    def create_combined_stat_card(title: str) -> tuple[QFrame, QLabel, QLabel, QLabel, QLabel]:
        """Crea una scheda statistica che raggruppa Doc e Pagine fianco a fianco per massima compattezza."""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS["bg_secondary"]};
                border: none;
                border-radius: 8px;
                padding: 4px 8px;
            }}
        """)
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout = QVBoxLayout(card)
        layout.setSpacing(2)

        t_label = QLabel(title)
        t_label.setFont(FONTS["small_bold"])
        t_label.setStyleSheet(f"color: {COLORS['accent']}; border: none;")
        t_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(t_label)

        content = QHBoxLayout()
        content.setSpacing(10)

        def create_stat_sub_col(label_text: str):
            col = QVBoxLayout()
            col.setSpacing(0)

            lbl = QLabel(label_text)
            lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
            lbl.setStyleSheet("color: #6B7280; border: none;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            col.addWidget(lbl)

            vals = QHBoxLayout()
            vals.setSpacing(2)
            s_val = QLabel("0")
            s_val.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
            s_val.setStyleSheet(f"color: {COLORS['accent']}; border: none;")

            sep = QLabel("/")
            sep.setStyleSheet("color: #D1D5DB; border: none;")

            t_val = QLabel("0")
            t_val.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
            t_val.setStyleSheet(f"color: {COLORS['text_primary']}; border: none;")

            vals.addStretch()
            vals.addWidget(s_val)
            vals.addWidget(sep)
            vals.addWidget(t_val)
            vals.addStretch()
            col.addLayout(vals)
            return col, s_val, t_val

        # Doc a sinistra
        col_doc, ds, dt = create_stat_sub_col("DOCUMENTI (SESSIONE / TOTALE)")
        content.addLayout(col_doc)

        # Divisore verticale
        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        line.setStyleSheet(f"background-color: {COLORS['border']}; max-width: 1px;")
        content.addWidget(line)

        # Pagine a destra
        col_pag, ps, pt = create_stat_sub_col("PAGINE (SESSIONE / TOTALE)")
        content.addLayout(col_pag)

        layout.addLayout(content)
        return card, ds, dt, ps, pt

    @staticmethod
    def create_license_card(title: str) -> tuple[QFrame, QLabel, QGridLayout]:
        """Crea una scheda dedicata alla licenza con layout a due colonne."""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS["bg_secondary"]};
                border: none;
                border-radius: 8px;
                padding: 4px 8px;
            }}
        """)
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout = QVBoxLayout(card)
        layout.setSpacing(2)

        t_label = QLabel(title)
        t_label.setFont(FONTS["small_bold"])
        t_label.setStyleSheet(f"color: {COLORS['text_secondary']}; border: none;")
        t_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(t_label)

        status_label = QLabel("VERIFICA...")
        status_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_label.setStyleSheet(f"color: {COLORS['text_muted']}; border: none;")
        layout.addWidget(status_label)

        grid = QGridLayout()
        grid.setSpacing(4)
        grid.setContentsMargins(0, 2, 0, 0)
        layout.addLayout(grid)

        return card, status_label, grid

    @staticmethod
    def create_license_field(label: str, icon: str) -> tuple[QFrame, QLabel]:
        """Crea un campo informativo per il pannello licenza."""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS["bg_secondary"]};
                border: 1px solid {COLORS["border"]};
                border-radius: 4px;
                padding: 8px;
            }}
        """)
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout = QVBoxLayout(card)

        header = QHBoxLayout()
        icon_lbl = QLabel(icon)
        icon_lbl.setFont(QFont("Segoe UI Emoji", 11))
        header.addWidget(icon_lbl)

        text_lbl = QLabel(label)
        text_lbl.setFont(FONTS["small"])
        text_lbl.setStyleSheet(f"color: {COLORS['text_secondary']}; border: none;")
        header.addWidget(text_lbl)
        header.addStretch()

        v_label = QLabel("ATTESA DATI...")
        v_label.setFont(FONTS["mono_bold"])
        v_label.setStyleSheet(f"color: {COLORS['accent']}; border: none;")

        layout.addLayout(header)
        layout.addWidget(v_label)

        return card, v_label

    @staticmethod
    def create_compact_info_row(label: str, icon_file: str) -> tuple[QFrame, QLabel]:
        """Crea una riga informativa compatta con icona SVG."""
        row = QFrame()
        row.setStyleSheet(f"background-color: {COLORS['bg_secondary']}; border: none; border-radius: 4px; padding: 0px;")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(6)

        svg_icon = UIFactory.create_svg_icon(icon_file, 16)
        layout.addWidget(svg_icon)

        text_lbl = QLabel(label + ":")
        text_lbl.setFont(FONTS["body_bold"])
        text_lbl.setStyleSheet(f"color: {COLORS['text_secondary']};")
        layout.addWidget(text_lbl)

        v_label = QLabel("...")
        v_label.setFont(FONTS["mono_bold"])
        v_label.setStyleSheet(f"color: {COLORS['accent']};")
        layout.addWidget(v_label)
        layout.addStretch()

        return row, v_label
