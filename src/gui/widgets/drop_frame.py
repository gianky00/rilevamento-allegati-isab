"""
Intelleo PDF Splitter — DropFrame
Frame che accetta il drag & drop nativo Qt di file PDF.
"""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout

from gui.theme import COLORS, FONTS


class DropFrame(QFrame):
    """Frame che accetta il drag & drop di file PDF."""

    def __init__(self, on_drop_callback, parent=None):
        """Inizializza il frame abilitando il supporto al drop di file."""
        super().__init__(parent)
        self.on_drop_callback = on_drop_callback

        # Abilita esplicitamente i drop e il rendering dello stile
        self.setAcceptDrops(True)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._set_default_style()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        self.lbl = QLabel("Trascina file o cartelle qui per avviare l'elaborazione automatica", self)
        self.lbl.setFont(FONTS["small"])
        self.lbl.setStyleSheet(f"color: {COLORS['text_secondary']}; border: none; background: transparent;")
        self.lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl.setWordWrap(True)

        # IMPORTANTE: L'etichetta non deve bloccare gli eventi di mouse/drop per il frame
        self.lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        layout.addWidget(self.lbl)

    def setText(self, text: str) -> None:
        """Aggiorna il testo dell'etichetta interna."""
        self.lbl.setText(text)

    def _set_default_style(self):
        """Ripristina lo stile grafico standard (bordo tratteggiato)."""
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS["bg_secondary"]};
                border: 2px dashed {COLORS["border"]};
                border-radius: 12px;
            }}
        """)

    def dragEnterEvent(self, event: QDragEnterEvent):
        """Gestisce l'evento di trascinamento file sopra il widget."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet(f"""
                QFrame {{
                    background-color: {COLORS["accent"]}15;
                    border: 2px dashed {COLORS["accent"]};
                    border-radius: 12px;
                }}
            """)

    def dragLeaveEvent(self, event):
        """Gestisce l'uscita del cursore dal widget senza rilascio."""
        self._set_default_style()

    def dropEvent(self, event: QDropEvent):
        """Gestisce il rilascio dei file PDF nel widget."""
        self._set_default_style()
        files = []
        for url in event.mimeData().urls():
            path_str = url.toLocalFile()
            if not path_str:
                continue
            path = Path(path_str)
            if path.exists():
                if path.is_dir():
                    for pdf_file in path.rglob("*.pdf"):
                        files.append(str(pdf_file.resolve()))
                elif path.suffix.lower() == ".pdf":
                    files.append(str(path.resolve()))

        if files:
            self.on_drop_callback(files)
            event.acceptProposedAction()
        else:
            event.ignore()
