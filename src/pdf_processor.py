"""
Intelleo PDF Splitter - Processore PDF
Gestisce l'elaborazione e la divisione dei file PDF basata su regole OCR.
"""

import os
import shutil
import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

import pymupdf as fitz
import pytesseract
from PIL import Image


def _log(progress_callback: Optional[Callable[..., None]], msg: str, level: str = "INFO") -> None:
    """Log interno con timestamp se è definito un callback."""
    if progress_callback:
        progress_callback(msg, level)


def _log_separator(progress_callback: Optional[Callable[..., None]]) -> None:
    """Stampa un separatore visivo."""
    _log(progress_callback, "─" * 50, "INFO")


def _get_binary(img: Image.Image) -> Image.Image:
    """Restituisce la versione binarizzata di un'immagine per migliorare l'OCR."""
    return img.point(lambda x: 0 if x < 128 else 255, "1")


def _get_contrast(img: Image.Image) -> Image.Image:
    """Tenta l'autocontrasto estremo sull'immagine in base ai toni in scala di grigi."""
    try:
        from PIL import ImageOps
        return ImageOps.autocontrast(img)
    except Exception:
        return img


def _analyze_pages(
    pdf_doc: fitz.Document,
    rules: List[Dict[str, Any]],
    progress_callback: Optional[Callable[..., None]]
) -> Dict[str, List[int]]:
    """Esegue la scansione OCR su tutte le pagine ripartendole in categorie in base alle rules definite."""
    page_groups: Dict[str, List[int]] = {}
    total_pages = len(pdf_doc)
    avg_time_per_page = 0.0
    alpha = 0.3

    for i, page in enumerate(pdf_doc):
        page_start_time = time.time()
        eta_seconds: float = 0.0
        if i > 0 and avg_time_per_page > 0:
            remaining_pages = total_pages - i
            eta_seconds = remaining_pages * avg_time_per_page

        current_pct = ((i + 1) / total_pages) * 90

        if progress_callback:
            progress_callback(
                {
                    "type": "page_progress",
                    "current": i + 1,
                    "total": total_pages,
                    "eta_seconds": eta_seconds,
                    "phase": "analysis",
                    "phase_pct": current_pct,
                }
            )

        page_category = "sconosciuto"
        page_rect = page.rect
        page_found = False

        for rule in rules:
            if page_found:
                break
            rois = rule.get("rois", [])
            keywords = [k.lower() for k in rule.get("keywords", [])]
            category_name = rule.get("category_name", "sconosciuto")

            for roi in rois:
                if page_found:
                    break

                if not all(isinstance(c, int) and c >= 0 for c in roi) or len(roi) != 4:
                    continue

                roi_rect = fitz.Rect(roi)
                if roi_rect.x1 > page_rect.width or roi_rect.y1 > page_rect.height:
                    continue

                try:
                    text_content = page.get_text("text", clip=roi_rect).lower()
                    if any(keyword in text_content for keyword in keywords):
                        _log(progress_callback, f"   ⚡ Match veloce (Testo Nativo) per '{category_name}'", "INFO")
                        page_category = category_name
                        page_found = True
                        break
                except Exception:
                    pass

                if page_found:
                    break

                try:
                    mat = fitz.Matrix(300 / 72, 300 / 72)
                    pix = page.get_pixmap(matrix=mat, clip=roi_rect, colorspace=fitz.csGRAY)
                    if pix.width < 1 or pix.height < 1:
                        continue
                    base_img = Image.frombytes("L", (pix.width, pix.height), pix.samples)
                except Exception as e:
                    _log(progress_callback, f"⚠ Rendering ROI '{category_name}': {e}", "WARNING")
                    continue

                steps: List[Dict[str, Any]] = [
                    {"name": "Standard", "img": base_img, "angles": [0, -90]},
                    {"name": "Binary", "img": _get_binary(base_img), "angles": [0, -90]},
                    {"name": "DeepRotate", "img": _get_binary(base_img), "angles": [90, 180]},
                    {"name": "Contrast", "img": _get_contrast(base_img), "angles": [0, -90]},
                ]

                roi_found = False
                for step in steps:
                    if roi_found:
                        break
                    current_img = step["img"]
                    for angle in step["angles"]:
                        if roi_found:
                            break
                        img_to_scan = current_img if angle == 0 else current_img.rotate(angle, expand=True)

                        try:
                            ocr_text = pytesseract.image_to_string(
                                img_to_scan, lang="ita", config="--psm 6", timeout=15
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

        if page_category not in page_groups:
            page_groups[page_category] = []
        page_groups[page_category].append(i)

        page_end_time = time.time()
        this_page_time = page_end_time - page_start_time
        if i == 0:
            avg_time_per_page = this_page_time
        else:
            avg_time_per_page = (alpha * this_page_time) + ((1 - alpha) * avg_time_per_page)

    return page_groups


def _save_split_pdfs(
    pdf_doc: fitz.Document,
    page_groups: Dict[str, List[int]],
    rules: List[Dict[str, Any]],
    base_output_dir: str,
    odc: str,
    progress_callback: Optional[Callable[..., None]]
) -> List[Dict[str, Any]]:
    """Basato sui gruppi logici, salva la documentazione su filesystem in PDF divisi, tentando il retry su file chiusi."""
    generated_files: List[Dict[str, Any]] = []
    total_pages = len(pdf_doc)

    if progress_callback:
        progress_callback(
            {
                "type": "page_progress",
                "current": total_pages,
                "total": total_pages,
                "eta_seconds": 0,
                "phase": "saving",
                "phase_pct": 95,
            }
        )

    for category, pages in page_groups.items():
        if not pages:
            continue

        suffix = category
        if category != "sconosciuto":
            for rule in rules:
                if rule.get("category_name") == category:
                    suffix = rule.get("filename_suffix", category)
                    if not suffix:
                        suffix = category
                    break

        output_filename = f"{odc}_.pdf" if category == "sconosciuto" else f"{odc}_{suffix}.pdf"
        output_path = os.path.join(base_output_dir, output_filename)

        new_pdf = fitz.open()
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

            for block_start, block_end in ranges:
                new_pdf.insert_pdf(pdf_doc, from_page=block_start, to_page=block_end)

        saved = False
        save_error: Optional[Exception] = None

        for attempt in range(3):
            try:
                new_pdf.save(output_path)
                saved = True
                break
            except PermissionError as e:
                save_error = e
                _log(progress_callback, f"⚠ Tentativo {attempt + 1}/3: file bloccato", "WARNING")
                time.sleep(1.0)
            except Exception as e:
                save_error = e
                break

        new_pdf.close()

        if not saved:
            _log(progress_callback, f"✗ Errore salvataggio {output_filename}: {save_error}", "ERROR")
            continue

        abs_path = os.path.abspath(output_path)
        _log(progress_callback, f"   ✓ {output_filename}", "INFO")
        generated_files.append({"category": category, "path": abs_path})

    return generated_files


def _archive_original_file(pdf_path: str, base_output_dir: str, progress_callback: Optional[Callable[..., None]]) -> str:
    """Archivia in cartella separata 'ORIGINALI' il template sorgente."""
    if os.path.basename(base_output_dir) == "ORIGINALI":
        originali_dir = base_output_dir
    else:
        originali_dir = os.path.join(base_output_dir, "ORIGINALI")
        os.makedirs(originali_dir, exist_ok=True)

    destination_path = os.path.join(originali_dir, os.path.basename(pdf_path))

    if os.path.abspath(destination_path) == os.path.abspath(pdf_path):
        _log(progress_callback, "   [i] File già in ORIGINALI", "INFO")
        return pdf_path

    if os.path.exists(destination_path):
        for _attempt in range(3):
            try:
                os.remove(destination_path)
                break
            except OSError:
                time.sleep(1.0)

    moved = False
    for attempt in range(3):
        try:
            shutil.move(pdf_path, destination_path)
            moved = True
            moved_original_path = destination_path
            break
        except PermissionError:
            _log(progress_callback, f"⚠ Tentativo spostamento {attempt + 1}/3", "WARNING")
            time.sleep(1.0)
        except Exception as e:
            _log(progress_callback, f"✗ Errore spostamento: {e}", "ERROR")
            break

    if not moved:
        raise OSError(f"Impossibile spostare '{os.path.basename(pdf_path)}'")

    _log(progress_callback, "   ✓ Spostato in ORIGINALI", "INFO")
    return moved_original_path


def process_pdf(
    pdf_path: str,
    odc: str,
    config: Dict[str, Any],
    progress_callback: Optional[Callable[..., None]] = None
) -> Tuple[bool, str, List[Dict[str, Any]], Optional[str]]:
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
    generated_files: List[Dict[str, Any]] = []
    moved_original_path = None
    start_time = datetime.now()

    _log(progress_callback, f"📄 File: {os.path.basename(pdf_path)}", "INFO")
    _log(progress_callback, f"📁 Percorso: {os.path.dirname(pdf_path)}", "INFO")
    _log_separator(progress_callback)

    try:
        tesseract_path = config.get("tesseract_path")
        if tesseract_path and os.path.isfile(tesseract_path):
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
            _log(progress_callback, "✓ Tesseract OCR configurato", "INFO")
        else:
            raise ValueError("Percorso Tesseract non configurato o non valido")

        pdf_doc = fitz.open(pdf_path)
        total_pages = len(pdf_doc)
        _log(progress_callback, f"✓ PDF aperto: {total_pages} pagine", "INFO")
        _log_separator(progress_callback)

        _log(progress_callback, "🔍 ANALISI OCR IN CORSO (Modalita' Smart)...", "INFO")
        rules = config.get("classification_rules", [])
        _log(progress_callback, f"   Regole di classificazione: {len(rules)}", "INFO")

        page_groups = _analyze_pages(pdf_doc, rules, progress_callback)

        _log_separator(progress_callback)
        _log(progress_callback, "📊 RISULTATO CLASSIFICAZIONE:", "INFO")
        for cat, pages in page_groups.items():
            icon = "✓" if cat != "sconosciuto" else "?"
            _log(progress_callback, f"   {icon} {cat}: {len(pages)} pagine", "INFO")

        _log_separator(progress_callback)
        _log(progress_callback, "💾 SALVATAGGIO FILE...", "INFO")
        
        base_output_dir = os.path.dirname(pdf_path)
        generated_files = _save_split_pdfs(pdf_doc, page_groups, rules, base_output_dir, odc, progress_callback)
        pdf_doc.close()

        _log_separator(progress_callback)
        _log(progress_callback, "📦 ARCHIVIAZIONE ORIGINALE...", "INFO")
        moved_original_path = _archive_original_file(pdf_path, base_output_dir, progress_callback)

        elapsed = datetime.now() - start_time
        elapsed_str = str(elapsed).split(".")[0]

        _log_separator(progress_callback)
        _log(progress_callback, f"✅ COMPLETATO in {elapsed_str}", "SUCCESS")
        _log(progress_callback, f"   File generati: {len(generated_files)}", "INFO")

        return True, "Successo", generated_files, moved_original_path

    except Exception as e:
        _log(progress_callback, f"❌ ERRORE CRITICO: {e}", "ERROR")
        return False, str(e), generated_files, None
