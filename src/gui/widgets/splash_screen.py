"""
Intelleo PDF Splitter — Splash Screen (PySide6)
Finestra di caricamento iniziale con logo animato e barra di progresso.
"""

from PySide6.QtCore import (
    QEasingCurve,
    QPoint,
    QPropertyAnimation,
    Qt,
    QTimer,
)
from PySide6.QtGui import QColor, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsDropShadowEffect,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from core.path_manager import get_resource_path
from gui.theme import COLORS, FONTS


class SplashScreen(QWidget):
    """Finestra di caricamento iniziale stilizzata con animazioni avanzate."""

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(550, 350)

        # Layout principale
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(15, 15, 15, 15)

        # Contenitore con bordo arrotondato e ombra profonda
        self.container = QFrame()
        self.container.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_primary']};
                border-radius: 20px;
            }}
        """)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setXOffset(0)
        shadow.setYOffset(5)
        shadow.setColor(QColor(0, 0, 0, 100))
        self.container.setGraphicsEffect(shadow)

        self.content_layout = QVBoxLayout(self.container)  # refurb: ignore FURB184
        self.content_layout.setContentsMargins(40, 40, 40, 40)
        self.content_layout.setSpacing(10)

        # 1. Logo Animato
        self.logo_label = QLabel()
        icon_path = get_resource_path("icon.ico")
        icon = QIcon(icon_path)
        pixmap = icon.pixmap(80, 80)
        self.logo_label.setPixmap(pixmap)
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(self.logo_label)

        # 2. Titolo con animazione ingresso
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

        # 4. Barra di progresso moderna
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {COLORS['bg_tertiary']};
                border: none;
                border-radius: 2px;
            }}
            QProgressBar::chunk {{
                background-color: {COLORS['accent']};
                border-radius: 2px;
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

        # Inizializza animazioni
        self._setup_animations()

    def _setup_animations(self):
        """Configura le animazioni spettacolari di ingresso e loop."""
        # A. Pulsazione del Logo (Scale/Opacity loop)
        self.logo_opacity = QGraphicsOpacityEffect(self.logo_label)
        self.logo_label.setGraphicsEffect(self.logo_opacity)

        self.pulse_anim = QPropertyAnimation(self.logo_opacity, b"opacity")
        self.pulse_anim.setDuration(1500)
        self.pulse_anim.setStartValue(0.7)
        self.pulse_anim.setEndValue(1.0)
        self.pulse_anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        self.pulse_anim.setLoopCount(-1)
        self.pulse_anim.start()

        # B. Fade-in ingresso per l'intero widget (Opacità finestra)
        self.cont_opacity = QGraphicsOpacityEffect(self.container)
        self.container.setGraphicsEffect(self.cont_opacity)

        self.fade_in_anim = QPropertyAnimation(self.cont_opacity, b"opacity")
        self.fade_in_anim.setDuration(800)
        self.fade_in_anim.setStartValue(0.0)
        self.fade_in_anim.setEndValue(1.0)
        self.fade_in_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.fade_in_anim.start()

        # C. Slide-up del titolo e sottotitolo
        QTimer.singleShot(50, self._start_slide_animations)

    def _start_slide_animations(self):
        """Avvia le animazioni di scorrimento dopo il primo rendering."""
        orig_pos = self.title_label.pos()
        self.title_label.move(orig_pos.x(), orig_pos.y() + 20)

        self.title_anim = QPropertyAnimation(self.title_label, b"pos")
        self.title_anim.setDuration(800)
        self.title_anim.setStartValue(QPoint(orig_pos.x(), orig_pos.y() + 20))
        self.title_anim.setEndValue(orig_pos)
        self.title_anim.setEasingCurve(QEasingCurve.Type.OutBack)
        self.title_anim.start()

    def set_progress(self, value: int, message: str | None = None):
        """Aggiorna il progresso e opzionalmente il messaggio."""
        # Animazione fluida della barra di progresso
        self.bar_anim = QPropertyAnimation(self.progress_bar, b"value")
        self.bar_anim.setDuration(300)
        self.bar_anim.setEndValue(value)
        self.bar_anim.start()

        if message:
            self.status_label.setText(message)

        QApplication.processEvents()

    def set_version(self, version: str):
        """Imposta la versione visualizzata."""
        self.version_label.setText(f"Version {version}")
