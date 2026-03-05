"""
Intelleo PDF Splitter — Splash Screen (PySide6)
Finestra di caricamento iniziale con barra di progresso.
"""

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QColor
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
    QGraphicsDropShadowEffect
)

from gui.theme import COLORS, FONTS


class SplashScreen(QWidget):
    """Finestra di caricamento iniziale stilizzata."""

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(500, 300)

        # Layout principale
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)

        # Contenitore con bordo arrotondato e ombra
        self.container = QFrame()
        self.container.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_primary']};
                border-radius: 15px;
            }}
        """)
        
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(0)
        shadow.setColor(QColor(0, 0, 0, 80))
        self.container.setGraphicsEffect(shadow)

        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(30, 30, 30, 30)
        container_layout.setSpacing(15)

        # Titolo / Logo Placeholder
        self.title_label = QLabel("INTELLEO PDF SPLITTER")
        self.title_label.setFont(FONTS["heading"])
        self.title_label.setStyleSheet(f"color: {COLORS['accent']}; border: none;")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(self.title_label)

        self.subtitle_label = QLabel("Automazione Documentale Intelligente")
        self.subtitle_label.setFont(FONTS["body"])
        self.subtitle_label.setStyleSheet(f"color: {COLORS['text_secondary']}; border: none;")
        self.subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(self.subtitle_label)

        container_layout.addStretch()

        # Messaggio di stato
        self.status_label = QLabel("Inizializzazione sistema...")
        self.status_label.setFont(FONTS["small"])
        self.status_label.setStyleSheet(f"color: {COLORS['text_muted']}; border: none;")
        container_layout.addWidget(self.status_label)

        # Barra di progresso
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {COLORS['bg_tertiary']};
                border: none;
                border-radius: 3px;
            }}
            QProgressBar::chunk {{
                background-color: {COLORS['accent']};
                border-radius: 3px;
            }}
        """)
        container_layout.addWidget(self.progress_bar)

        self.version_label = QLabel("v2.0 (Stable Build)")
        self.version_label.setFont(FONTS["small"])
        self.version_label.setStyleSheet(f"color: {COLORS['text_muted']}; border: none;")
        self.version_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        container_layout.addWidget(self.version_label)

        self.main_layout.addWidget(self.container)

    def set_progress(self, value: int, message: str = None):
        """Aggiorna il progresso e opzionalmente il messaggio."""
        self.progress_bar.setValue(value)
        if message:
            self.status_label.setText(message)
        # Forza Qt a processare gli eventi per aggiornare la GUI immediatamente
        from PySide6.QtWidgets import QApplication
        QApplication.processEvents()

    def set_version(self, version: str):
        """Imposta la versione visualizzata."""
        self.version_label.setText(f"v{version}")
