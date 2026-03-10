"""
Modulo per la Tab Dashboard (SRP).
Gestisce la visualizzazione principale, le statistiche e l'area di elaborazione.
"""

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from gui.theme import COLORS, FONTS
from gui.ui_factory import AnimatedButton
from gui.widgets.drop_frame import DropFrame


class DashboardTab(QWidget):
    """Gestisce la costruzione e i widget della tab Dashboard unificata."""

    def __init__(self, parent: QWidget, main_app: Any) -> None:
        """
        Inizializza la tab dashboard collegandola all'applicazione principale.

        Args:
            parent (QWidget): Widget genitore.
            main_app (Any): Riferimento all'istanza dell'applicazione principale.
        """
        super().__init__(parent)
        self.main_app = main_app
        self._init_ui()

    def _init_ui(self) -> None:
        """Configura l'interfaccia utente unificata (Dashboard + Elaborazione)."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 5)
        layout.setSpacing(10)

        # 1. Header Row (STRUTTURA TRIPARTITA)
        header = QHBoxLayout()
        header.setSpacing(10)

        # --- SINISTRA: DOC e PAG ---
        left_stats = QHBoxLayout()
        left_stats.setSpacing(15)

        def create_header_stat(label_text: str):
            """Crea un micro-layout per le statistiche nell'header."""
            container = QHBoxLayout()
            container.setSpacing(5)
            lbl = QLabel(label_text + ":")
            lbl.setFont(FONTS["small_bold"])
            lbl.setStyleSheet(f"color: {COLORS['text_secondary']};")

            val_sess = QLabel("0")
            val_sess.setFont(FONTS["mono_bold"])
            val_sess.setStyleSheet(f"color: {COLORS['accent']};")

            sep = QLabel("/")
            sep.setStyleSheet(f"color: {COLORS['text_muted']};")

            val_tot = QLabel("0")
            val_tot.setFont(FONTS["mono_bold"])
            val_tot.setStyleSheet(f"color: {COLORS['text_primary']};")

            container.addWidget(lbl)
            container.addWidget(val_sess)
            container.addWidget(sep)
            container.addWidget(val_tot)
            return container, val_sess, val_tot

        cont_doc, self.main_app.files_count_sess_label, self.main_app.files_count_tot_label = create_header_stat("DOC")
        left_stats.addLayout(cont_doc)

        cont_pag, self.main_app.pages_count_sess_label, self.main_app.pages_count_tot_label = create_header_stat("PAG")
        left_stats.addLayout(cont_pag)

        header.addLayout(left_stats)
        header.addStretch(1)  # Primo stretch per centrare REGOLE

        # --- CENTRO: REGOLE ---
        regole_container = QHBoxLayout()
        regole_container.setSpacing(5)
        lbl_reg = QLabel("REGOLE:")
        lbl_reg.setFont(FONTS["small_bold"])
        lbl_reg.setStyleSheet(f"color: {COLORS['text_secondary']};")

        self.main_app.rules_count_label = QLabel("0")
        self.main_app.rules_count_label.setFont(FONTS["mono_bold"])
        self.main_app.rules_count_label.setStyleSheet(
            f"color: {COLORS['success']}; padding: 2px 8px; background-color: {COLORS['bg_secondary']}; border-radius: 4px;"
        )

        regole_container.addWidget(lbl_reg)
        regole_container.addWidget(self.main_app.rules_count_label)
        header.addLayout(regole_container)

        header.addStretch(1)  # Secondo stretch per centrare REGOLE

        # --- DESTRA: SPINNER, BELL, CLOCK ---
        right_info = QHBoxLayout()
        right_info.setSpacing(10)

        self.main_app.spinner_label = QLabel("")
        self.main_app.spinner_label.setFont(QFont("Consolas", 14, QFont.Weight.Bold))
        right_info.addWidget(self.main_app.spinner_label)

        if self.main_app.notifier:
            self.main_app.notifier.setup_bell_icon(right_info)

        self.clock_label = QLabel("")
        self.clock_label.setFont(FONTS["mono_bold"])
        self.clock_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        right_info.addWidget(self.clock_label)

        header.addLayout(right_info)
        layout.addLayout(header)

        # --- DROP ZONE ---
        self.main_app.drop_frame = DropFrame(self.main_app._on_drop)
        self.main_app.drop_frame.setMinimumHeight(70)
        self.main_app.drop_frame.setText("Trascina qui i PDF per iniziare")
        layout.addWidget(self.main_app.drop_frame)

        # 2. Sezione Comandi (Row ultra-compatta allineata a sinistra)
        middle_row = QHBoxLayout()
        middle_row.setSpacing(10)
        middle_row.setAlignment(Qt.AlignmentFlag.AlignLeft)

        # GRUPPO AZIONI (Pulsanti compatti)
        actions_group = QGroupBox(" AZIONI ")
        actions_group.setStyleSheet(
            f"QGroupBox {{ font-weight: bold; border: 1px solid {COLORS['border']}; background-color: {COLORS['bg_secondary']}; border-radius: 8px; color: {COLORS['text_primary']}; }}",
        )
        act_layout = QHBoxLayout(actions_group)
        act_layout.setContentsMargins(10, 18, 10, 8)
        act_layout.setSpacing(8)

        def setup_btn(btn):
            """Configura la policy di dimensione e aggiunge il bottone al layout."""
            btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
            act_layout.addWidget(btn)

        self.main_app.dashboard_start_btn = AnimatedButton("AVVIA", is_primary=True)
        self.main_app.dashboard_start_btn.clicked.connect(self.main_app._quick_select_pdf)
        setup_btn(self.main_app.dashboard_start_btn)

        btn_rules = AnimatedButton("REGOLE")
        btn_rules.clicked.connect(lambda: self.main_app.notebook.setCurrentWidget(self.main_app.config_tab))
        setup_btn(btn_rules)

        btn_roi = AnimatedButton("ROI")
        btn_roi.clicked.connect(self.main_app._launch_roi_utility)
        setup_btn(btn_roi)

        self.main_app.restore_btn = AnimatedButton("RECUPERA")
        self.main_app.restore_btn.setEnabled(False)
        self.main_app.restore_btn.clicked.connect(self.main_app._restore_session)
        setup_btn(self.main_app.restore_btn)

        act_layout.addStretch()
        middle_row.addWidget(actions_group)

        # GRUPPO CONFIG (ODC SOPRA LA CASELLA + SFOGLIA)
        config_group = QGroupBox(" CONFIGURAZIONE ")
        config_group.setStyleSheet(
            f"QGroupBox {{ font-weight: bold; border: 1px solid {COLORS['border']}; background-color: {COLORS['bg_secondary']}; border-radius: 8px; color: {COLORS['text_primary']}; }}",
        )
        conf_layout = QHBoxLayout(config_group)
        conf_layout.setContentsMargins(10, 18, 10, 8)
        conf_layout.setSpacing(10)

        odc_container = QVBoxLayout()
        odc_container.setSpacing(2)

        odc_label = QLabel("ODC")
        odc_label.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        odc_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        odc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        odc_container.addWidget(odc_label)

        self.main_app.odc_entry = QLineEdit("")
        self.main_app.odc_entry.setFixedWidth(150)
        self.main_app.odc_entry.setPlaceholderText("Inserisci ODC...")
        self.main_app.odc_entry.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_app.odc_entry.setStyleSheet(
            f"background-color: {COLORS['bg_primary']}; border: 1px solid {COLORS['border']}; border-radius: 4px; padding: 4px;"
        )
        odc_container.addWidget(self.main_app.odc_entry)
        conf_layout.addLayout(odc_container)

        btn_sfoglia = AnimatedButton("SFOGLIA")
        btn_sfoglia.clicked.connect(self.main_app._select_pdf)
        conf_layout.addWidget(btn_sfoglia)

        middle_row.addWidget(config_group)
        middle_row.addStretch(1)

        layout.addLayout(middle_row)

        # 3. Sezione Elaborazione
        self.main_app.proc_group = QGroupBox(" ELABORAZIONE IN CORSO ")
        self.main_app.proc_group.setMinimumHeight(110)
        self.main_app.proc_group.setStyleSheet(
            f"QGroupBox {{ font-weight: bold; border: 2px solid {COLORS['accent']}; background-color: {COLORS['bg_primary']}; border-radius: 8px; color: {COLORS['accent']}; }}"
        )
        self.main_app.proc_group.setVisible(False)
        playout = QVBoxLayout(self.main_app.proc_group)
        playout.setContentsMargins(12, 22, 12, 10)
        playout.setSpacing(5)

        info_row = QHBoxLayout()
        self.main_app.pdf_path_label = QLabel("Nessun file")
        self.main_app.pdf_path_label.setFont(FONTS["small_bold"])
        info_row.addWidget(self.main_app.pdf_path_label)

        self.main_app.progress_label = QLabel("Pronto")
        self.main_app.progress_label.setFont(FONTS["body_bold"])
        info_row.addWidget(self.main_app.progress_label, 0, Qt.AlignmentFlag.AlignCenter)

        self.main_app.eta_label = QLabel("")
        self.main_app.eta_label.setFont(FONTS["mono_bold"])
        self.main_app.eta_label.setStyleSheet(f"color: {COLORS['danger']};")
        info_row.addWidget(self.main_app.eta_label, 0, Qt.AlignmentFlag.AlignRight)
        playout.addLayout(info_row)

        self.main_app.progress_bar = QProgressBar()
        self.main_app.progress_bar.setMaximum(1000)
        self.main_app.progress_bar.setFixedHeight(18)
        playout.addWidget(self.main_app.progress_bar)

        self.main_app.stop_btn = QPushButton("STOP")
        self.main_app.stop_btn.setStyleSheet(
            f"background-color: {COLORS['danger']}; color: white; font-weight: bold; border-radius: 4px;"
        )
        self.main_app.stop_btn.setVisible(False)
        self.main_app.stop_btn.clicked.connect(self.main_app._stop_processing)
        playout.addWidget(self.main_app.stop_btn)
        layout.addWidget(self.main_app.proc_group)

        # 4. Terminale
        log_group = QGroupBox(" ATTIVITÀ ")
        log_group.setStyleSheet(
            f"QGroupBox {{ font-weight: bold; border: 1px solid {COLORS['border']}; background-color: {COLORS['bg_secondary']}; border-radius: 8px; color: {COLORS['text_primary']}; }}"
        )
        log_layout = QVBoxLayout(log_group)
        log_layout.setContentsMargins(8, 18, 8, 8)
        self.main_app.log_area = QTextEdit()
        self.main_app.log_area.setReadOnly(True)
        self.main_app.log_area.setFont(FONTS["mono"])
        self.main_app.log_area.setStyleSheet("border: none; background: transparent;")
        log_layout.addWidget(self.main_app.log_area)
        self.main_app.recent_log = self.main_app.log_area
        layout.addWidget(log_group, 1)

        # 5. FOOTER LICENZA
        footer = QFrame()
        footer.setStyleSheet(f"background-color: {COLORS['bg_tertiary']}; border-top: 1px solid {COLORS['border']};")
        footer.setFixedHeight(30)
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(15, 0, 15, 0)
        footer_layout.setSpacing(20)

        self.main_app.license_status_label = QLabel("SISTEMA ATTIVO")
        self.main_app.license_status_label.setFont(FONTS["small_bold"])
        footer_layout.addWidget(self.main_app.license_status_label)

        def add_sep():
            """Aggiunge un divisore verticale nel footer."""
            line = QFrame()
            line.setFrameShape(QFrame.Shape.VLine)
            line.setStyleSheet(f"background-color: {COLORS['text_muted']}; max-height: 15px;")
            footer_layout.addWidget(line)

        add_sep()

        self.main_app.license_fields = {}
        info_items = [
            ("UTENTE", "cliente"),
            ("SCADENZA", "scadenza"),
            ("HWID", "hwid"),
            ("ACCESSO", "last_access"),
        ]

        for label, key in info_items:
            item_layout = QHBoxLayout()
            item_layout.setSpacing(5)
            l_lbl = QLabel(label + ":")
            l_lbl.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            l_lbl.setStyleSheet(f"color: {COLORS['text_secondary']};")
            v_lbl = QLabel("---")
            v_lbl.setFont(QFont("Consolas", 8))
            v_lbl.setStyleSheet(f"color: {COLORS['text_primary']};")
            item_layout.addWidget(l_lbl)
            item_layout.addWidget(v_lbl)
            self.main_app.license_fields[key] = v_lbl
            footer_layout.addLayout(item_layout)
            if label != "ACCESSO":
                footer_layout.addSpacing(10)

        footer_layout.addStretch()

        import version

        v_lbl = QLabel(f"v{version.__version__}")
        v_lbl.setFont(FONTS["small_bold"])
        v_lbl.setStyleSheet(f"color: {COLORS['text_muted']}")
        footer_layout.addWidget(v_lbl)

        layout.addWidget(footer)
