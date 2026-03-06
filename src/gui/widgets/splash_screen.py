"""
Intelleo PDF Splitter — Splash Screen (PySide6)
Finestra di caricamento iniziale semplificata per stabilità massima.
"""

from PySide6.QtCore import (
    Qt,
)
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from core.path_manager import get_resource_path
from gui.theme import COLORS, FONTS


class SplashScreen(QWidget):
    """Finestra di caricamento iniziale stilizzata senza effetti grafici pesanti per evitare crash QPainter."""

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(550, 350)

        # Layout principale
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(15, 15, 15, 15)

        # Contenitore con bordo arrotondato (Design pulito via QSS)
        self.container = QFrame()
        self.container.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS["bg_primary"]};
                border: 1px solid {COLORS["border"]};
                border-radius: 20px;
            }}
        """)

        self.content_layout = QVBoxLayout(self.container)
        self.content_layout.setContentsMargins(40, 40, 40, 40)
        self.content_layout.setSpacing(10)

        # 1. Logo
        self.logo_label = QLabel()
        icon_path = get_resource_path("icon.ico")
        icon = QIcon(icon_path)
        self.logo_label.setPixmap(icon.pixmap(80, 80))
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(self.logo_label)

        # 2. Titolo
        self.title_label = QLabel("INTELLEO PDF SPLITTER")
        self.title_label.setFont(FONTS["heading"])
        self.title_label.setStyleSheet(f"color: {COLORS['accent']}; border: none; letter-spacing: 1px;")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(self.title_label)

        self.subtitle_label = QLabel("Automazione Documentale Intelligente")
        self.subtitle_label.setFont(FONTS["body"])
        self.subtitle_label.setStyleSheet(f"color: {COLORS['text_secondary']}; border: none;")
        self.subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(self.subtitle_label)

        self.content_layout.addStretch()

        # 3. Messaggio di stato
        self.status_label = QLabel("Inizializzazione sistema...")
        self.status_label.setFont(FONTS["small"])
        self.status_label.setStyleSheet(f"color: {COLORS['text_muted']}; border: none;")
        self.content_layout.addWidget(self.status_label)

        # 4. Barra di progresso
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {COLORS["bg_tertiary"]};
                border: none;
                border-radius: 3px;
            }}
            QProgressBar::chunk {{
                background-color: {COLORS["accent"]};
                border-radius: 3px;
            }}
        """)
        self.content_layout.addWidget(self.progress_bar)

        # 5. Footer Info
        footer = QHBoxLayout()
        self.version_label = QLabel("v2.0")
        self.version_label.setFont(FONTS["small"])
        self.version_label.setStyleSheet(f"color: {COLORS['text_muted']};")
        footer.addWidget(self.version_label)

        footer.addStretch()

        self.build_label = QLabel("Stable Build")
        self.build_label.setFont(FONTS["small"])
        self.build_label.setStyleSheet(f"color: {COLORS['text_muted']};")
        footer.addWidget(self.build_label)

        self.content_layout.addLayout(footer)
        self.main_layout.addWidget(self.container)

    def set_progress(self, value: int, message: str | None = None):
        """Aggiorna il progresso e il messaggio istantaneamente per stabilità."""
        self.progress_bar.setValue(value)
        if message:
            self.status_label.setText(message)

        # Forza Qt a elaborare gli eventi grafici immediatamente
        QApplication.processEvents()

    def set_version(self, version: str):
        """Imposta la versione visualizzata."""
        self.version_label.setText(f"Version {version}")
