# PDF Splitter and ROI Selector

This project contains two Python desktop applications for splitting scanned PDF files based on OCR rules and for selecting the Region of Interest (ROI) for OCR.

## Main Application

A GUI application that allows the user to:
- Select a scanned PDF file.
- Enter an ODC number.
- Split the file into multiple PDFs based on user-defined OCR classification rules.

## ROI Setup Utility

A separate GUI tool that allows the user to:
- Open a sample PDF file.
- Visually draw areas (ROIs).
- Save the coordinates for the main application.

## Configuration

The system uses a single external `config.json` file to store all settings, which is shared between the main application and the ROI utility.

The configuration file stores:
- The path to the Tesseract-OCR executable.
- A template for the output file name (e.g., `{ODC}_{category}.pdf`).
- A list of "Classification Rules".

Each classification rule contains:
- `category_name`: (e.g., "consuntivo", "pdl", "rapportini")
- `keyword`: The exact text (case-insensitive) to search for via OCR (e.g., "Riepilogo", "PDL").
- `roi`: The coordinates (x0, y0, x1, y1) where to search for the keyword.

## Dependencies

- tkinter
- PyMuPDF (fitz)
- Pillow (PIL)
- pytesseract
- Tesseract-OCR
- json or configparser
