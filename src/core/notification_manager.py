"""
Intelleo PDF Splitter - Notification Manager (PySide6)
Gestisce le notifiche toast a comparsa.
"""

import logging
import time
from contextlib import suppress
from pathlib import Path

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt, QTimer
from PySide6.QtGui import QCursor, QFont
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

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
    """Widget per una singola notifica toast."""

    def __init__(self, title, message, bg_color, fg_color, on_close=None):
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
        close_btn = QLabel("✕")
        close_btn.setStyleSheet(f"color: {fg_color}; padding: 2px; border: none;")
        close_btn.mousePressEvent = lambda e: self.close_toast()
        header_layout.addWidget(close_btn)
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

    def show_animated(self):
        self.show()
        self._fade_anim.start()

    def close_toast(self):
        if self._on_close_callback: self._on_close_callback(self)
        self.close()
        self.deleteLater()


class NotificationManager:
    """Gestisce le notifiche toast (Standard OOP)."""

    def __init__(self, parent_widget):
        self.parent = parent_widget
        self.notifications = []
        self.active_toasts = [] # Alias per i test
        self.unread_count = 0
        self.history = []
        self.bell_container = None
        self.bell_svg = None
        self.bell_count_label = None

        if hasattr(parent_widget, "controller"):
            parent_widget.controller.log_received.connect(self.on_controller_log)

    def on_controller_log(self, message: str, level: str, replace_last: bool = False) -> None:
        """Alias pubblico per i test."""
        if level in ("SUCCESS", "ERROR", "WARNING"):
            self.notify(message, level)

    def notify(self, message: str, level: str = "INFO", title: str | None = None):
        """Crea una nuova notifica toast."""
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

    def _on_toast_closed(self, toast):
        self.notifications = [n for n in self.notifications if n["window"] is not toast]
        self.active_toasts = [n["window"] for n in self.notifications]

    def setup_bell_icon(self, parent):
        self.bell_container = QFrame()
        self.bell_count_label = QLabel("0")
        self._update_bell()

    def _update_bell(self):
        if self.bell_count_label:
            self.bell_count_label.setText(str(self.unread_count))

    def show_history(self, event=None):
        self.unread_count = 0
        self._update_bell()

    def show_toast(self, title, message, level="INFO"):
        """Alias richiesto dai test."""
        self.notify(message, level, title)
        return self.notifications[-1]["window"]
