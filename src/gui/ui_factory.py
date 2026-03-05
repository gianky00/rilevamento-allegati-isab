"""
Fabbrica per i componenti dell'interfaccia utente (SRP).
Riduce il boilerplate in MainApp gestendo la creazione di layout complessi.
"""
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGridLayout, QFrame, QLabel, QGroupBox, QPushButton, QSizePolicy
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPixmap
from PySide6.QtSvgWidgets import QSvgWidget
import os
from core.path_manager import get_asset_path
from gui.theme import COLORS, FONTS

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
        """Crea una scheda statistica stilizzata."""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{ 
                background-color: {COLORS["bg_secondary"]};
                border: 1px solid {COLORS["border"]}; 
                border-radius: 4px; 
                padding: 10px;
            }}
        """)
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout = QVBoxLayout(card)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        t_label = QLabel(title)
        t_label.setFont(FONTS["small"])
        t_label.setStyleSheet(f"color: {COLORS['text_secondary']}; border: none;")
        t_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        v_label = QLabel(initial_value)
        v_label.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        v_label.setStyleSheet(f"color: {COLORS['accent']}; border: none;")
        v_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(t_label)
        layout.addWidget(v_label)
        
        return card, v_label

    @staticmethod
    def create_license_field(label: str, icon: str) -> tuple[QFrame, QLabel]:
        """Crea un campo informativo per il pannello licenza."""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{ 
                background-color: {COLORS["bg_secondary"]};
                border: 1px solid {COLORS["border"]}; 
                border-radius: 4px; 
                padding: 12px; 
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
        row.setStyleSheet(f"background-color: {COLORS['bg_secondary']}; border-radius: 4px; padding: 4px;")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(8, 4, 8, 4)
        
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
