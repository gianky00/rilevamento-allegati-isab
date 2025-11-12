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
                roi = rule.get("roi")
                keywords = [k.lower() for k in rule.get("keywords", [])]
                category_name = rule.get("category_name")

                # Salta la regola se la ROI non è valida
                if not all(isinstance(c, int) and c >= 0 for c in roi) or len(roi) != 4:
                    if progress_callback:
                        progress_callback(f"Salto la regola '{category_name}' a causa di una ROI non valida.")
                    continue

                # Converte le coordinate della ROI da punti PDF a coordinate pixel
                factor = 300 / 72
                crop_box = [int(c * factor) for c in roi]

                # Controlla se il riquadro di ritaglio è valido
                if crop_box[2] > img.width or crop_box[3] > img.height:
                    if progress_callback:
                        progress_callback(f"Attenzione: la ROI per '{category_name}' è fuori dai limiti della pagina.")
                    continue

                cropped_img = img.crop(crop_box)

                # Esegue l'OCR sull'immagine ritagliata
                try:
                    ocr_text = pytesseract.image_to_string(cropped_img, lang='ita').lower()
                    for keyword in keywords:
                        if keyword in ocr_text:
                            page_category = category_name
                            break  # Keyword trovata, interrompe il controllo delle keyword per questa regola
                    if page_category == category_name:
                        break  # Regola trovata, interrompe il controllo delle altre regole per questa pagina
                except pytesseract.TesseractNotFoundError:
                     raise ValueError("Eseguibile di Tesseract non trovato. Controlla il percorso nella configurazione.")
                except Exception as ocr_error:
                    if progress_callback:
                        progress_callback(f"OCR fallito per la regola '{category_name}' sulla pagina {i+1}: {ocr_error}")

            # Aggiunge l'indice della pagina al gruppo corrispondente
            if page_category not in page_groups:
                page_groups[page_category] = []
            page_groups[page_category].append(i)

        if progress_callback:
            progress_callback("Raggruppamento e salvataggio dei PDF...")

        output_dir = os.path.dirname(pdf_path)
        output_template = config.get("output_template", "{ODC}_{category}.pdf")

        # Salva i PDF divisi per ogni categoria
        for category, pages in page_groups.items():
            if category == "sconosciuto" or not pages:
                continue

            output_filename = output_template.format(ODC=odc, category=category)
            output_path = os.path.join(output_dir, output_filename)

            new_pdf = fitz.open()
            for page_num in pages:
                new_pdf.insert_pdf(pdf_doc, from_page=page_num, to_page=page_num)

            new_pdf.save(output_path)
            new_pdf.close()

            if progress_callback:
                progress_callback(f"Salvato: {output_filename}")

        pdf_doc.close()
        if progress_callback:
            progress_callback("Elaborazione completata.")

        return True, "Successo"

    except Exception as e:
        if progress_callback:
            progress_callback(f"Errore: {e}")
        return False, str(e)
