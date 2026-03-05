"""
Controller per l'utility ROI (SRP/SoC).
Gestisce la logica di navigazione PDF, zoom e coordinamento RoiManager/PdfManager.
"""
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QImage, QPixmap

from core.roi_manager import RoiManager
from core.pdf_manager import PdfManager

logger = logging.getLogger("ROI_CONTROLLER")
SIGNAL_FILE = ".update_signal"

class ROIController(QObject):
    """
    Controller che separa la logica di gestione ROI dalla View (ROIDrawingApp).
    """
    
    # Segnali per la View
    page_rendered = Signal(object, int, int)  # QPixmap, current_page, total_pages
    rules_updated = Signal()
    status_message = Signal(str, str)  # message, level
    zoom_changed = Signal(float)
    roi_data_ready = Signal(list) # categories

    def __init__(self) -> None:
        """Inizializza il controller e i gestori per le ROI e i PDF."""
        super().__init__()
        self.roi_manager = RoiManager()
        self.pdf_manager = PdfManager()
        
        self.current_page_index = 0
        self.zoom_level = 1.0
        self.delete_mode = False

    def load_config(self) -> None:
        """Carica la configurazione iniziale."""
        self.roi_manager.load_config()
        self.rules_updated.emit()

    def open_pdf(self, filepath: str) -> None:
        """Apre un file PDF e resetta lo stato."""
        if not filepath:
            return

        success, msg = self.pdf_manager.open(filepath)
        if success:
            if self.pdf_manager.get_page_count() > 0:
                self.current_page_index = 0
                self.zoom_level = 1.0
                self.render_current_page()
                self.status_message.emit(f"PDF caricato: {os.path.basename(filepath)}", "SUCCESS")
            else:
                self.status_message.emit("Il PDF non contiene pagine", "WARNING")
        else:
            self.status_message.emit(f"Errore apertura PDF: {msg}", "ERROR")

    def render_current_page(self) -> None:
        """Renderizza la pagina corrente basandosi sullo zoom."""
        if not self.pdf_manager.doc:
            return

        pix = self.pdf_manager.get_pixmap(self.current_page_index, self.zoom_level)
        if not pix:
            return

        # Conversione in QPixmap (Logica GUI minima necessaria nel controller per efficienza)
        qimage = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888)
        qpixmap = QPixmap.fromImage(qimage)
        
        self.page_rendered.emit(qpixmap, self.current_page_index, self.pdf_manager.get_page_count())
        self.zoom_changed.emit(self.zoom_level)

    def next_page(self) -> None:
        """Naviga alla pagina successiva del documento PDF."""
        if self.pdf_manager.doc and self.current_page_index < self.pdf_manager.get_page_count() - 1:
            self.current_page_index += 1
            self.render_current_page()

    def prev_page(self) -> None:
        """Naviga alla pagina precedente del documento PDF."""
        if self.current_page_index > 0:
            self.current_page_index -= 1
            self.render_current_page()

    def set_zoom(self, level: float) -> None:
        """Imposta il livello di zoom (limite tra 0.25 e 4.0) e aggiorna la vista."""
        self.zoom_level = max(0.25, min(4.0, level))
        self.render_current_page()

    def zoom_in(self) -> None:
        """Incrementa lo zoom del 20%."""
        self.set_zoom(self.zoom_level * 1.2)

    def zoom_out(self) -> None:
        """Decrementa lo zoom del 20%."""
        self.set_zoom(self.zoom_level / 1.2)

    def zoom_reset(self) -> None:
        """Ripristina lo zoom al 100%."""
        self.set_zoom(1.0)

    def add_roi(self, category: str, coords: List[int]) -> bool:
        """Aggiunge una ROI e salva."""
        if self.roi_manager.add_roi(category, coords):
            self.save_and_signal()
            return True
        return False

    def remove_roi(self, rule_index: int, roi_index: int) -> bool:
        """Rimuove una ROI e salva."""
        if self.roi_manager.remove_roi(rule_index, roi_index):
            self.save_and_signal()
            return True
        return False

    def save_and_signal(self) -> None:
        """Salva fisicamente e crea il segnale per l'app principale."""
        try:
            self.roi_manager.save_config()
            with open(SIGNAL_FILE, "w") as f:
                f.write("update")
            self.rules_updated.emit()
            self.render_current_page()
        except Exception as e:
            logger.error(f"Errore salvataggio ROI: {e}")
            self.status_message.emit(f"Errore salvataggio: {e}", "ERROR")

    def get_rules(self) -> List[Dict[str, Any]]:
        """Restituisce l'elenco delle regole di classificazione correnti."""
        return self.roi_manager.get_rules()

    def get_categories(self) -> List[str]:
        """Restituisce i nomi delle categorie disponibili."""
        return self.roi_manager.get_categories()
