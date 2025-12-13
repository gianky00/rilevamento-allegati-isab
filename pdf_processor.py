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
            La signature attesa è `progress_callback(message, level="INFO")`.

    Returns:
        tuple: (success (bool), message (str), generated_files (list), moved_original_path (str or None))
               generated_files è una lista di dict: {'category': str, 'path': str}
    """
    generated_files = []
    moved_original_path = None

    def log(msg, level="INFO"):
        if progress_callback:
            progress_callback(msg, level)

    log(f"Avvio dell'elaborazione del PDF: {os.path.basename(pdf_path)}", "INFO")

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
            # Dynamic log update format implied by repeated calls with same prefix?
            # The UI handles the "Elaborazione pagina X/Y..." logic if we send a specific message format.
            log(f"Elaborazione pagina {i + 1}/{total_pages}...", "PROGRESS")

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
                        log(f"Errore rendering ROI per '{category_name}': {e}", "WARNING")
                        continue

                    # Tenta l'OCR sull'immagine originale e poi ruotata
                    for angle in [0, -90]: # 0 = nessuna rotazione, -90 = 90 gradi orario
                        img_to_scan = cropped_img
                        if angle != 0:
                            img_to_scan = cropped_img.rotate(angle, expand=True)

                        try:
                            # Add timeout to prevent indefinite hangs
                            ocr_text = pytesseract.image_to_string(img_to_scan, lang='ita', timeout=30).lower()
                            # print(f"DEBUG OCR (angle={angle}): '{ocr_text}'")
                            if any(keyword in ocr_text for keyword in keywords):
                                page_category = category_name
                                break  # Keyword trovata, esce dal ciclo di rotazione
                        except Exception as ocr_error:
                            log(f"Avviso OCR per '{category_name}': {ocr_error}", "WARNING")

                    if page_category == category_name:
                        break  # Regola trovata, interrompe il ciclo delle ROI

                if page_category == category_name:
                    break  # Regola trovata, interrompe il ciclo delle regole

            # Aggiunge l'indice della pagina al gruppo corrispondente
            if page_category not in page_groups:
                page_groups[page_category] = []
            page_groups[page_category].append(i)

        log("Raggruppamento e salvataggio dei PDF...", "INFO")

        base_output_dir = os.path.dirname(pdf_path)

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

            if category == "sconosciuto":
                output_filename = f"{odc}_.pdf"
            else:
                output_filename = f"{odc}_{suffix}.pdf"

            output_path = os.path.join(base_output_dir, output_filename)

            new_pdf = fitz.open()

            # Optimization: Insert contiguous page ranges instead of single pages
            if pages:
                pages.sort()
                ranges = []
                if pages:
                    start = pages[0]
                    end = pages[0]
                    for p in pages[1:]:
                        if p == end + 1:
                            end = p
                        else:
                            ranges.append((start, end))
                            start = p
                            end = p
                    ranges.append((start, end))

                for start, end in ranges:
                    new_pdf.insert_pdf(pdf_doc, from_page=start, to_page=end)

            # Retry loop for saving file (robustness against locks)
            saved = False
            save_error = None
            for attempt in range(3):
                try:
                    new_pdf.save(output_path)
                    saved = True
                    break
                except PermissionError as e:
                    save_error = e
                    log(f"Tentativo salvataggio {attempt+1}/3 fallito (file bloccato): {output_filename}. Riprovo...", "WARNING")
                    time.sleep(1.0)
                except Exception as e:
                    save_error = e
                    break

            new_pdf.close()

            if not saved:
                log(f"Errore: Impossibile salvare {output_filename}: {save_error}", "ERROR")
                continue

            abs_path = os.path.abspath(output_path)
            log(f"Salvato: {abs_path}", "INFO")

            generated_files.append({
                'category': category,
                'path': abs_path
            })

        pdf_doc.close()

        # Sposta il file originale nella cartella ORIGINALI
        log("Spostamento file originale...", "INFO")

        # Check if we are already in an ORIGINALI directory to avoid nesting
        if os.path.basename(base_output_dir) == "ORIGINALI":
            originali_dir = base_output_dir
        else:
            originali_dir = os.path.join(base_output_dir, "ORIGINALI")
            os.makedirs(originali_dir, exist_ok=True)

        destination_path = os.path.join(originali_dir, os.path.basename(pdf_path))

        # Check if destination is the same as source (e.g. processed inside ORIGINALI)
        if os.path.abspath(destination_path) == os.path.abspath(pdf_path):
            log("Il file è già nella cartella ORIGINALI. Nessuno spostamento necessario.", "INFO")
            moved_original_path = pdf_path
        else:
            # Handle overwrite with retry logic for deletion
            if os.path.exists(destination_path):
                removed = False
                for attempt in range(3):
                    try:
                        os.remove(destination_path)
                        removed = True
                        break
                    except OSError as e:
                        log(f"Tentativo rimozione destinazione {attempt+1}/3 fallito: {e}. Riprovo...", "WARNING")
                        time.sleep(1.0)
                if not removed:
                    log(f"Avviso: Impossibile rimuovere il file esistente in ORIGINALI dopo 3 tentativi.", "WARNING")
                    # Move might fail if remove failed, but we try anyway

            # Retry loop for file move (robustness against file locks)
            moved = False
            for attempt in range(3):
                try:
                    shutil.move(pdf_path, destination_path)
                    moved = True
                    moved_original_path = destination_path
                    break
                except PermissionError:
                    log(f"Tentativo spostamento {attempt+1}/3 fallito (file bloccato). Riprovo...", "WARNING")
                    time.sleep(1.0)
                except Exception as e:
                    log(f"Errore durante lo spostamento: {e}", "ERROR")
                    break

            if not moved:
                 raise OSError(f"Impossibile spostare il file '{os.path.basename(pdf_path)}' dopo 3 tentativi.")

        log("Elaborazione completata.", "INFO")

        return True, "Successo", generated_files, moved_original_path

    except Exception as e:
        log(f"Errore critico: {e}", "ERROR")
        return False, str(e), generated_files, None
