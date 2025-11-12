import tkinter as tk
from tkinter import ttk, filedialog, simpledialog, messagebox
import pymupdf as fitz  # PyMuPDF
from PIL import Image, ImageTk
import os
import config_manager
import math

SIGNAL_FILE = ".update_signal"

class ROIDrawingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Utility di Gestione ROI")
        self.root.geometry("1200x900")

        self.pdf_doc = None
        self.tk_image = None
        self.current_page_index = 0
        self.config = config_manager.load_config()
        self.delete_mode = tk.BooleanVar(value=False)

        # --- Layout GUI ---
        control_frame = ttk.Frame(self.root)
        control_frame.pack(pady=5, padx=10, fill=tk.X)
        ttk.Button(control_frame, text="Apri PDF di Esempio", command=self.open_pdf).pack(side=tk.LEFT, padx=5)

        self.nav_frame = ttk.Frame(control_frame)
        ttk.Button(self.nav_frame, text="<< Pagina Prec.", command=self.prev_page).pack(side=tk.LEFT)
        self.page_label = ttk.Label(self.nav_frame, text="N/A", anchor=tk.CENTER, width=20)
        self.page_label.pack(side=tk.LEFT, padx=10)
        ttk.Button(self.nav_frame, text="Pagina Succ. >>", command=self.next_page).pack(side=tk.LEFT)

        # Pulsante per la modalità cancellazione
        self.delete_mode_button = ttk.Checkbutton(control_frame, text="Modalità Cancellazione ROI", variable=self.delete_mode, command=self.toggle_delete_mode)
        self.delete_mode_button.pack(side=tk.RIGHT, padx=20)

        canvas_frame = ttk.Frame(self.root)
        canvas_frame.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)
        self.canvas = tk.Canvas(canvas_frame, bg="gray", cursor="crosshair")
        # ... (scrollbars setup)
        self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)
        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)

        # Inizializzazione variabili di disegno
        self.rect = None
        self.start_x = None
        self.start_y = None

    def toggle_delete_mode(self):
        if self.delete_mode.get():
            self.canvas.config(cursor="pirate") # Cursore a forma di teschio per cancellare
        else:
            self.canvas.config(cursor="crosshair")

    def on_mouse_wheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def open_pdf(self):
        filepath = filedialog.askopenfilename(title="Seleziona PDF", filetypes=[("PDF Files", "*.pdf")])
        if not filepath: return
        self.pdf_doc = fitz.open(filepath)
        if self.pdf_doc.page_count > 0:
            self.current_page_index = 0
            self.nav_frame.pack(side=tk.LEFT, padx=20)
            self.render_page(self.current_page_index)

    def render_page(self, page_index):
        # ... (codice per renderizzare la pagina)
        self.draw_existing_rois()
        self.update_nav_controls()

    def draw_existing_rois(self):
        self.config = config_manager.load_config()
        self.canvas.delete("roi") # Cancella solo i vecchi ROI
        factor = 300 / 72
        for rule_index, rule in enumerate(self.config.get("classification_rules", [])):
            category_name = rule.get("category_name", "N/A")
            color = rule.get("color", "#FF0000")
            for roi_index, roi in enumerate(rule.get("rois", [])):
                if not all(isinstance(c, int) for c in roi) or len(roi) != 4: continue
                x0, y0, x1, y1 = [c * factor for c in roi]
                # Aggiungi tag univoci per identificare regola e ROI
                tag = f"roi_{rule_index}_{roi_index}"
                self.canvas.create_rectangle(x0, y0, x1, y1, outline=color, width=2, dash=(5, 3), tags=("roi", tag))
                self.canvas.create_text(x0 + 5, y0 + 5, text=category_name, fill=color, font=("Arial", 10, "bold"), anchor="nw", tags=("roi", f"label_{tag}"))

    def on_button_press(self, event):
        if self.delete_mode.get():
            self.handle_delete_click(event)
        else:
            self.start_x = self.canvas.canvasx(event.x)
            self.start_y = self.canvas.canvasy(event.y)
            if self.rect: self.canvas.delete(self.rect)
            self.rect = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline='black', width=2, dash=(5, 3))

    def on_mouse_drag(self, event):
        if not self.delete_mode.get():
            cur_x, cur_y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
            self.canvas.coords(self.rect, self.start_x, self.start_y, cur_x, cur_y)

    def on_button_release(self, event):
        if not self.delete_mode.get():
            # ... (logica per normalizzare e convertire le coordinate)
            factor = 72 / 300
            end_x, end_y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
            x0, y0, x1, y1 = min(self.start_x, end_x), min(self.start_y, end_y), max(self.start_x, end_x), max(self.start_y, end_y)
            roi_pdf_coords = [int(c * factor) for c in [x0, y0, x1, y1]]
            self.prompt_and_save_roi(roi_pdf_coords)
            self.canvas.delete(self.rect)
            self.rect = None

    def handle_delete_click(self, event):
        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        item_ids = self.canvas.find_closest(x, y)
        if not item_ids: return

        tags = self.canvas.gettags(item_ids[0])
        roi_tag = next((t for t in tags if t.startswith("roi_")), None)
        if not roi_tag: return

        _, rule_index_str, roi_index_str = roi_tag.split("_")
        rule_index, roi_index = int(rule_index_str), int(roi_index_str)

        rule = self.config["classification_rules"][rule_index]
        category_name = rule["category_name"]

        if messagebox.askyesno("Conferma Cancellazione", f"Sei sicuro di voler cancellare questa ROI per la categoria '{category_name}'?"):
            del rule["rois"][roi_index]
            self.save_and_refresh()

    def prompt_and_save_roi(self, roi_coords):
        # ... (codice quasi identico, ma la logica di salvataggio cambia)
        def save():
            selected_category = category_var.get()
            if not selected_category: return
            for rule in self.config["classification_rules"]:
                if rule["category_name"] == selected_category:
                    # Aggiunge la nuova ROI alla lista invece di sovrascrivere
                    rule.setdefault("rois", []).append(roi_coords)
                    break
            self.save_and_refresh()
            dialog.destroy()
        # ...
        categories = [rule["category_name"] for rule in self.config.get("classification_rules", [])]
        dialog = tk.Toplevel(self.root)
        dialog.title("Aggiungi ROI")
        ttk.Label(dialog, text="Associa nuova ROI alla categoria:").pack(pady=5)
        category_var = tk.StringVar()
        category_combo = ttk.Combobox(dialog, textvariable=category_var, values=categories, state='readonly')
        category_combo.pack(pady=10)
        if categories: category_combo.set(categories[0])
        ttk.Button(dialog, text="Aggiungi e Salva", command=save).pack(pady=5)


    def save_and_refresh(self):
        try:
            config_manager.save_config(self.config)
            with open(SIGNAL_FILE, "w") as f: f.write("update")
            self.render_page(self.current_page_index)
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile salvare la configurazione: {e}")

    # Metodi di navigazione (prev_page, next_page, update_nav_controls) rimangono quasi invariati
    def prev_page(self):
        if self.current_page_index > 0: self.render_page(self.current_page_index - 1)
    def next_page(self):
        if self.pdf_doc and self.current_page_index < self.pdf_doc.page_count - 1: self.render_page(self.current_page_index + 1)
    def update_nav_controls(self):
        if not self.pdf_doc: return
        total_pages = self.pdf_doc.page_count
        self.page_label.config(text=f"Pagina {self.current_page_index + 1} / {total_pages}")

if __name__ == "__main__":
    root = tk.Tk()
    app = ROIDrawingApp(root)
    root.mainloop()
