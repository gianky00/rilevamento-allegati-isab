"""
Intelleo PDF Splitter - Notification Manager (PySide6)
Gestisce le notifiche toast a comparsa.
"""

import logging
import time
from typing import Any, cast

from PySide6.QtCore import QPropertyAnimation, Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

logger = logging.getLogger("MAIN")

# Fallback COLORS
COLORS = {
    "bg_primary": "#FFFFFF",
    "bg_secondary": "#F8F9FA",
    "text_primary": "#111827",
    "accent": "#2563EB",
    "border": "#E5E7EB",
    "danger": "#DC3545",
    "success": "#198754",
    "warning": "#FFC107",
    "text_secondary": "#6B7280"
}


class ToastNotification(QWidget):
    """Widget per una singola notifica toast a comparsa."""

    def __init__(self, title: str, message: str, bg_color: str, fg_color: str, on_close: Any = None) -> None:
        """Inizializza la notifica toast con stile e contenuti specificati."""
        super().__init__()
        self._on_close_callback = on_close
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setFixedSize(300, 80)
        self.setStyleSheet(f"background-color: {bg_color}; border: 1px solid {COLORS['border']}; border-radius: 6px;")

        main_layout = QVBoxLayout(self)
        header_layout = QHBoxLayout()
        title_label = QLabel(title)
        title_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        title_label.setStyleSheet(f"color: {fg_color}; border: none;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(20, 20)
        self.close_btn.setFlat(True)
        self.close_btn.setStyleSheet(f"color: {fg_color}; padding: 0px; border: none; font-weight: bold;")
        self.close_btn.clicked.connect(self.close_toast)
        header_layout.addWidget(self.close_btn)
        main_layout.addLayout(header_layout)

        msg_label = QLabel(message)
        msg_label.setFont(QFont("Segoe UI", 9))
        msg_label.setStyleSheet(f"color: {fg_color}; border: none;")
        msg_label.setWordWrap(True)
        main_layout.addWidget(msg_label)

        self.setWindowOpacity(0.0)
        self._fade_anim = QPropertyAnimation(self, b"windowOpacity")
        self._fade_anim.setDuration(200)
        self._fade_anim.setStartValue(0.0)
        self._fade_anim.setEndValue(0.95)

    def show_animated(self) -> None:
        """Mostra la notifica avviando l'animazione di dissolvenza."""
        self.show()
        self._fade_anim.start()

    def close_toast(self) -> None:
        """Chiude la notifica, invoca la callback e distrugge il widget."""
        if self._on_close_callback:
            self._on_close_callback(self)
        self.close()
        self.deleteLater()


class NotificationManager:
    """Gestisce il ciclo di vita delle notifiche toast e la loro integrazione con il controller."""

    def __init__(self, parent_widget: QWidget) -> None:
        """Inizializza il manager collegandolo opzionalmente al controller del parent."""
        self.parent = parent_widget
        self.notifications: list[dict[str, Any]] = []
        self.active_toasts: list[ToastNotification] = []  # Alias per i test
        self.unread_count = 0
        self.history: list[dict[str, Any]] = []
        self.bell_container: QFrame | None = None
        self.bell_svg: Any = None
        self.bell_count_label: QLabel | None = None

        if hasattr(parent_widget, "controller"):
            parent_widget.controller.log_received.connect(self.on_controller_log)

    def on_controller_log(self, message: str, level: str, replace_last: bool = False) -> None:
        """Riceve log dal controller e attiva una notifica per i livelli rilevanti."""
        if level in ("SUCCESS", "ERROR", "WARNING"):
            self.notify(message, level)

    def notify(self, message: str, level: str = "INFO", title: str | None = None) -> None:
        """Crea, visualizza e registra una nuova notifica toast."""
        self.unread_count += 1
        title = title or level

        bg_color = COLORS["success"] if level == "SUCCESS" else COLORS["danger"] if level == "ERROR" else COLORS["warning"] if level == "WARNING" else "#333"
        fg_color = "#FFFFFF" if level != "WARNING" else "#000000"

        toast = ToastNotification(title, message, bg_color, fg_color, on_close=self._on_toast_closed)
        self.notifications.append({"window": toast})
        self.active_toasts = [n["window"] for n in self.notifications]
        self.history.append({"title": title, "msg": message, "time": time.time(), "level": level})

        toast.show_animated()
        QTimer.singleShot(5000, toast.close_toast)
        self._update_bell()

    def _on_toast_closed(self, toast: ToastNotification) -> None:
        """Rimuove la notifica dalla lista dei toast attivi quando viene chiusa."""
        self.notifications = [n for n in self.notifications if n["window"] is not toast]
        self.active_toasts = [n["window"] for n in self.notifications]

    def setup_bell_icon(self, parent: QHBoxLayout) -> None:
        """Inizializza gli elementi grafici dell'icona campana nel layout parent."""
        self.bell_container = QFrame()
        self.bell_count_label = QLabel("0")
        self._update_bell()

    def _update_bell(self) -> None:
        """Aggiorna il contatore numerico sull'icona della campana."""
        if self.bell_count_label:
            self.bell_count_label.setText(str(self.unread_count))

    def show_history(self, event: Any = None) -> None:
        """Azzera il contatore delle notifiche non lette."""
        self.unread_count = 0
        self._update_bell()

    def show_toast(self, title: str, message: str, level: str = "INFO") -> ToastNotification:
        """Crea una notifica e restituisce il widget creato (Metodo richiesto dai test)."""
        self.notify(message, level, title)
        return cast("ToastNotification", self.notifications[-1]["window"])
