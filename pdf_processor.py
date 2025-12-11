import pymupdf as fitz  # PyMuPDF
import pytesseract
from PIL import Image
import os
import shutil
import time

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
        if tesseract_path and os.path.isfile(tesseract_path):
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
        else:
            raise ValueError("Il percorso di Tesseract non è configurato o non è un file valido.")

        pdf_doc = fitz.open(pdf_path)

        page_groups = {}
        total_pages = len(pdf_doc)

        # Itera su ogni pagina del PDF
        for i, page in enumerate(pdf_doc):
            if progress_callback:
                progress_callback(f"Elaborazione pagina {i + 1}/{total_pages}...")

            page_category = "sconosciuto"
            page_rect = page.rect

            # Itera attraverso ogni regola di classificazione
            for rule in config.get("classification_rules", []):
                rois = rule.get("rois", [])
                keywords = [k.lower() for k in rule.get("keywords", [])]
                category_name = rule.get("category_name")

                # Cicla attraverso ogni ROI definita per la regola
                for roi in rois:
                    if not all(isinstance(c, int) and c >= 0 for c in roi) or len(roi) != 4:
                        continue

                    # Crea un rettangolo per la ROI (coordinate PDF originali)
                    roi_rect = fitz.Rect(roi)

                    # Verifica che la ROI sia all'interno della pagina
                    if roi_rect.x1 > page_rect.width or roi_rect.y1 > page_rect.height:
                        continue

                    # Renderizza SOLO l'area definita dalla ROI
                    # Matrix(300/72, 300/72) scala da 72 DPI (default PDF) a 300 DPI
                    mat = fitz.Matrix(300/72, 300/72)
                    try:
                        # Optimization: Use grayscale (csGRAY) directly from MuPDF to reduce memory and processing
                        pix = page.get_pixmap(matrix=mat, clip=roi_rect, colorspace=fitz.csGRAY)

                        # Verifica validità pixmap
                        if pix.width < 1 or pix.height < 1:
                            continue

                        cropped_img = Image.frombytes("L", [pix.width, pix.height], pix.samples)
                    except Exception as e:
                        if progress_callback:
                            progress_callback(f"Errore rendering ROI per '{category_name}': {e}")
                        continue

                    # Tenta l'OCR sull'immagine originale e poi ruotata
                    for angle in [0, -90]: # 0 = nessuna rotazione, -90 = 90 gradi orario
                        img_to_scan = cropped_img
                        if angle != 0:
                            img_to_scan = cropped_img.rotate(angle, expand=True)

                        try:
                            ocr_text = pytesseract.image_to_string(img_to_scan, lang='ita').lower()
                            # print(f"DEBUG OCR (angle={angle}): '{ocr_text}'")
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
        # REMOVED: odc_dir creation
        # odc_dir = os.path.join(base_output_dir, odc)
        # os.makedirs(odc_dir, exist_ok=True)

        for category, pages in page_groups.items():
            if not pages:
                continue

            # Determina il suffisso del file
            suffix = category # Default
            if category != "sconosciuto":
                for rule in config.get("classification_rules", []):
                    if rule["category_name"] == category:
                        suffix = rule.get("filename_suffix", category)
                        if not suffix: # Handle empty string case if present
                            suffix = category
                        break

            # Sconosciuto logic handling (if needed specific override, or just empty string?)
            # Prompt said: "quando trovi la categoria "consuntivo" devi rinominare il pdf con "cons" finale"
            # And: "2. Unknown Category: Currently, unrecognized pages are saved as {ODC}_.pdf. How should these be named? -> cosi come attualmente"
            # Currently it is `{ODC}_.pdf` for unknown.
            if category == "sconosciuto":
                output_filename = f"{odc}_.pdf"
            else:
                output_filename = f"{odc}_{suffix}.pdf"

            output_path = os.path.join(base_output_dir, output_filename)

            new_pdf = fitz.open()
            for page_num in pages:
                new_pdf.insert_pdf(pdf_doc, from_page=page_num, to_page=page_num)

            new_pdf.save(output_path)
            new_pdf.close()

            # Log del percorso (ora relativo alla cartella base)
            if progress_callback:
                progress_callback(f"Salvato: {output_filename}")

        pdf_doc.close()

        # Sposta il file originale nella cartella ORIGINALI
        if progress_callback:
            progress_callback("Spostamento file originale...")

        originali_dir = os.path.join(base_output_dir, "ORIGINALI")
        os.makedirs(originali_dir, exist_ok=True)

        destination_path = os.path.join(originali_dir, os.path.basename(pdf_path))

        # Gestione sovrascrittura se necessario (shutil.move sovrascrive su POSIX ma su Windows dipende)
        # Per sicurezza, se esiste lo cancelliamo prima? O lasciamo che fallisca?
        # User said "devono essere spostati". Usually implies simple move.
        if os.path.exists(destination_path):
            try:
                os.remove(destination_path)
            except OSError as e:
                if progress_callback:
                    progress_callback(f"Avviso: Impossibile rimuovere il file esistente in ORIGINALI: {e}")

        # Retry loop for file move (robustness against file locks)
        moved = False
        for attempt in range(3):
            try:
                shutil.move(pdf_path, destination_path)
                moved = True
                break
            except PermissionError:
                if progress_callback:
                    progress_callback(f"Tentativo spostamento {attempt+1}/3 fallito (file bloccato). Riprovo...")
                time.sleep(1.0)
            except Exception as e:
                if progress_callback:
                    progress_callback(f"Errore durante lo spostamento: {e}")
                break

        if not moved:
             raise OSError(f"Impossibile spostare il file '{os.path.basename(pdf_path)}' dopo 3 tentativi.")

        if progress_callback:
            progress_callback("Elaborazione completata.")

        return True, "Successo"

    except Exception as e:
        if progress_callback:
            progress_callback(f"Errore: {e}")
        return False, str(e)
