"""
Intelleo PDF Splitter - Processore PDF
Gestisce l'elaborazione e la divisione dei file PDF basata su regole OCR.
"""
import pymupdf as fitz
import pytesseract
from PIL import Image
import os
import shutil
import time
from datetime import datetime


def process_pdf(pdf_path, odc, config, progress_callback=None):
    """
    Elabora un file PDF, classifica le pagine in base a regole OCR e salva i PDF divisi.

    Args:
        pdf_path (str): Il percorso del file PDF da elaborare.
        odc (str): Il numero ODC da utilizzare nel nome del file di output.
        config (dict): Il dizionario di configurazione contenente le impostazioni.
        progress_callback (function, optional): Funzione per riportare i progressi.
            Signature: progress_callback(message, level="INFO")

    Returns:
        tuple: (success, message, generated_files, moved_original_path)
               generated_files: lista di dict {'category': str, 'path': str}
    """
    generated_files = []
    moved_original_path = None
    start_time = datetime.now()

    def log(msg, level="INFO"):
        """Log interno con timestamp."""
        if progress_callback:
            progress_callback(msg, level)

    def log_separator():
        """Stampa un separatore visivo."""
        log("─" * 50, "INFO")

    # ========================================================================
    # FASE 1: INIZIALIZZAZIONE
    # ========================================================================
    log(f"📄 File: {os.path.basename(pdf_path)}", "INFO")
    log(f"📁 Percorso: {os.path.dirname(pdf_path)}", "INFO")
    log_separator()

    try:
        # Verifica Tesseract
        tesseract_path = config.get("tesseract_path")
        if tesseract_path and os.path.isfile(tesseract_path):
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
            log("✓ Tesseract OCR configurato", "INFO")
        else:
            raise ValueError("Percorso Tesseract non configurato o non valido")

        # Apertura PDF
        pdf_doc = fitz.open(pdf_path)
        total_pages = len(pdf_doc)
        log(f"✓ PDF aperto: {total_pages} pagine", "INFO")
        log_separator()

        # ====================================================================
        # FASE 2: ANALISI OCR DELLE PAGINE
        # ====================================================================
        log("🔍 ANALISI OCR IN CORSO...", "INFO")
        
        page_groups = {}
        rules = config.get("classification_rules", [])
        rules_count = len(rules)
        
        log(f"   Regole di classificazione: {rules_count}", "INFO")

        for i, page in enumerate(pdf_doc):
            log(f"Elaborazione pagina {i + 1}/{total_pages}...", "PROGRESS")

            page_category = "sconosciuto"
            page_rect = page.rect

            # Itera attraverso ogni regola
            for rule in rules:
                rois = rule.get("rois", [])
                keywords = [k.lower() for k in rule.get("keywords", [])]
                category_name = rule.get("category_name")

                # Cicla attraverso ogni ROI definita
                for roi in rois:
                    if not all(isinstance(c, int) and c >= 0 for c in roi) or len(roi) != 4:
                        continue

                    roi_rect = fitz.Rect(roi)

                    # Verifica che la ROI sia all'interno della pagina
                    if roi_rect.x1 > page_rect.width or roi_rect.y1 > page_rect.height:
                        continue

                    # Renderizza l'area ROI a 300 DPI in scala di grigi
                    mat = fitz.Matrix(300/72, 300/72)
                    try:
                        pix = page.get_pixmap(matrix=mat, clip=roi_rect, colorspace=fitz.csGRAY)
                        
                        if pix.width < 1 or pix.height < 1:
                            continue

                        cropped_img = Image.frombytes("L", [pix.width, pix.height], pix.samples)
                    except Exception as e:
                        log(f"⚠ Rendering ROI '{category_name}': {e}", "WARNING")
                        continue

                    # OCR con rotazione automatica
                    for angle in [0, -90]:
                        img_to_scan = cropped_img
                        if angle != 0:
                            img_to_scan = cropped_img.rotate(angle, expand=True)

                        try:
                            ocr_text = pytesseract.image_to_string(
                                img_to_scan, lang='ita', timeout=30).lower()
                            
                            if any(keyword in ocr_text for keyword in keywords):
                                page_category = category_name
                                break
                        except Exception as ocr_error:
                            log(f"⚠ OCR '{category_name}': {ocr_error}", "WARNING")

                    if page_category == category_name:
                        break

                if page_category == category_name:
                    break

            # Aggiunge la pagina al gruppo
            if page_category not in page_groups:
                page_groups[page_category] = []
            page_groups[page_category].append(i)

        # Sommario classificazione
        log_separator()
        log("📊 RISULTATO CLASSIFICAZIONE:", "INFO")
        for cat, pages in page_groups.items():
            icon = "✓" if cat != "sconosciuto" else "?"
            log(f"   {icon} {cat}: {len(pages)} pagine", "INFO")

        # ====================================================================
        # FASE 3: SALVATAGGIO DEI PDF DIVISI
        # ====================================================================
        log_separator()
        log("💾 SALVATAGGIO FILE...", "INFO")

        base_output_dir = os.path.dirname(pdf_path)

        for category, pages in page_groups.items():
            if not pages:
                continue

            # Determina il suffisso del file
            suffix = category
            if category != "sconosciuto":
                for rule in rules:
                    if rule["category_name"] == category:
                        suffix = rule.get("filename_suffix", category)
                        if not suffix:
                            suffix = category
                        break

            if category == "sconosciuto":
                output_filename = f"{odc}_.pdf"
            else:
                output_filename = f"{odc}_{suffix}.pdf"

            output_path = os.path.join(base_output_dir, output_filename)

            # Crea nuovo PDF
            new_pdf = fitz.open()

            # Inserisci pagine per range contigui (ottimizzazione)
            if pages:
                pages.sort()
                ranges = []
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

            # Salvataggio con retry
            saved = False
            save_error = None
            
            for attempt in range(3):
                try:
                    new_pdf.save(output_path)
                    saved = True
                    break
                except PermissionError as e:
                    save_error = e
                    log(f"⚠ Tentativo {attempt+1}/3: file bloccato", "WARNING")
                    time.sleep(1.0)
                except Exception as e:
                    save_error = e
                    break

            new_pdf.close()

            if not saved:
                log(f"✗ Errore salvataggio {output_filename}: {save_error}", "ERROR")
                continue

            abs_path = os.path.abspath(output_path)
            log(f"   ✓ {output_filename}", "INFO")

            generated_files.append({
                'category': category,
                'path': abs_path
            })

        pdf_doc.close()

        # ====================================================================
        # FASE 4: SPOSTAMENTO FILE ORIGINALE
        # ====================================================================
        log_separator()
        log("📦 ARCHIVIAZIONE ORIGINALE...", "INFO")

        if os.path.basename(base_output_dir) == "ORIGINALI":
            originali_dir = base_output_dir
        else:
            originali_dir = os.path.join(base_output_dir, "ORIGINALI")
            os.makedirs(originali_dir, exist_ok=True)

        destination_path = os.path.join(originali_dir, os.path.basename(pdf_path))

        if os.path.abspath(destination_path) == os.path.abspath(pdf_path):
            log("   ℹ File già in ORIGINALI", "INFO")
            moved_original_path = pdf_path
        else:
            # Gestione sovrascrittura
            if os.path.exists(destination_path):
                for attempt in range(3):
                    try:
                        os.remove(destination_path)
                        break
                    except OSError:
                        time.sleep(1.0)

            # Spostamento con retry
            moved = False
            for attempt in range(3):
                try:
                    shutil.move(pdf_path, destination_path)
                    moved = True
                    moved_original_path = destination_path
                    break
                except PermissionError:
                    log(f"⚠ Tentativo spostamento {attempt+1}/3", "WARNING")
                    time.sleep(1.0)
                except Exception as e:
                    log(f"✗ Errore spostamento: {e}", "ERROR")
                    break

            if not moved:
                raise OSError(f"Impossibile spostare '{os.path.basename(pdf_path)}'")

            log(f"   ✓ Spostato in ORIGINALI", "INFO")

        # ====================================================================
        # FASE 5: COMPLETAMENTO
        # ====================================================================
        elapsed = datetime.now() - start_time
        elapsed_str = str(elapsed).split('.')[0]

        log_separator()
        log(f"✅ COMPLETATO in {elapsed_str}", "SUCCESS")
        log(f"   File generati: {len(generated_files)}", "INFO")

        return True, "Successo", generated_files, moved_original_path

    except Exception as e:
        log(f"❌ ERRORE CRITICO: {e}", "ERROR")
        return False, str(e), generated_files, None
