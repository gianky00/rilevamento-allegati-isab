"""
Intelleo PDF Splitter - Notification Manager (PySide6)
Gestisce le notifiche toast a comparsa.
"""

import time
from contextlib import suppress
from pathlib import Path

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt, QTimer
from PySide6.QtGui import QCursor, QFont
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget


class ToastNotification(QWidget):
    """Widget per una singola notifica toast."""

    def __init__(self, title, message, bg_color, fg_color, on_close=None):
        """Inizializza un widget di notifica toast a comparsa."""
        super().__init__()
        self._on_close_callback = on_close

        # Finestra senza bordi, sempre in primo piano
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
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
        close_btn.setStyleSheet(f"color: {fg_color}; background: transparent; padding: 2px 4px;")
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
        """Inizializza il gestore delle notifiche e lo collega al controller se disponibile."""
        self.parent = parent_widget
        self.notifications = []
        self.unread_count = 0
        self.bell_container = None
        self.bell_svg = None
        self.bell_count_label = None

        # Connessione automatica ai segnali del controller se presente
        if hasattr(parent_widget, "controller"):
            parent_widget.controller.log_received.connect(self._on_controller_log)

    def _on_controller_log(self, message: str, level: str, replace_last: bool = False) -> None:
        """Riceve log dal controller e mostra notifiche per eventi critici."""
        if level in ("SUCCESS", "ERROR"):
            # Filtra solo i messaggi più importanti per i toast
            important_keywords = ("File completato", "ELABORAZIONE COMPLETATA", "Errore", "sincronizzata", "aggiornata")
            if any(kw in message for kw in important_keywords):
                self.notify(level, message, level)

    def setup_bell_icon(self, parent_layout_or_widget):
        """
        Aggiunge l'icona della campanella alla dashboard.
        """
        self.bell_container = QFrame()
        self.bell_container.setStyleSheet("background: transparent;")
        self.bell_container_layout = QHBoxLayout(self.bell_container)
        self.bell_container_layout.setContentsMargins(10, 0, 10, 0)
        self.bell_container_layout.setSpacing(5)

        self.bell_svg = None
        self.bell_count_label = QLabel("0")
        self.bell_count_label.setStyleSheet("color: #6C757D; background: transparent;")
        self.bell_container_layout.addWidget(self.bell_count_label)

        self.bell_container.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.bell_container.mousePressEvent = self.show_history

        self._update_bell()

        if hasattr(parent_layout_or_widget, "addWidget"):
            parent_layout_or_widget.addWidget(self.bell_container)
        elif hasattr(parent_layout_or_widget, "layout") and parent_layout_or_widget.layout():
            parent_layout_or_widget.layout().addWidget(self.bell_container)

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
        active_toasts = [n for n in self.notifications if n["window"].isVisible()]
        offset_y = margin + (len(active_toasts) * (window_height + 10))

        x = screen_width - window_width - margin
        y = screen_height - window_height - offset_y

        # Crea toast
        toast = ToastNotification(title, message, bg_color, fg_color, on_close=self._on_toast_closed)
        toast.move(x, y)
        toast.show_animated()

        # Tracking e Cronologia (manteniamo le ultime 50 notifiche)
        if not hasattr(self, "history"):
            self.history = []
        self.history.append({"title": title, "msg": message, "time": time.time(), "level": level})
        if len(self.history) > 50:
            self.history.pop(0)

        self.notifications.append({"window": toast, "title": title, "msg": message, "time": time.time()})

        # Auto close dopo 5 secondi
        QTimer.singleShot(5000, lambda t=toast: self._close_toast(t))

    def _on_toast_closed(self, toast):
        """Callback quando un toast viene chiuso."""
        self.notifications = [n for n in self.notifications if n["window"] is toast]

    def _fade_in(self, window, alpha=0):
        """Mantenuto per compatibilità, ma il fade è gestito da QPropertyAnimation."""

    def _close_toast(self, window):
        """Chiude un toast se ancora visibile."""
        with suppress(RuntimeError):
            if window and window.isVisible():
                window.close_toast()

    def _update_bell(self):
        """Aggiorna il contatore sulla campanella."""
        if self.bell_container:
            # Rimuove vecchio SVG
            if self.bell_svg:
                self.bell_svg.setParent(None)
                self.bell_svg.deleteLater()

            # Crea nuovo SVG
            color = "#DC3545" if self.unread_count > 0 else "#6C757D"

            base_path = Path(__file__).resolve().parents[2]
            path = base_path / "assets" / "bell.svg"
            self.bell_svg = QSvgWidget(str(path))
            self.bell_svg.setFixedSize(20, 20)
            self.bell_container_layout.insertWidget(0, self.bell_svg)

            self.bell_count_label.setText(str(self.unread_count))
            self.bell_count_label.setStyleSheet(f"color: {color}; background: transparent; font-weight: bold;")

    def show_history(self, event=None):
        """Reset del contatore notifiche e mostra la cronologia all'utente in un popup interno."""
        self.unread_count = 0
        self._update_bell()

        if not hasattr(self, "history") or not self.history:
            return

        from PySide6.QtCore import Qt
        from PySide6.QtGui import QFont
        from PySide6.QtWidgets import QFrame, QListWidget, QListWidgetItem, QVBoxLayout

        # Crea il popup se non esiste
        if not hasattr(self, "_history_popup") or self._history_popup is None:
            self._history_popup = QFrame(self.parent, Qt.WindowType.Popup)
            self._history_popup.setFixedWidth(350)
            self._history_popup.setMinimumHeight(200)
            self._history_popup.setMaximumHeight(400)
            self._history_popup.setStyleSheet("""
                QFrame {
                    background-color: #2D2D30;
                    border: 1px solid #444444;
                    border-radius: 6px;
                }
                QListWidget {
                    background-color: #2D2D30;
                    border: none;
                    color: #E0E0E0;
                    outline: none;
                }
                QListWidget::item {
                    border-bottom: 1px solid #333333;
                    padding: 8px;
                }
                QListWidget::item:hover {
                    background-color: #3E3E42;
                }
            """)

            layout = QVBoxLayout(self._history_popup)
            layout.setContentsMargins(5, 5, 5, 5)
            layout.setSpacing(0)

            # Label intestazione
            from PySide6.QtWidgets import QLabel

            header = QLabel(" Centro Notifiche ")
            header.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            header.setStyleSheet("color: #0d6efd; padding: 5px; border-bottom: 1px solid #444444;")
            layout.addWidget(header)

            self._history_list = QListWidget()
            self._history_list.setFont(QFont("Segoe UI", 9))
            self._history_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            layout.addWidget(self._history_list)
        else:
            self._history_list.clear()

        # Popola la lista in ordine inverso
        for notif in reversed(self.history):
            time_str = time.strftime("%H:%M:%S", time.localtime(notif["time"]))
            level_emoji = (
                "✅"
                if notif["title"] == "SUCCESS"
                else "⚠️"
                if notif["title"] == "WARNING"
                else "🛑"
                if notif["title"] == "ERROR"
                else "ℹ️"
            )

            item = QListWidgetItem(f"{time_str} - {level_emoji} {notif['msg']}")
            # Wrappa il test per favorire la lettura multi-linea
            item.setToolTip(notif["msg"])
            self._history_list.addItem(item)

        # Calcola posizione: in basso a destra rispetto all'icona della campanella
        if self.bell_container:
            global_pos = self.bell_container.mapToGlobal(self.bell_container.rect().bottomRight())
            # Sposta a sinistra della larghezza del popup per farlo allineare a destra
            global_pos.setX(global_pos.x() - 350)
            self._history_popup.move(global_pos)

        self._history_popup.show()
