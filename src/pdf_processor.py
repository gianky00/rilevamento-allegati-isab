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
        log("🔍 ANALISI OCR IN CORSO (Modalita' Smart)...", "INFO")
        
        page_groups = {}
        rules = config.get("classification_rules", [])
        rules_count = len(rules)
        
        log(f"   Regole di classificazione: {rules_count}", "INFO")

        # Variabili per calcolo ETA
        avg_time_per_page = 0.0
        alpha = 0.3  # Fattore smorzamento media mobile (0.0-1.0)

        for i, page in enumerate(pdf_doc):
            page_start_time = time.time()
            
            # Calcolo ETA
            eta_seconds = 0
            if i > 0 and avg_time_per_page > 0:
                remaining_pages = total_pages - i
                eta_seconds = remaining_pages * avg_time_per_page

            # Invia aggiornamento strutturato (Smart Progress - Scalato al 90% per lasciare spazio al salvataggio)
            # Analysis Phase: 0% -> 90%
            current_pct = ((i + 1) / total_pages) * 90
            
            if progress_callback:
                progress_callback({
                    'type': 'page_progress',
                    'current': i + 1,
                    'total': total_pages,
                    'eta_seconds': eta_seconds,
                    'phase': 'analysis',
                    'phase_pct': current_pct
                })

            page_category = "sconosciuto"
            page_rect = page.rect
            page_found = False  # Flag per uscita rapida se trovato match

            # Itera attraverso ogni regola
            for rule in rules:
                if page_found: break
                
                rois = rule.get("rois", [])
                keywords = [k.lower() for k in rule.get("keywords", [])]
                category_name = rule.get("category_name")

                # Cicla attraverso ogni ROI definita
                for roi in rois:
                    if page_found: break

                    if not all(isinstance(c, int) and c >= 0 for c in roi) or len(roi) != 4:
                        continue

                    roi_rect = fitz.Rect(roi)

                    # Verifica che la ROI sia all'interno della pagina
                    if roi_rect.x1 > page_rect.width or roi_rect.y1 > page_rect.height:
                        continue

                    # ================================================================
                    # OTTIMIZZAZIONE 0: TEXT EXTRACTION (Direct)
                    # ================================================================
                    # Prima di usare l'OCR (lento), proviamo ad estrarre il testo 
                    # direttamente dal PDF se è un PDF nativo/digitale.
                    try:
                        text_content = page.get_text("text", clip=roi_rect).lower()
                        if any(keyword in text_content for keyword in keywords):
                            log(f"   ⚡ Match veloce (Testo Nativo) per '{category_name}'", "INFO")
                            page_category = category_name
                            roi_found = True
                            page_found = True
                            break
                    except Exception:
                        pass # Fallback su OCR

                    if page_found: break

                    # OTTIMIZZAZIONE 1: Risoluzione Bilanciata (300 DPI invece di 400)
                    # 300 DPI è lo standard per OCR e riduce i tempi del 40-50% rispetto a 400 DPI
                    try:
                        mat = fitz.Matrix(300/72, 300/72)
                        pix = page.get_pixmap(matrix=mat, clip=roi_rect, colorspace=fitz.csGRAY)
                        
                        if pix.width < 1 or pix.height < 1:
                            continue

                        base_img = Image.frombytes("L", [pix.width, pix.height], pix.samples)
                    except Exception as e:
                        log(f"⚠ Rendering ROI '{category_name}': {e}", "WARNING")
                        continue

                    # OTTIMIZZAZIONE 2: "LAZY EVALUATION" (A Cascata)
                    # Helper functions per varianti immagine
                    def get_binary(img):
                        return img.point(lambda x: 0 if x < 128 else 255, '1')
                    
                    def get_contrast(img):
                        try:
                            from PIL import ImageOps
                            return ImageOps.autocontrast(img)
                        except:
                            return img

                    # Strategia a passaggi successivi
                    steps = [
                        # Passo 1: Veloce. Immagine originale, angoli standard. 
                        # Copre il 90% dei casi.
                        {'name': 'Standard', 'img': base_img, 'angles': [0, -90]},
                        
                        # Passo 2: Contrasto forte (Binarizzata). 
                        # Per testi sbiaditi o scuri su fondo chiaro.
                        {'name': 'Binary', 'img': get_binary(base_img), 'angles': [0, -90]},
                        
                        # Passo 3: Disperato. Angoli "strani" (90, 180).
                        # Copre documenti capovolti o ruotati a destra.
                        {'name': 'DeepRotate', 'img': get_binary(base_img), 'angles': [90, 180]},
                        
                        # Passo 4: Ultima spiaggia. Autocontrast.
                        {'name': 'Contrast', 'img': get_contrast(base_img), 'angles': [0, -90]}
                    ]

                    roi_found = False

                    for step in steps:
                        if roi_found: break
                        
                        current_img = step['img']
                        
                        for angle in step['angles']:
                            if roi_found: break

                            # Ruota l'immagine solo se necessario
                            img_to_scan = current_img
                            if angle != 0:
                                img_to_scan = current_img.rotate(angle, expand=True)

                            try:
                                # Configurazione Tesseract Ottimizzata per ROI:
                                # --psm 6: Assume un singolo blocco di testo uniforme (ideale per ROI)
                                ocr_text = pytesseract.image_to_string(
                                    img_to_scan, 
                                    lang='ita', 
                                    config='--psm 6',
                                    timeout=15  # Timeout ridotto per non bloccare
                                ).lower()
                                
                                if any(keyword in ocr_text for keyword in keywords):
                                    page_category = category_name
                                    roi_found = True
                                    page_found = True
                                    break
                            except Exception:
                                pass

                    if page_category == category_name:
                        break

                if page_category == category_name:
                    break

            # Aggiunge la pagina al gruppo
            if page_category not in page_groups:
                page_groups[page_category] = []
            page_groups[page_category].append(i)

            # Aggiornamento statistiche tempo (Media Mobile)
            page_end_time = time.time()
            this_page_time = page_end_time - page_start_time
            if i == 0:
                avg_time_per_page = this_page_time
            else:
                avg_time_per_page = (alpha * this_page_time) + ((1 - alpha) * avg_time_per_page)

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
            
            if progress_callback:
                progress_callback({
                    'type': 'page_progress',
                    'current': total_pages,
                    'total': total_pages,
                    'eta_seconds': 0,
                    'phase': 'saving',
                    'phase_pct': 95  # Jump to 95% during saving
                })

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
