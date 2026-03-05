"""
Motore OCR e Utility di Imaging (SRP).
Gestisce l'interazione con Tesseract e il pre-processing delle immagini.
"""
import os
import pytesseract
from PIL import Image, ImageOps
from typing import List, Optional, Dict, Any, Tuple

class OcrEngine:
    """Gestisce le operazioni di OCR e trasformazione immagini."""

    def __init__(self, tesseract_path: Optional[str] = None) -> None:
        """Inizializza il motore OCR e imposta il percorso dell'eseguibile Tesseract."""
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path

    @staticmethod
    def get_binary(img: Image.Image) -> Image.Image:
        """Restituisce la versione binarizzata di un'immagine."""
        return img.point(lambda x: 0 if x < 128 else 255, "1")

    @staticmethod
    def get_contrast(img: Image.Image) -> Image.Image:
        """Applica l'autocontrasto all'immagine."""
        try:
            return ImageOps.autocontrast(img)
        except Exception:
            return img

    def scan_image(self, img: Image.Image, lang: str = "ita", config: str = "--psm 6") -> str:
        """Esegue l'OCR su una singola immagine."""
        try:
            result = pytesseract.image_to_string(img, lang=lang, config=config, timeout=15)
            return str(result).lower()
        except Exception:
            return ""

    def robust_scan(self, base_img: Image.Image, keywords: List[str]) -> Tuple[bool, str]:
        """
        Esegue una scansione robusta tentando diverse trasformazioni e rotazioni.
        Restituisce (found, matched_keyword).
        """
        steps: List[Dict[str, Any]] = [
            {"name": "Standard", "img": base_img, "angles": [0, -90]},
            {"name": "Binary", "img": self.get_binary(base_img), "angles": [0, -90]},
            {"name": "DeepRotate", "img": self.get_binary(base_img), "angles": [90, 180]},
            {"name": "Contrast", "img": self.get_contrast(base_img), "angles": [0, -90]},
        ]

        for step in steps:
            current_img: Image.Image = step["img"]
            angles: List[int] = step["angles"]
            for angle in angles:
                img_to_scan = current_img if angle == 0 else current_img.rotate(angle, expand=True)
                text = self.scan_image(img_to_scan)
                for keyword in keywords:
                    if keyword in text:
                        return True, keyword
        return False, ""
