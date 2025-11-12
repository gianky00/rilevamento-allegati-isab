import tkinter as tk
from tkinter import ttk, filedialog, simpledialog, messagebox
import pymupdf as fitz  # PyMuPDF
from PIL import Image, ImageTk
import os
import config_manager

# Il file usato come segnale per l'aggiornamento in tempo reale
SIGNAL_FILE = ".update_signal"

class ROIDrawingApp:
    """
    Utility per disegnare ROI su un PDF, con colori persistenti, scrolling del mouse
    e aggiornamento in tempo reale dell'applicazione principale.
    """
    def __init__(self, root):
        self.root = root
        self.root.title("Utility di Rilevamento ROI")
        self.root.geometry("1200x900")

        self.pdf_doc = None
        self.tk_image = None
        self.current_page_index = 0
        self.config = config_manager.load_config()

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

        canvas_frame = ttk.Frame(self.root)
        canvas_frame.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)
        self.canvas = tk.Canvas(canvas_frame, bg="gray")
        self.h_scroll = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.v_scroll = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.canvas.config(xscrollcommand=self.h_scroll.set, yscrollcommand=self.v_scroll.set)
        self.h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        self.v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)

        self.rect = None
        self.start_x = None
        self.start_y = None

        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)
        # Binding per lo scroll con la rotellina del mouse
        self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)

    def on_mouse_wheel(self, event):
        """Gestisce lo scrolling verticale con la rotellina del mouse."""
        # Su Windows, event.delta è solitamente un multiplo di 120
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def open_pdf(self):
        filepath = filedialog.askopenfilename(title="Seleziona un PDF di Esempio", filetypes=[("PDF Files", "*.pdf")])
        if not filepath: return
        try:
            self.pdf_doc = fitz.open(filepath)
            if self.pdf_doc.page_count > 0:
                self.current_page_index = 0
                self.nav_frame.pack(side=tk.LEFT, padx=20)
                self.render_page(self.current_page_index)
            else:
                messagebox.showwarning("PDF Vuoto", "Il documento non ha pagine.")
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile aprire il PDF: {e}")

    def render_page(self, page_index):
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
        self.config = config_manager.load_config()
        factor = 300 / 72
        for rule in self.config.get("classification_rules", []):
            roi = rule.get("roi")
            if not all(isinstance(c, int) and c >= 0 for c in roi) or len(roi) != 4 or sum(roi) == 0:
                continue

            color = rule.get("color", "#FF0000") # Rosso di default
            category_name = rule.get("category_name", "N/A")
            x0, y0, x1, y1 = [c * factor for c in roi]

            self.canvas.create_rectangle(x0, y0, x1, y1, outline=color, width=2, dash=(5, 3))
            self.canvas.create_text(x0 + 5, y0 + 5, text=category_name, fill=color, font=("Arial", 10, "bold"), anchor="nw")

    def update_nav_controls(self):
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
        # Rettangolo di selezione nero e tratteggiato
        self.rect = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline='black', width=2, dash=(5, 3))

    def on_mouse_drag(self, event):
        cur_x, cur_y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        self.canvas.coords(self.rect, self.start_x, self.start_y, cur_x, cur_y)

    def on_button_release(self, event):
        end_x, end_y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        x0, y0 = min(self.start_x, end_x), min(self.start_y, end_y)
        x1, y1 = max(self.start_x, end_x), max(self.start_y, end_y)
        factor = 72 / 300
        roi_pdf_coords = [int(c * factor) for c in [x0, y0, x1, y1]]
        self.prompt_and_save_roi(roi_pdf_coords)
        self.canvas.delete(self.rect)
        self.rect = None

    def prompt_and_save_roi(self, roi_coords):
        self.config = config_manager.load_config()
        categories = [rule["category_name"] for rule in self.config.get("classification_rules", [])]
        if not categories:
            messagebox.showwarning("Nessuna Categoria", "Definisci almeno una categoria nell'app principale.")
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
                with open(SIGNAL_FILE, "w") as f:
                    f.write("update")
                messagebox.showinfo("Successo", f"ROI per '{selected_category}' salvata.", parent=self.root)
                dialog.destroy()
                self.render_page(self.current_page_index)
            except Exception as e:
                messagebox.showerror("Errore", f"Impossibile salvare: {e}", parent=dialog)

        ttk.Button(dialog, text="Salva ROI", command=save).pack(pady=10)

if __name__ == "__main__":
    root = tk.Tk()
    app = ROIDrawingApp(root)
    root.mainloop()
