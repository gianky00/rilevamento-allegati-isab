import tkinter as tk
from tkinter import ttk, filedialog, simpledialog, messagebox
import pymupdf as fitz
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
        self.roi_item_map = {}

        # --- Layout GUI ---
        control_frame = ttk.Frame(self.root)
        control_frame.pack(pady=5, padx=10, fill=tk.X)
        ttk.Button(control_frame, text="Apri PDF di Esempio", command=self.open_pdf).pack(side=tk.LEFT, padx=5)

        self.nav_frame = ttk.Frame(control_frame)
        self.prev_page_button = ttk.Button(self.nav_frame, text="<< Pagina Prec.", command=self.prev_page)
        self.prev_page_button.pack(side=tk.LEFT)
        self.page_label = ttk.Label(self.nav_frame, text="N/A", anchor=tk.CENTER, width=20)
        self.page_label.pack(side=tk.LEFT, padx=10)
        self.next_page_button = ttk.Button(self.nav_frame, text="Pagina Succ. >>", command=self.next_page)
        self.next_page_button.pack(side=tk.LEFT)

        self.delete_mode_button = ttk.Checkbutton(control_frame, text="Modalità Cancellazione ROI", variable=self.delete_mode, command=self.toggle_delete_mode)
        self.delete_mode_button.pack(side=tk.RIGHT, padx=20)

        canvas_frame = ttk.Frame(self.root)
        canvas_frame.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)
        self.canvas = tk.Canvas(canvas_frame, bg="gray", cursor="crosshair")
        self.h_scroll = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.v_scroll = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.canvas.config(xscrollcommand=self.h_scroll.set, yscrollcommand=self.v_scroll.set)
        self.h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        self.v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)

        self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)
        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)

        self.rect = None
        self.start_x = None
        self.start_y = None

    def toggle_delete_mode(self):
        self.canvas.config(cursor="pirate" if self.delete_mode.get() else "crosshair")

    def on_mouse_wheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def open_pdf(self):
        filepath = filedialog.askopenfilename(title="Seleziona PDF", filetypes=[("PDF Files", "*.pdf")])
        if not filepath: return
        try:
            self.pdf_doc = fitz.open(filepath)
            if self.pdf_doc.page_count > 0:
                self.current_page_index = 0
                self.nav_frame.pack(side=tk.LEFT, padx=20)
                self.render_page(self.current_page_index)
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile aprire il PDF: {e}")

    def render_page(self, page_index):
        if not self.pdf_doc or not (0 <= page_index < self.pdf_doc.page_count):
            return

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
        self.canvas.delete("roi")
        self.roi_item_map.clear()  # Pulisce la mappa prima di ridisegnare
        factor = 300 / 72
        for rule_index, rule in enumerate(self.config.get("classification_rules", [])):
            category_name = rule.get("category_name", "N/A")
            color = rule.get("color", "#FF0000")
            for roi_index, roi in enumerate(rule.get("rois", [])):
                if not all(isinstance(c, int) for c in roi) or len(roi) != 4: continue
                x0, y0, x1, y1 = [c * factor for c in roi]

                # Creazione degli elementi grafici
                rect_id = self.canvas.create_rectangle(x0, y0, x1, y1, outline=color, width=2, dash=(5, 3), tags="roi", fill="", stipple="gray12")
                text_id = self.canvas.create_text(x0 + 5, y0 + 5, text=category_name, fill=color, font=("Arial", 10, "bold"), anchor="nw", tags="roi")

                # Popolamento della mappa
                roi_info = {"rule_index": rule_index, "roi_index": roi_index}
                self.roi_item_map[rect_id] = roi_info
                self.roi_item_map[text_id] = roi_info

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
            factor = 72 / 300
            end_x, end_y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
            x0, y0, x1, y1 = min(self.start_x, end_x), min(self.start_y, end_y), max(self.start_x, end_x), max(self.start_y, end_y)
            roi_pdf_coords = [int(c * factor) for c in [x0, y0, x1, y1]]
            self.prompt_and_save_roi(roi_pdf_coords)
            self.canvas.delete(self.rect)
            self.rect = None

    def handle_delete_click(self, event):
        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        item_ids = self.canvas.find_overlapping(x, y, x, y)
        if not item_ids: return

        for item_id in reversed(item_ids):
            if item_id in self.roi_item_map:
                roi_info = self.roi_item_map[item_id]
                rule_index = roi_info["rule_index"]
                roi_index = roi_info["roi_index"]

                if rule_index < len(self.config["classification_rules"]) and \
                   roi_index < len(self.config["classification_rules"][rule_index].get("rois", [])):

                    rule = self.config["classification_rules"][rule_index]
                    category_name = rule.get("category_name", "N/A")

                    if messagebox.askyesno("Conferma Cancellazione", f"Sei sicuro di voler cancellare questa ROI per la categoria '{category_name}'?"):
                        # Rimuovi il ROI dalla configurazione
                        del rule["rois"][roi_index]

                        # Aggiorna gli indici nella mappa per gli elementi successivi
                        # Questa è la parte complessa ma cruciale per la consistenza
                        for item, info in list(self.roi_item_map.items()):
                            if info["rule_index"] == rule_index and info["roi_index"] > roi_index:
                                self.roi_item_map[item]["roi_index"] -= 1

                        self.save_and_refresh()
                        return # Esci dopo una cancellazione riuscita

    def prompt_and_save_roi(self, roi_coords):
        categories = [rule["category_name"] for rule in self.config.get("classification_rules", [])]
        dialog = tk.Toplevel(self.root)
        dialog.title("Aggiungi ROI")
        ttk.Label(dialog, text="Associa nuova ROI alla categoria:").pack(pady=5)
        category_var = tk.StringVar()
        category_combo = ttk.Combobox(dialog, textvariable=category_var, values=categories, state='readonly')
        category_combo.pack(pady=10)
        if categories: category_combo.set(categories[0])

        def save():
            selected_category = category_var.get()
            if not selected_category: return
            for rule in self.config["classification_rules"]:
                if rule["category_name"] == selected_category:
                    rule.setdefault("rois", []).append(roi_coords)
                    break
            self.save_and_refresh()
            dialog.destroy()

        ttk.Button(dialog, text="Aggiungi e Salva", command=save).pack(pady=5)

    def save_and_refresh(self):
        try:
            config_manager.save_config(self.config)
            with open(SIGNAL_FILE, "w") as f: f.write("update")
            self.render_page(self.current_page_index)
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile salvare la configurazione: {e}")

    def prev_page(self):
        self.render_page(self.current_page_index - 1)

    def next_page(self):
        self.render_page(self.current_page_index + 1)

    def update_nav_controls(self):
        if not self.pdf_doc: return
        total_pages = self.pdf_doc.page_count
        self.page_label.config(text=f"Pagina {self.current_page_index + 1} / {total_pages}")
        self.prev_page_button.config(state=tk.NORMAL if self.current_page_index > 0 else tk.DISABLED)
        self.next_page_button.config(state=tk.NORMAL if self.current_page_index < total_pages - 1 else tk.DISABLED)

if __name__ == "__main__":
    root = tk.Tk()
    app = ROIDrawingApp(root)
    root.mainloop()
