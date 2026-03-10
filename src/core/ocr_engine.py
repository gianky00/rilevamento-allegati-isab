"""
Motore OCR e Utility di Imaging (SRP).
Gestisce l'interazione con Tesseract e il pre-processing delle immagini.
Ottimizzato per massime prestazioni con early-exit e riduzione chiamate OCR.
"""

import os

import pytesseract
from PIL import Image, ImageOps


class OcrEngine:
    """Gestisce le operazioni di OCR e trasformazione immagini."""

    # Configurazione OCR ottimizzata per keyword matching
    _DEFAULT_TIMEOUT = 8  # Ridotto da 15s: keyword matching non richiede scan lunghi
    _DEFAULT_CONFIG = "--psm 6"  # Page segmentation mode 6: uniform block of text

    def __init__(self, tesseract_path: str | None = None) -> None:
        """Inizializza il motore OCR e imposta il percorso dell'eseguibile Tesseract."""
        self._tesseract_path = tesseract_path or ""
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path

        # Ottimizzazione: limita il numero di thread interni di Tesseract (OpenMP)
        # Quando eseguiamo analisi in parallelo a livello di pagina,
        # Tesseract non deve cercare di usare tutti i core per ogni singola chiamata OCR.
        os.environ["OMP_THREAD_LIMIT"] = "1"

    @staticmethod
    def get_binary(img: Image.Image) -> Image.Image:
        """Restituisce la versione binarizzata di un'immagine (converte in L se necessario)."""
        if img.mode != "L":
            img = img.convert("L")
        return img.point(lambda x: 0 if x < 128 else 255, "1")

    @staticmethod
    def get_contrast(img: Image.Image) -> Image.Image:
        """Applica l'autocontrasto all'immagine."""
        try:
            return ImageOps.autocontrast(img)
        except Exception:
            return img

    def scan_image(self, img: Image.Image, lang: str = "ita", config: str = "") -> str:
        """Esegue l'OCR su una singola immagine."""
        try:
            result = pytesseract.image_to_string(
                img,
                lang=lang,
                config=config or self._DEFAULT_CONFIG,
                timeout=self._DEFAULT_TIMEOUT,
            )
            return str(result).lower()
        except Exception:
            return ""

    def robust_scan(self, base_img: Image.Image, keywords: list[str]) -> tuple[bool, str]:
        """
        Esegue una scansione robusta tentando diverse trasformazioni e rotazioni.
        Ottimizzato: 5 step massimi con early-exit (eliminati duplicati dello Stadio 2).
        Lo Stadio 2 dell'analysis_service ha già fatto la scan Standard a 0°,
        quindi qui iniziamo direttamente con le varianti.
        Restituisce (found, matched_keyword).
        """
        keywords_lower = [k.lower() for k in keywords]

        # Step ottimizzati: nessun duplicato con lo Stadio 2 (Standard 0° già fatto)
        steps: list[tuple[str, Image.Image, list[int]]] = [
            ("Standard-90", base_img, [-90]),
            ("Binary", self.get_binary(base_img), [0, -90]),
            ("Contrast", self.get_contrast(base_img), [0]),
            ("DeepRotate", self.get_binary(base_img), [90, 180]),
        ]

        for _name, current_img, angles in steps:
            for angle in angles:
                img_to_scan = current_img if angle == 0 else current_img.rotate(angle, expand=True)
                text = self.scan_image(img_to_scan)
                for keyword in keywords_lower:
                    if keyword in text:
                        return True, keyword
        return False, ""
