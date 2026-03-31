"""
Fabbrica per i componenti dell'interfaccia utente (SRP).
Riduce il boilerplate in MainApp gestendo la creazione di layout complessi.
"""

from PySide6.QtCore import Property, QPropertyAnimation, Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
)

from core.path_manager import get_asset_path
from gui.theme import COLORS, FONTS
from shared.security_utils import sanitize_html


class AnimatedButton(QPushButton):
    """Pulsante con animazioni fluide per hover e pressione."""

    def __init__(self, text: str, parent=None, is_primary=False):
        """
        Inizializza il pulsante animato.

        Args:
            text (str): Testo del pulsante.
            parent (QWidget, optional): Widget genitore. Defaults to None.
            is_primary (bool, optional): Se True, usa lo stile primario (accento). Defaults to False.
        """
        super().__init__(text, parent)
        self.is_primary = is_primary
        self._bg_color = QColor(COLORS["accent"] if is_primary else COLORS["bg_secondary"])
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_style()

    def _update_style(self):
        """Aggiorna lo stile CSS del pulsante in base al colore corrente."""
        color = self._bg_color.name()
        text_color = "white" if self.is_primary else COLORS["text_primary"]
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: {text_color};
                border: none;
                border-radius: 5px;
                padding: 8px 15px;
                font-weight: bold;
            }}
        """)

    def enterEvent(self, event):
        """Gestisce l'evento di entrata del mouse per l'hover."""
        self.animate_color(COLORS["accent_hover"] if self.is_primary else COLORS["bg_tertiary"])
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Gestisce l'evento di uscita del mouse."""
        self.animate_color(COLORS["accent"] if self.is_primary else COLORS["bg_secondary"])
        super().leaveEvent(event)

    def animate_color(self, target_color_hex):
        """
        Avvia l'animazione del colore di sfondo.

        Args:
            target_color_hex (str): Colore esadecimale di destinazione.
        """
        self._anim = QPropertyAnimation(self, b"background_color")
        self._anim.setDuration(200)
        self._anim.setEndValue(QColor(target_color_hex))
        self._anim.start()

    def get_bg_color(self):
        """Getter per la property background_color."""
        return self._bg_color

    def set_bg_color(self, color):
        """Setter per la property background_color."""
        self._bg_color = color
        self._update_style()

    background_color = Property(QColor, get_bg_color, set_bg_color)


class UIFactory:
    """Collezione di metodi statici per la creazione di componenti UI standardizzati."""

    @staticmethod
    def create_svg_icon(filename: str, size: int = 20) -> QSvgWidget:
        """
        Crea un widget SVG caricando il file specificato.

        Args:
            filename (str): Nome del file icona negli asset.
            size (int, optional): Dimensione fissa (quadrata). Defaults to 20.

        Returns:
            QSvgWidget: Il widget icona pronto per l'uso.
        """
        path = get_asset_path(filename)
        svg = QSvgWidget(path)
        svg.setFixedSize(size, size)
        return svg

    @staticmethod
    def create_stat_card(title: str, initial_value: str) -> tuple[QFrame, QLabel]:
        """
        Crea una scheda statistica stilizzata con font uniforme.

        Args:
            title (str): Titolo della scheda.
            initial_value (str): Valore iniziale da mostrare.

        Returns:
            tuple[QFrame, QLabel]: La riga/cornice della scheda e la label del valore.
        """
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS["bg_secondary"]};
                border: 1px solid {COLORS["border"]};
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
        v_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        v_label.setStyleSheet(f"color: {COLORS['accent']}; border: none;")
        v_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(t_label)
        layout.addWidget(v_label)

        return card, v_label

    @staticmethod
    def create_combined_stat_card(title: str) -> tuple[QFrame, QLabel, QLabel, QLabel, QLabel]:
        """
        Crea una scheda statistica che raggruppa Doc e Pagine fianco a fianco per massima compattezza.

        Args:
            title (str): Titolo superiore del gruppo.

        Returns:
            tuple[QFrame, QLabel, QLabel, QLabel, QLabel]: Card e le 4 label (DocSess, DocTot, PagSess, PagTot).
        """
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS["bg_secondary"]};
                border: 1px solid {COLORS["border"]};
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
        content.setContentsMargins(0, 0, 0, 0)

        def create_stat_sub_col(label_text: str):
            """Crea una sotto-colonna per i valori di sessione e totali."""
            col = QVBoxLayout()
            col.setSpacing(0)

            lbl = QLabel(label_text)
            lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            lbl.setStyleSheet(f"color: {COLORS['text_secondary']}; border: none;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            col.addWidget(lbl)

            vals = QHBoxLayout()
            vals.setSpacing(2)
            s_val = QLabel("0")
            s_val.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
            s_val.setStyleSheet(f"color: {COLORS['accent']}; border: none;")

            sep = QLabel("/")
            sep.setStyleSheet(f"color: {COLORS['text_muted']}; border: none;")

            t_val = QLabel("0")
            t_val.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
            t_val.setStyleSheet(f"color: {COLORS['text_primary']}; border: none;")

            vals.addStretch()
            vals.addWidget(s_val)
            vals.addWidget(sep)
            vals.addWidget(t_val)
            vals.addStretch()
            col.addLayout(vals)
            return col, s_val, t_val

        # Doc a sinistra
        col_doc, ds, dt = create_stat_sub_col("DOCUMENTI (SESS / TOT)")
        content.addLayout(col_doc)

        # Divisore verticale
        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        line.setStyleSheet(f"background-color: {COLORS['border']}; max-width: 1px;")
        content.addWidget(line)

        # Pagine a destra
        col_pag, ps, pt = create_stat_sub_col("PAGINE (SESS / TOT)")
        content.addLayout(col_pag)

        layout.addLayout(content)
        return card, ds, dt, ps, pt

    @staticmethod
    def create_license_card(title: str) -> tuple[QFrame, QLabel, QGridLayout]:
        """
        Crea una scheda dedicata alla licenza con layout a due colonne.

        Args:
            title (str): Titolo della sezione licenza.

        Returns:
            tuple[QFrame, QLabel, QGridLayout]: Card, label di stato e grid per i dettagli.
        """
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS["bg_secondary"]};
                border: 1px solid {COLORS["border"]};
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
    def create_compact_info_row(label: str, icon_file: str) -> tuple[QFrame, QLabel]:
        """
        Crea una riga informativa compatta con icona SVG.

        Args:
            label (str): Etichetta informativa.
            icon_file (str): File icona SVG da caricare.

        Returns:
            tuple[QFrame, QLabel]: Riga/cornice e la label del valore dinamico.
        """
        row = QFrame()
        row.setStyleSheet(
            f"background-color: {COLORS['bg_secondary']}; border: none; border-radius: 4px; padding: 0px;"
        )
        layout = QHBoxLayout(row)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(6)

        svg_icon = UIFactory.create_svg_icon(icon_file, 16)
        layout.addWidget(svg_icon)

        text_lbl = QLabel(label + ":")
        text_lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        text_lbl.setStyleSheet(f"color: {COLORS['text_secondary']}; border: none;")
        layout.addWidget(text_lbl)

        v_label = QLabel("...")
        v_label.setFont(FONTS["mono_bold"])
        v_label.setStyleSheet(f"color: {COLORS['accent']}; border: none;")
        layout.addWidget(v_label)
        layout.addStretch()

        return row, v_label

    @staticmethod
    def show_message(
        parent,
        title: str,
        text: str,
        icon: QMessageBox.Icon = QMessageBox.Icon.Information,
        is_rich_text: bool = False,
    ) -> int:
        """
        Mostra un messaggio QMessageBox sanificato (Pillar 4).
        Di default usa PlainText. Se abilitato RichText, sanifica l'input.
        """
        msg = QMessageBox(parent)
        msg.setWindowTitle(title)
        msg.setIcon(icon)

        if is_rich_text:
            sanitized_text = sanitize_html(text)
            msg.setTextFormat(Qt.TextFormat.RichText)
            msg.setText(sanitized_text)
        else:
            msg.setTextFormat(Qt.TextFormat.PlainText)
            msg.setText(text)

        return msg.exec()

    @staticmethod
    def set_secure_text(widget: QLabel, text: str, is_rich_text: bool = False) -> None:
        """
        Imposta il testo di una QLabel in modo sicuro (Pillar 4).
        """
        if is_rich_text:
            sanitized_text = sanitize_html(text)
            widget.setTextFormat(Qt.TextFormat.RichText)
            widget.setText(sanitized_text)
        else:
            widget.setTextFormat(Qt.TextFormat.PlainText)
            widget.setText(text)
