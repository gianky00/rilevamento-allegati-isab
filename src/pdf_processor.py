import pymupdf as fitz  # PyMuPDF
import pytesseract
from PIL import Image
import os

import re

def extract_odc_from_pdf(pdf_doc, config, progress_callback=None):
    """Estrae il valore ODC dalla prima pagina del PDF utilizzando una ROI definita."""
    odc_roi = config.get("odc_roi")
    if not odc_roi:
        if progress_callback:
            progress_callback("ROI per ODC non definita nella configurazione. Salto estrazione.")
        return "ODC_Sconosciuto"

    try:
        first_page = pdf_doc[0]
        pix = first_page.get_pixmap(dpi=300)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        factor = 300 / 72
        crop_box = [int(c * factor) for c in odc_roi]

        if crop_box[2] > img.width or crop_box[3] > img.height:
            if progress_callback:
                progress_callback("Attenzione: la ROI per ODC è fuori dai limiti della pagina.")
            return "ODC_Invalido"

        cropped_img = img.crop(crop_box)
        ocr_text = pytesseract.image_to_string(cropped_img, lang='ita').strip()

        # Pulizia dell'output OCR: rimuovi caratteri non numerici
        odc_value = re.sub(r'\D', '', ocr_text)

        if not odc_value:
            return "ODC_NonTrovato"

        return odc_value

    except Exception as e:
        if progress_callback:
            progress_callback(f"Errore durante l'estrazione dell'ODC: {e}")
        return "ODC_Errore"

def process_pdf(pdf_path, config, progress_callback=None):
    if progress_callback:
        progress_callback("Avvio dell'elaborazione del PDF...")

    try:
        tesseract_path = config.get("tesseract_path")
        if tesseract_path and os.path.exists(tesseract_path):
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
        else:
            raise ValueError("Il percorso di Tesseract non è configurato o non è valido.")

        pdf_doc = fitz.open(pdf_path)

        # Estrai ODC dalla prima pagina
        odc = extract_odc_from_pdf(pdf_doc, config, progress_callback)
        if progress_callback:
            progress_callback(f"ODC estratto: {odc}")

        page_groups = {"sconosciuto": []}
        total_pages = len(pdf_doc)

        for i, page in enumerate(pdf_doc):
            if progress_callback:
                progress_callback(f"Elaborazione pagina {i + 1}/{total_pages}...")

            pix = page.get_pixmap(dpi=300)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            page_category = "sconosciuto"

            for rule in config.get("classification_rules", []):
                # ... (resto della logica di classificazione invariata)
                rois = rule.get("rois", [])
                keywords = [k.lower() for k in rule.get("keywords", [])]
                category_name = rule.get("category_name")

                for roi in rois:
                    if not all(isinstance(c, int) and c >= 0 for c in roi) or len(roi) != 4:
                        continue
                    factor = 300 / 72
                    crop_box = [int(c * factor) for c in roi]
                    if crop_box[2] > img.width or crop_box[3] > img.height:
                        continue
                    cropped_img = img.crop(crop_box)
                    try:
                        ocr_text = pytesseract.image_to_string(cropped_img, lang='ita').lower()
                        for keyword in keywords:
                            if keyword in ocr_text:
                                page_category = category_name
                                break
                        if page_category == category_name:
                            break
                    except Exception:
                        pass # Ignora errori OCR per singole ROI
                if page_category == category_name:
                    break

            if page_category not in page_groups:
                page_groups[page_category] = []
            page_groups[page_category].append(i)

        if progress_callback:
            progress_callback("Salvataggio dei PDF divisi...")

        base_output_dir = os.path.dirname(pdf_path)
        odc_output_dir = os.path.join(base_output_dir, odc)
        unclassified_dir = os.path.join(odc_output_dir, "non rilevati")
        os.makedirs(unclassified_dir, exist_ok=True)

        output_template = config.get("output_template", "{category}.pdf") # Rimuoviamo ODC dal template

        for category, pages in page_groups.items():
            if not pages:
                continue

            # Scegli la cartella di output
            current_output_dir = unclassified_dir if category == "sconosciuto" else odc_output_dir
            output_filename = output_template.format(category=category)
            output_path = os.path.join(current_output_dir, output_filename)

            new_pdf = fitz.open()
            for page_num in pages:
                new_pdf.insert_pdf(pdf_doc, from_page=page_num, to_page=page_num)

            new_pdf.save(output_path)
            new_pdf.close()

            if progress_callback:
                progress_callback(f"Salvato: {os.path.join(os.path.basename(current_output_dir), output_filename)}")

        pdf_doc.close()
        if progress_callback:
            progress_callback("Elaborazione completata.")

        return True, "Successo"

    except Exception as e:
        if progress_callback:
            progress_callback(f"Errore: {e}")
        return False, str(e)
