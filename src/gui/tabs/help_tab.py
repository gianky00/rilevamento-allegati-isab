"""
Modulo per la Tab Guida (SRP).
"""
from typing import Any
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QSplitter, QListWidget, QTextEdit
)
from PySide6.QtCore import Qt
from gui.theme import COLORS, FONTS
from shared.constants import APP_DATA_DIR

class HelpTab(QWidget):
    """Gestisce la costruzione e i widget della tab Guida."""

    def __init__(self, parent: QWidget, main_app: Any) -> None:
        """Inizializza la tab della guida caricando i contenuti informativi."""
        super().__init__(parent)
        self.main_app = main_app
        self._init_ui()

    def _init_ui(self) -> None:
        """Configura l'interfaccia utente della guida con il browser dei contenuti."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        header = QHBoxLayout()
        h = QLabel("Guida all'Uso")
        h.setFont(FONTS["heading"])
        h.setStyleSheet(f"color: {COLORS['accent']};")
        header.addWidget(h)
        
        btn_open = QPushButton("Apri Cartella Dati")
        btn_open.clicked.connect(lambda: os.startfile(APP_DATA_DIR))
        header.addWidget(btn_open)
        layout.addLayout(header)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.help_topics_list = QListWidget()
        self.help_detail_text = QTextEdit()
        self.help_detail_text.setReadOnly(True)
        self.help_detail_text.setFont(FONTS["body"])
        
        splitter.addWidget(self.help_topics_list)
        splitter.addWidget(self.help_detail_text)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        layout.addWidget(splitter, 1)

        self.help_data = {
            "🚀 Introduzione": "BENVENUTO IN INTELLEO PDF SPLITTER\n\nIntelleo è uno strumento professionale per l'automazione documentale.\nPermette di dividere massicci volumi di scansioni PDF in singoli documenti, classificandoli automaticamente.\n\n✨ FUNZIONALITÀ CHIAVE\n1. Smart Splitting: Riconoscimento intelligente delle pagine tramite parole chiave.\n2. Supporto ROI: Aree di interesse specifiche per aumentare la precisione.\n3. Analisi Ibrida: Combina estrazione testo nativa con OCR Tesseract.\n4. Revisione Manuale: Interfaccia dedicata per gestire i file non riconosciuti.",
            "⚙️ Configurazione Iniziale": "PRIMA CONFIGURAZIONE\n\n1. Installazione Tesseract OCR\n   Tab 'Configurazione' -> Seleziona il percorso di tesseract.exe.\n   Usa 'Auto-Rileva' per trovarlo automaticamente.\n\n2. Creazione Regole\n   Tab 'Configurazione' -> 'Regole di Classificazione' -> 'Aggiungi'.\n   Imposta Nome Categoria e Parole Chiave.",
            "🎯 Utility ROI": "UTILITY ROI (Region of Interest)\n\nSe la ricerca generica non basta, usa le ROI.\n\n1. Apri l'utility dal pulsante 'Utility ROI'.\n2. Carica un PDF di esempio.\n3. Disegna un rettangolo sull'area di interesse.\n4. Assegna la ROI alla categoria.",
            "📂 Elaborazione": "ELABORAZIONE DOCUMENTI\n\n1. Vai alla scheda Elaborazione.\n2. Trascina i file PDF nell'area tratteggiata.\n3. Verifica il codice ODC.\n4. La barra di progresso mostrerà l'avanzamento.",
            "📝 Revisione Manuale": "REVISIONE FILE SCONOSCIUTI\n\nSe pagine non corrispondono a nessuna regola:\n- Lista a Sinistra: Seleziona le pagine.\n- Anteprima a Destra: Controlla il contenuto.\n- RINOMINA: Crea il file PDF finale.\n- SALTA: Passa al prossimo gruppo.",
        }
        
        for topic in self.help_data:
            self.help_topics_list.addItem(topic)
            
        self.help_topics_list.currentItemChanged.connect(self._on_help_topic_select)
        self.help_topics_list.setCurrentRow(0)

    def _on_help_topic_select(self, current: QListWidget, previous: Any = None) -> None:
        """Gestisce il cambio di topic nella guida."""
        if current:
            self.help_detail_text.setPlainText(self.help_data.get(current.text(), ""))
