"""
Modulo per la Tab Guida (SRP).
"""

import os
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QListWidget, QSplitter, QTextEdit, QVBoxLayout, QWidget

from gui.theme import COLORS, FONTS
from gui.ui_factory import AnimatedButton
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
        from shared.constants import APP_DATA_DIR
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)

        header = QHBoxLayout()
        header.addStretch()

        btn_open = AnimatedButton("APRI CARTELLA DATI")
        btn_open.clicked.connect(lambda: os.startfile(APP_DATA_DIR))
        header.addWidget(btn_open)
        layout.addLayout(header)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet(f"QSplitter::handle {{ background-color: {COLORS['border']}; }}")

        self.help_topics_list = QListWidget()
        self.help_topics_list.setStyleSheet(
            f"QListWidget {{ border: none; background-color: {COLORS['bg_secondary']}; border-radius: 8px; padding: 10px; }}"
        )

        self.help_detail_text = QTextEdit()
        self.help_detail_text.setReadOnly(True)
        self.help_detail_text.setFont(FONTS["body"])
        self.help_detail_text.setStyleSheet(
            f"QTextEdit {{ border: none; background-color: {COLORS['bg_secondary']}; border-radius: 8px; padding: 15px; }}"
        )

        splitter.addWidget(self.help_topics_list)
        splitter.addWidget(self.help_detail_text)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        layout.addWidget(splitter, 1)

        self.help_data = {
            "🚀 Benvenuto": (
                "BENVENUTO IN INTELLEO PDF SPLITTER\n\n"
                "Intelleo è uno strumento professionale per l'automazione documentale, "
                "progettato per dividere massicci volumi di scansioni PDF in documenti singoli, "
                "classificandoli automaticamente tramite OCR e intelligenza artificiale.\n\n"
                "✨ FLUSSO UNIFICATO\n"
                "L'applicazione è stata ottimizzata per operare interamente dalla Dashboard principale, "
                "riducendo al minimo i cambi di schermata e massimizzando la produttività."
            ),
            "📂 Caricamento e Avvio": (
                "COME AVVIARE UN'ANALISI\n\n"
                "Ci sono tre modi rapidi per iniziare il lavoro:\n\n"
                "1. PULSANTE AVVIA ANALISI: Clicca sul tasto blu principale. Il sistema ti chiederà "
                "se desideri selezionare singoli 'File PDF' o scansionare un'intera 'Cartella'.\n\n"
                "2. DRAG & DROP: Trascina i file PDF direttamente nell'area 'DROP' in fondo alla Dashboard. "
                "L'analisi partirà immediatamente con i parametri correnti.\n\n"
                "3. COMANDI CLI: Puoi trascinare un file sopra l'icona dell'applicazione per lanciarla "
                "direttamente su quel documento."
            ),
            "⚙️ Configurazione e ODC": (
                "GESTIONE PARAMETRI\n\n"
                "• CODICE ODC: Inserisci il codice commessa nel campo dedicato all'interno del gruppo "
                "'CONFIGURAZIONE' nella Dashboard. Verrà usato come prefisso per ogni file generato.\n\n"
                "• TESSERACT OCR: Assicurati che il percorso dell'eseguibile sia corretto nella "
                "tab 'Configurazione'. Usa 'Auto-Rileva' per una configurazione istantanea.\n\n"
                "• REGOLE: Gestisci le parole chiave e i criteri di classificazione premendo il tasto 'REGOLE'."
            ),
            "🎯 Utility ROI": (
                "AREE DI INTERESSE (ROI)\n\n"
                "Se i documenti hanno una struttura fissa ma testi difficili da rilevare globalmente, "
                "usa l'utility ROI:\n\n"
                "1. Apri 'UTILITY ROI' dalla Dashboard.\n"
                "2. Carica un PDF e disegna un'area specifica dove il software deve cercare il testo.\n"
                "3. Assegna l'area a una categoria e salva.\n\n"
                "Questo aumenta drasticamente la precisione e la velocità di analisi."
            ),
            "📝 Sessioni e Revisione": (
                "SICUREZZA E CONTROLLO\n\n"
                "• RECUPERA SESSIONE: Se l'app si chiude accidentalmente durante un lavoro, al riavvio "
                "potrai riprendere esattamente da dove avevi interrotto.\n\n"
                "• REVISIONE MANUALE: Le pagine non riconosciute automaticamente vengono isolate. "
                "Al termine del processo si aprirà un'interfaccia dedicata per rinominarle o scartarle manualmentee."
            ),
        }

        for topic in self.help_data:
            self.help_topics_list.addItem(topic)

        self.help_topics_list.currentItemChanged.connect(self._on_help_topic_select)
        self.help_topics_list.setCurrentRow(0)

    def _on_help_topic_select(self, current: Any, previous: Any = None) -> None:
        """Gestisce il cambio di topic nella guida."""
        if current and hasattr(current, "text"):
            self.help_detail_text.setPlainText(self.help_data.get(current.text(), ""))
