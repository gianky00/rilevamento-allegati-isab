import pymupdf as fitz  # PyMuPDF
import pytesseract
from PIL import Image
import os

def process_pdf(pdf_path, odc, config, progress_callback=None):
    """
    Elabora un file PDF, classifica le pagine in base a regole OCR e salva i PDF divisi.

    Args:
        pdf_path (str): Il percorso del file PDF da elaborare.
        odc (str): Il numero ODC da utilizzare nel nome del file di output.
        config (dict): Il dizionario di configurazione contenente le impostazioni.
        progress_callback (function, optional): Una funzione da chiamare per riportare i progressi.

    Returns:
        tuple: Una tupla contenente un booleano di successo e un messaggio.
    """
    if progress_callback:
        progress_callback("Avvio dell'elaborazione del PDF...")

    try:
        # Imposta il percorso di Tesseract se specificato
        tesseract_path = config.get("tesseract_path")
        if tesseract_path and os.path.exists(tesseract_path):
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
        else:
            raise ValueError("Il percorso di Tesseract non è configurato o non è valido.")

        pdf_doc = fitz.open(pdf_path)

        page_groups = {}
        total_pages = len(pdf_doc)

        # Itera su ogni pagina del PDF
        for i, page in enumerate(pdf_doc):
            if progress_callback:
                progress_callback(f"Elaborazione pagina {i + 1}/{total_pages}...")

            # Renderizza la pagina come immagine ad alta risoluzione
            pix = page.get_pixmap(dpi=300)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            page_category = "sconosciuto"

            # Itera attraverso ogni regola di classificazione
            for rule in config.get("classification_rules", []):
                rois = rule.get("rois", [])
                keywords = [k.lower() for k in rule.get("keywords", [])]
                category_name = rule.get("category_name")

                # Cicla attraverso ogni ROI definita per la regola
                for roi in rois:
                    if not all(isinstance(c, int) and c >= 0 for c in roi) or len(roi) != 4:
                        continue

                    factor = 300 / 72
                    crop_box = [int(c * factor) for c in roi]

                    if crop_box[2] > img.width or crop_box[3] > img.height:
                        continue

                    cropped_img = img.crop(crop_box)

                    # Tenta l'OCR sull'immagine originale e poi ruotata
                    for angle in [0, -90]: # 0 = nessuna rotazione, -90 = 90 gradi orario
                        img_to_scan = cropped_img
                        if angle != 0:
                            img_to_scan = cropped_img.rotate(angle, expand=True)

                        try:
                            ocr_text = pytesseract.image_to_string(img_to_scan, lang='ita').lower()
                            if any(keyword in ocr_text for keyword in keywords):
                                page_category = category_name
                                break  # Keyword trovata, esce dal ciclo di rotazione
                        except Exception as ocr_error:
                            if progress_callback:
                                progress_callback(f"Avviso OCR per '{category_name}': {ocr_error}")

                    if page_category == category_name:
                        break  # Regola trovata, interrompe il ciclo delle ROI

                if page_category == category_name:
                    break  # Regola trovata, interrompe il ciclo delle regole

            # Aggiunge l'indice della pagina al gruppo corrispondente
            if page_category not in page_groups:
                page_groups[page_category] = []
            page_groups[page_category].append(i)

        if progress_callback:
            progress_callback("Raggruppamento e salvataggio dei PDF...")

        base_output_dir = os.path.dirname(pdf_path)
        odc_dir = os.path.join(base_output_dir, odc)
        os.makedirs(odc_dir, exist_ok=True)

        for category, pages in page_groups.items():
            if not pages:
                continue

            # Nome del file basato su ODC e categoria
            if category == "sconosciuto":
                output_filename = f"{odc}_.pdf"
            else:
                output_filename = f"{odc}_{category}.pdf"
            output_path = os.path.join(odc_dir, output_filename)

            new_pdf = fitz.open()
            for page_num in pages:
                new_pdf.insert_pdf(pdf_doc, from_page=page_num, to_page=page_num)

            new_pdf.save(output_path)
            new_pdf.close()

            # Log del percorso relativo
            relative_path = os.path.join(odc, output_filename)
            if progress_callback:
                progress_callback(f"Salvato: {relative_path}")

        pdf_doc.close()
        if progress_callback:
            progress_callback("Elaborazione completata.")

        return True, "Successo"

    except Exception as e:
        if progress_callback:
            progress_callback(f"Errore: {e}")
        return False, str(e)
