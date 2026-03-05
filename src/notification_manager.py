"""
Intelleo PDF Splitter - Notification Manager (PySide6)
Gestisce le notifiche toast a comparsa.
"""
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout, QFrame
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont, QCursor
import time


class ToastNotification(QWidget):
    """Widget per una singola notifica toast."""

    def __init__(self, title, message, bg_color, fg_color, on_close=None):
        super().__init__()
        self._on_close_callback = on_close

        # Finestra senza bordi, sempre in primo piano
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setFixedSize(300, 80)

        # Layout principale
        self.setStyleSheet(f"background-color: {bg_color}; border-radius: 6px;")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 8, 10, 8)
        main_layout.setSpacing(2)

        # Header con titolo e pulsante chiudi
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        title_label = QLabel(title)
        title_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        title_label.setStyleSheet(f"color: {fg_color}; background: transparent;")
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        close_btn = QLabel("✕")
        close_btn.setFont(QFont("Segoe UI", 10))
        close_btn.setStyleSheet(
            f"color: {fg_color}; background: transparent; padding: 2px 4px;"
        )
        close_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        close_btn.mousePressEvent = lambda e: self.close_toast()
        header_layout.addWidget(close_btn)

        main_layout.addLayout(header_layout)

        # Messaggio
        msg_label = QLabel(message)
        msg_label.setFont(QFont("Segoe UI", 9))
        msg_label.setStyleSheet(f"color: {fg_color}; background: transparent;")
        msg_label.setWordWrap(True)
        main_layout.addWidget(msg_label)

        # Fade-in animation
        self.setWindowOpacity(0.0)
        self._fade_anim = QPropertyAnimation(self, b"windowOpacity")
        self._fade_anim.setDuration(200)
        self._fade_anim.setStartValue(0.0)
        self._fade_anim.setEndValue(0.95)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def show_animated(self):
        """Mostra il toast con animazione fade-in."""
        self.show()
        self._fade_anim.start()

    def close_toast(self):
        """Chiude il toast con pulizia."""
        if self._on_close_callback:
            self._on_close_callback(self)
        self.close()
        self.deleteLater()


class NotificationManager:
    """Gestisce le notifiche toast a comparsa."""

    def __init__(self, parent_widget):
        self.parent = parent_widget
        self.notifications = []
        self.unread_count = 0
        self.bell_label = None

    def setup_bell_icon(self, parent_layout_or_widget):
        """
        Aggiunge l'icona della campanella alla dashboard.

        Args:
            parent_layout_or_widget: Il layout o widget padre dove aggiungere l'icona.
                                      Accetta QLayout, QWidget, o oggetto con metodo addWidget.
        """
        container = QFrame()
        container.setStyleSheet("background: transparent;")

        container_layout = QHBoxLayout(container)
        container_layout.setContentsMargins(10, 0, 10, 0)

        self.bell_label = QLabel("🔔 0")
        self.bell_label.setFont(QFont("Segoe UI Emoji", 12))
        self.bell_label.setStyleSheet("color: #6C757D; background: transparent;")
        self.bell_label.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.bell_label.mousePressEvent = lambda e: self.show_history(e)
        container_layout.addWidget(self.bell_label)

        # Compatibilità: accetta sia layout che widget
        if hasattr(parent_layout_or_widget, 'addWidget'):
            parent_layout_or_widget.addWidget(container)
        elif hasattr(parent_layout_or_widget, 'layout') and parent_layout_or_widget.layout():
            parent_layout_or_widget.layout().addWidget(container)

    def notify(self, title, message, level="INFO"):
        """Crea una nuova notifica toast."""
        self.unread_count += 1
        self._update_bell()

        # Colori in base al livello
        bg_color = "#333333"
        fg_color = "#FFFFFF"
        if level == "SUCCESS":
            bg_color = "#198754"
        elif level == "WARNING":
            bg_color = "#FFC107"
            fg_color = "#000000"
        elif level == "ERROR":
            bg_color = "#DC3545"

        # Calcolo posizione (stacking dal basso a destra)
        from PySide6.QtWidgets import QApplication
        screen = QApplication.primaryScreen()
        if screen:
            screen_geo = screen.availableGeometry()
            screen_width = screen_geo.width()
            screen_height = screen_geo.height()
        else:
            screen_width = 1920
            screen_height = 1080

        window_width = 300
        window_height = 80
        margin = 20

        # Trova slot libero (conta solo toast ancora visibili)
        active_toasts = [n for n in self.notifications if n['window'].isVisible()]
        offset_y = margin + (len(active_toasts) * (window_height + 10))

        x = screen_width - window_width - margin
        y = screen_height - window_height - offset_y

        # Crea toast
        toast = ToastNotification(
            title, message, bg_color, fg_color,
            on_close=self._on_toast_closed
        )
        toast.move(x, y)
        toast.show_animated()

        # Tracking
        self.notifications.append({
            'window': toast, 'title': title,
            'msg': message, 'time': time.time()
        })

        # Auto close dopo 5 secondi
        QTimer.singleShot(5000, lambda t=toast: self._close_toast(t))

    def _on_toast_closed(self, toast):
        """Callback quando un toast viene chiuso."""
        self.notifications = [
            n for n in self.notifications if n['window'] is not toast
        ]

    def _fade_in(self, window, alpha=0):
        """Mantenuto per compatibilità, ma il fade è gestito da QPropertyAnimation."""
        pass

    def _close_toast(self, window):
        """Chiude un toast se ancora visibile."""
        try:
            if window and window.isVisible():
                window.close_toast()
        except RuntimeError:
            # Widget già distrutto
            pass

    def _update_bell(self):
        """Aggiorna il contatore sulla campanella."""
        if self.bell_label:
            color = '#DC3545' if self.unread_count > 0 else '#6C757D'
            self.bell_label.setText(f"🔔 {self.unread_count}")
            self.bell_label.setStyleSheet(
                f"color: {color}; background: transparent;"
            )

    def show_history(self, event=None):
        """Reset del contatore notifiche."""
        self.unread_count = 0
        self._update_bell()
        # TODO: Mostrare finestra storico se richiesto (per ora resetta solo)
