import tkinter as tk
from tkinter import ttk, filedialog, simpledialog, messagebox
import pymupdf as fitz  # PyMuPDF
from PIL import Image, ImageTk
import os
import config_manager
import itertools

class ROIDrawingApp:
    """
    Applicazione di utilità per disegnare Regioni di Interesse (ROI) su più pagine di un PDF
    e salvare le coordinate nel file di configurazione.
    """
    def __init__(self, root):
        self.root = root
        self.root.title("Utility di Rilevamento ROI Multi-Pagina")
        self.root.geometry("1200x900")

        # --- Variabili di Stato ---
        self.pdf_doc = None
        self.tk_image = None
        self.current_page_index = 0
        self.config = config_manager.load_config()
        self.roi_colors = self.generate_roi_colors()

        # --- Layout GUI ---
        # Frame Superiore per i Controlli
        control_frame = ttk.Frame(self.root)
        control_frame.pack(pady=5, padx=10, fill=tk.X)

        ttk.Button(control_frame, text="Apri PDF di Esempio", command=self.open_pdf).pack(side=tk.LEFT, padx=5)

        self.nav_frame = ttk.Frame(control_frame)
        self.prev_page_button = ttk.Button(self.nav_frame, text="<< Pagina Precedente", command=self.prev_page, state=tk.DISABLED)
        self.prev_page_button.pack(side=tk.LEFT)
        self.page_label = ttk.Label(self.nav_frame, text="Nessun PDF caricato", anchor=tk.CENTER, width=20)
        self.page_label.pack(side=tk.LEFT, padx=10)
        self.next_page_button = ttk.Button(self.nav_frame, text="Pagina Successiva >>", command=self.next_page, state=tk.DISABLED)
        self.next_page_button.pack(side=tk.LEFT)

        # Frame per il Canvas Scorrevole
        canvas_frame = ttk.Frame(self.root)
        canvas_frame.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)

        self.canvas = tk.Canvas(canvas_frame, bg="gray")
        self.h_scroll = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.v_scroll = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.canvas.config(xscrollcommand=self.h_scroll.set, yscrollcommand=self.v_scroll.set)

        self.h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        self.v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)

        # --- Variabili per il Disegno ---
        self.rect = None
        self.start_x = None
        self.start_y = None

        # --- Binding Eventi Mouse ---
        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)

    def generate_roi_colors(self):
        """Genera un ciclo di colori distinti per le ROI."""
        colors = ["red", "green", "blue", "cyan", "magenta", "yellow", "orange", "purple", "brown"]
        return itertools.cycle(colors)

    def open_pdf(self):
        """Apre un file PDF e renderizza la prima pagina."""
        filepath = filedialog.askopenfilename(title="Seleziona un PDF di Esempio", filetypes=[("PDF Files", "*.pdf")])
        if not filepath: return

        try:
            self.pdf_doc = fitz.open(filepath)
            if self.pdf_doc.page_count > 0:
                self.current_page_index = 0
                self.nav_frame.pack(side=tk.LEFT, padx=20) # Mostra la navigazione
                self.render_page(self.current_page_index)
            else:
                messagebox.showwarning("PDF Vuoto", "Il documento selezionato non ha pagine.")
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile aprire il PDF: {e}")

    def render_page(self, page_index):
        """Renderizza la pagina specificata, inclusi tutti i ROI esistenti."""
        if not self.pdf_doc: return

        self.current_page_index = page_index
        page = self.pdf_doc[page_index]
        pix = page.get_pixmap(dpi=300)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        self.tk_image = ImageTk.PhotoImage(img)

        self.canvas.delete("all")
        self.canvas.config(scrollregion=(0, 0, pix.width, pix.height))
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_image)

        self.draw_existing_rois()
        self.update_nav_controls()

    def draw_existing_rois(self):
        """Disegna tutti i ROI dal file di configurazione sulla pagina corrente."""
        self.config = config_manager.load_config() # Ricarica per avere i dati più recenti
        factor = 300 / 72  # Fattore di conversione da punti PDF a pixel

        for rule in self.config.get("classification_rules", []):
            roi = rule.get("roi")
            if not all(isinstance(c, int) and c >= 0 for c in roi) or len(roi) != 4 or sum(roi) == 0:
                continue

            color = next(self.roi_colors)
            category_name = rule.get("category_name", "N/A")

            # Converte le coordinate della ROI
            x0, y0, x1, y1 = [c * factor for c in roi]

            # Disegna il rettangolo e l'etichetta
            self.canvas.create_rectangle(x0, y0, x1, y1, outline=color, width=2, dash=(4, 4))
            self.canvas.create_text(x0 + 5, y0 + 5, text=category_name, fill="white", font=("Arial", 10, "bold"), anchor="nw",
                                    # Aggiunge un piccolo sfondo nero per la leggibilità
                                    tags="label_bg", state=tk.HIDDEN)
            self.canvas.create_text(x0 + 5, y0 + 5, text=category_name, fill=color, font=("Arial", 10, "bold"), anchor="nw")

    def update_nav_controls(self):
        """Aggiorna lo stato dei pulsanti di navigazione e l'etichetta della pagina."""
        if not self.pdf_doc: return

        total_pages = self.pdf_doc.page_count
        self.page_label.config(text=f"Pagina {self.current_page_index + 1} / {total_pages}")

        self.prev_page_button.config(state=tk.NORMAL if self.current_page_index > 0 else tk.DISABLED)
        self.next_page_button.config(state=tk.NORMAL if self.current_page_index < total_pages - 1 else tk.DISABLED)

    def prev_page(self):
        if self.current_page_index > 0:
            self.render_page(self.current_page_index - 1)

    def next_page(self):
        if self.pdf_doc and self.current_page_index < self.pdf_doc.page_count - 1:
            self.render_page(self.current_page_index + 1)

    def on_button_press(self, event):
        self.start_x = self.canvas.canvasx(event.x)
        self.start_y = self.canvas.canvasy(event.y)
        if self.rect: self.canvas.delete(self.rect)
        self.rect = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline='white', width=3)

    def on_mouse_drag(self, event):
        cur_x, cur_y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        self.canvas.coords(self.rect, self.start_x, self.start_y, cur_x, cur_y)

    def on_button_release(self, event):
        end_x, end_y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)

        # Normalizza e converte le coordinate in punti PDF
        x0, y0 = min(self.start_x, end_x), min(self.start_y, end_y)
        x1, y1 = max(self.start_x, end_x), max(self.start_y, end_y)
        factor = 72 / 300
        roi_pdf_coords = [int(x0 * factor), int(y0 * factor), int(x1 * factor), int(y1 * factor)]

        self.prompt_and_save_roi(roi_pdf_coords)
        # Rimuovi il rettangolo di disegno temporaneo
        self.canvas.delete(self.rect)
        self.rect = None

    def prompt_and_save_roi(self, roi_coords):
        """Chiede all'utente a quale categoria associare la nuova ROI e salva."""
        self.config = config_manager.load_config()
        categories = [rule["category_name"] for rule in self.config.get("classification_rules", [])]
        if not categories:
            messagebox.showwarning("Nessuna Categoria", "Nessuna categoria definita. Aggiungine una nell'app principale.")
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("Salva ROI")

        ttk.Label(dialog, text=f"Coordinate: {roi_coords}").pack(pady=5)
        ttk.Label(dialog, text="Associa alla categoria:").pack(pady=5)

        category_var = tk.StringVar()
        category_combo = ttk.Combobox(dialog, textvariable=category_var, values=categories, state='readonly')
        category_combo.pack(pady=5)
        if categories: category_combo.set(categories[0])

        def save():
            selected_category = category_var.get()
            if not selected_category: return

            for rule in self.config["classification_rules"]:
                if rule["category_name"] == selected_category:
                    rule["roi"] = roi_coords
                    break

            try:
                config_manager.save_config(self.config)
                messagebox.showinfo("Successo", f"ROI per '{selected_category}' salvata.", parent=self.root)
                dialog.destroy()
                # Ridisegna la pagina per mostrare la nuova ROI salvata
                self.render_page(self.current_page_index)
            except Exception as e:
                messagebox.showerror("Errore", f"Impossibile salvare: {e}", parent=dialog)

        ttk.Button(dialog, text="Salva ROI", command=save).pack(pady=10)

if __name__ == "__main__":
    root = tk.Tk()
    app = ROIDrawingApp(root)
    root.mainloop()
