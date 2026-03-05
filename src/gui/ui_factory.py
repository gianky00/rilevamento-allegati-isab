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
    def create_combined_stat_card(title: str) -> tuple[QFrame, QLabel, QLabel, QLabel, QLabel]:
        """Crea una scheda statistica che raggruppa Doc e Pagine con separazione sessione/totale."""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{ 
                background-color: {COLORS["bg_secondary"]};
                border: 1px solid {COLORS["border"]}; 
                border-radius: 6px; 
                padding: 10px;
            }}
        """)
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout = QVBoxLayout(card)
        layout.setSpacing(10)
        
        t_label = QLabel(title)
        t_label.setFont(FONTS["small_bold"])
        t_label.setStyleSheet(f"color: {COLORS['accent']}; border: none; margin-bottom: 2px;")
        t_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(t_label)

        def create_stat_row(label_text: str):
            row_layout = QVBoxLayout()
            row_layout.setSpacing(2)
            
            lbl = QLabel(label_text)
            lbl.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            lbl.setStyleSheet("color: #6B7280; border: none;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            row_layout.addWidget(lbl)
            
            vals = QHBoxLayout()
            s_val = QLabel("0")
            s_val.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
            s_val.setStyleSheet(f"color: {COLORS['accent']}; border: none;")
            s_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            sep = QLabel("/")
            sep.setStyleSheet("color: #D1D5DB; border: none;")
            
            t_val = QLabel("0")
            t_val.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
            t_val.setStyleSheet(f"color: {COLORS['text_primary']}; border: none;")
            t_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            vals.addStretch()
            vals.addWidget(s_val)
            vals.addWidget(sep)
            vals.addWidget(t_val)
            vals.addStretch()
            row_layout.addLayout(vals)
            return row_layout, s_val, t_val

        # Sezione Documenti
        row_doc, ds, dt = create_stat_row("DOCUMENTI (SESS / TOT)")
        layout.addLayout(row_doc)
        
        # Divisore orizzontale
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f"background-color: {COLORS['border']}; max-height: 1px;")
        layout.addWidget(line)
        
        # Sezione Pagine
        row_pag, ps, pt = create_stat_row("PAGINE (SESS / TOT)")
        layout.addLayout(row_pag)
        
        return card, ds, dt, ps, pt

    @staticmethod
    def create_license_card(title: str) -> tuple[QFrame, QLabel, QVBoxLayout]:
        """Crea una scheda dedicata alla licenza e info sistema."""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{ 
                background-color: {COLORS["bg_secondary"]};
                border: 1px solid {COLORS["border"]}; 
                border-radius: 6px; 
                padding: 8px;
            }}
        """)
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout = QVBoxLayout(card)
        layout.setSpacing(4)
        
        t_label = QLabel(title)
        t_label.setFont(FONTS["small_bold"])
        t_label.setStyleSheet(f"color: {COLORS['text_secondary']}; border: none; margin-bottom: 2px;")
        t_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(t_label)
        
        status_label = QLabel("VERIFICA...")
        status_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_label.setStyleSheet(f"color: {COLORS['text_muted']}; border: none;")
        layout.addWidget(status_label)
        
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"background-color: {COLORS['border']}; max-height: 1px; margin: 4px 0;")
        layout.addWidget(sep)
        
        content_layout = QVBoxLayout()
        content_layout.setSpacing(2)
        layout.addLayout(content_layout)
        
        return card, status_label, content_layout

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
