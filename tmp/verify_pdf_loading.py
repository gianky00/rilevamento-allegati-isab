import fitz
import os
import glob

def test_pdf_loading():
    # Cerca un PDF nel progetto
    pdfs = glob.glob("**/*.pdf", recursive=True)
    if not pdfs:
        print("Nessun file PDF trovato per il test.")
        return

    pdf_path = pdfs[0]
    print(f"Testando il caricamento di: {pdf_path}")
    
    try:
        doc = fitz.open(pdf_path)
        print(f"Pagine: {doc.page_count}")
        if doc.page_count > 0:
            page = doc.load_page(0)
            mat = fitz.Matrix(2.0, 2.0)
            pix = page.get_pixmap(matrix=mat)
            print(f"Dimensioni Pixmap (2x zoom): {pix.width}x{pix.height}")
            print(f"Sample size: {len(pix.samples)} byte")
        doc.close()
        print("VERIFICA COMPLETATA: La logica di PyMuPDF funziona correttamente.")
    except Exception as e:
        print(f"ERRORE nella verifica: {e}")

if __name__ == "__main__":
    test_pdf_loading()
