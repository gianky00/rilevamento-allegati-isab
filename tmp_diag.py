"""Test reale: classificazione sul PDF dell'utente con il codice aggiornato."""
import json, os, sys

# CRITICO: rimuovi TESSDATA_PREFIX se era stato impostato erroneamente
os.environ.pop("TESSDATA_PREFIX", None)

sys.path.insert(0, 'src')

with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

pdf_path = r'prova\ORIGINALI\5400190165_40.pdf'

from core.ocr_engine import OcrEngine
from core.analysis_service import AnalysisService

ocr = OcrEngine(config['tesseract_path'])
analyzer = AnalysisService(config['classification_rules'], ocr)

import time
start = time.time()
groups = analyzer.analyze_pdf(pdf_path)
elapsed = time.time() - start

print(f"\nRISULTATI ({elapsed:.1f}s):")
for cat, pages in groups.items():
    print(f"  {cat}: {len(pages)} pagine -> {pages}")
print(f"\nTotale pagine classificate: {sum(len(p) for p in groups.values())}")
