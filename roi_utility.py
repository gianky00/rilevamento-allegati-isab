"""
Intelleo PDF Splitter - Utility ROI
Gestisce la definizione delle aree ROI per l'OCR.
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pymupdf as fitz
from PIL import Image, ImageTk
import os
import config_manager
import math

SIGNAL_FILE = ".update_signal"

# ============================================================================
# COSTANTI STILE - TEMA CHIARO PROFESSIONALE
# ============================================================================
COLORS = {
    'bg_primary': '#FFFFFF',
    'bg_secondary': '#F8F9FA',
    'bg_tertiary': '#E9ECEF',
    'accent': '#0D6EFD',
    'accent_hover': '#0B5ED7',
    'success': '#198754',
    'warning': '#FFC107',
    'danger': '#DC3545',
    'text_primary': '#212529',
    'text_secondary': '#6C757D',
    'text_muted': '#ADB5BD',
    'border': '#DEE2E6',
}

FONTS = {
    'heading': ('Segoe UI', 14, 'bold'),
    'subheading': ('Segoe UI', 11, 'bold'),
    'body': ('Segoe UI', 10),
    'body_bold': ('Segoe UI', 10, 'bold'),
    'small': ('Segoe UI', 9),
}


class ROIDrawingApp:
    """Applicazione per la gestione delle aree ROI."""

    def __init__(self, root):
        self.root = root
        self.root.title("🎯 Intelleo - Utility Gestione ROI")
        self.root.geometry("1300x900")
        self.root.configure(bg=COLORS['bg_primary'])
        self.root.state('zoomed')

        # Variabili di stato
        self.pdf_doc = None
        self.tk_image = None
        self.current_page_index = 0
        self.config = config_manager.load_config()
        self.delete_mode = tk.BooleanVar(value=False)
        self.roi_item_map = {}
        self.rect = None
        self.start_x = None
        self.start_y = None
        self.zoom_level = 1.0

        # Setup stili e UI
        self._setup_styles()
        self._create_ui()
        self._bind_events()

    def _setup_styles(self):
        """Configura gli stili ttk."""
        style = ttk.Style()
        style.theme_use('clam')

        style.configure('TFrame', background=COLORS['bg_primary'])
        style.configure('TLabel', background=COLORS['bg_primary'], 
                       font=FONTS['body'], foreground=COLORS['text_primary'])
        style.configure('Header.TLabel', font=FONTS['heading'], foreground=COLORS['accent'])
        style.configure('Muted.TLabel', font=FONTS['small'], foreground=COLORS['text_secondary'])
        
        style.configure('TButton', font=FONTS['body'], padding=[12, 6])
        style.configure('Accent.TButton', font=FONTS['body_bold'])
        
        style.configure('TLabelframe', background=COLORS['bg_primary'])
        style.configure('TLabelframe.Label', font=FONTS['subheading'], 
                       foreground=COLORS['text_primary'], background=COLORS['bg_primary'])

        style.configure('TCheckbutton', background=COLORS['bg_primary'], font=FONTS['body'])

    def _create_ui(self):
        """Crea l'interfaccia utente."""
        # Container principale
        main_container = ttk.Frame(self.root, padding=15)
        main_container.pack(fill='both', expand=True)

        # Header
        header_frame = ttk.Frame(main_container)
        header_frame.pack(fill='x', pady=(0, 15))

        ttk.Label(header_frame, text="Utility Gestione ROI", 
                 style='Header.TLabel').pack(side='left')

        # Toolbar
        toolbar = ttk.LabelFrame(main_container, text=" Strumenti ", padding=10)
        toolbar.pack(fill='x', pady=(0, 15))

        # Bottoni toolbar
        btn_frame = ttk.Frame(toolbar)
        btn_frame.pack(fill='x')

        ttk.Button(btn_frame, text="Apri PDF di Esempio", 
                  command=self.open_pdf).pack(side='left', padx=5)

        ttk.Separator(btn_frame, orient='vertical').pack(side='left', fill='y', padx=15)

        # Navigazione pagine
        self.nav_frame = ttk.Frame(btn_frame)
        
        self.prev_page_button = ttk.Button(self.nav_frame, text="<< Pagina Precedente", 
                                          command=self.prev_page)
        self.prev_page_button.pack(side='left', padx=3)

        self.page_label = ttk.Label(self.nav_frame, text="Nessun PDF caricato", 
                                   font=FONTS['body_bold'], width=25, anchor='center')
        self.page_label.pack(side='left', padx=15)

        self.next_page_button = ttk.Button(self.nav_frame, text="Pagina Successiva >>", 
                                          command=self.next_page)
        self.next_page_button.pack(side='left', padx=3)

        ttk.Separator(btn_frame, orient='vertical').pack(side='left', fill='y', padx=15)

        # Zoom controls
        zoom_frame = ttk.Frame(btn_frame)
        zoom_frame.pack(side='left', padx=10)
        
        ttk.Label(zoom_frame, text="Zoom:", font=FONTS['body_bold']).pack(side='left', padx=5)
        ttk.Button(zoom_frame, text="-", width=3, command=self.zoom_out).pack(side='left', padx=2)
        self.zoom_label = ttk.Label(zoom_frame, text="100%", width=6, anchor='center')
        self.zoom_label.pack(side='left', padx=5)
        ttk.Button(zoom_frame, text="+", width=3, command=self.zoom_in).pack(side='left', padx=2)
        ttk.Button(zoom_frame, text="Reset", width=5, command=self.zoom_reset).pack(side='left', padx=2)

        ttk.Separator(btn_frame, orient='vertical').pack(side='left', fill='y', padx=15)

        # Modalita' cancellazione
        self.delete_mode_btn = ttk.Checkbutton(btn_frame, text="Modalita' Cancellazione ROI", 
                                               variable=self.delete_mode, 
                                               command=self.toggle_delete_mode)
        self.delete_mode_btn.pack(side='left', padx=10)

        # Indicatore modalita'
        self.mode_indicator = ttk.Label(btn_frame, text="[DISEGNO] Modalita' attiva", 
                                        foreground=COLORS['success'], font=FONTS['body_bold'])
        self.mode_indicator.pack(side='right', padx=15)

        # Area Canvas con sidebar
        content_frame = ttk.Frame(main_container)
        content_frame.pack(fill='both', expand=True)
        content_frame.columnconfigure(0, weight=1)
        content_frame.rowconfigure(0, weight=1)

        # Canvas Frame
        canvas_container = ttk.LabelFrame(content_frame, text=" Area di Lavoro ", padding=10)
        canvas_container.grid(row=0, column=0, sticky='nsew', padx=(0, 10))

        self.canvas = tk.Canvas(canvas_container, bg=COLORS['bg_tertiary'], 
                               cursor="crosshair", highlightthickness=1,
                               highlightbackground=COLORS['border'])
        self.h_scroll = ttk.Scrollbar(canvas_container, orient='horizontal', 
                                      command=self.canvas.xview)
        self.v_scroll = ttk.Scrollbar(canvas_container, orient='vertical', 
                                      command=self.canvas.yview)
        
        self.canvas.config(xscrollcommand=self.h_scroll.set, yscrollcommand=self.v_scroll.set)
        
        self.h_scroll.pack(side='bottom', fill='x')
        self.v_scroll.pack(side='right', fill='y')
        self.canvas.pack(side='left', expand=True, fill='both')

        # Sidebar con regole
        sidebar = ttk.LabelFrame(content_frame, text=" Regole Attive ", padding=10, width=280)
        sidebar.grid(row=0, column=1, sticky='nsew')
        sidebar.grid_propagate(False)

        # Lista regole
        self.rules_listbox = tk.Listbox(sidebar, font=FONTS['body'], 
                                        bg=COLORS['bg_secondary'],
                                        selectbackground=COLORS['accent'],
                                        selectforeground='white',
                                        relief='flat', highlightthickness=1,
                                        highlightbackground=COLORS['border'])
        self.rules_listbox.pack(fill='both', expand=True, pady=(0, 10))
        self._update_rules_list()

        ttk.Button(sidebar, text="Aggiorna Lista", 
                  command=self._update_rules_list).pack(fill='x')

        # Status bar
        self.status_bar = ttk.Label(main_container, text="[INFO] Carica un PDF per iniziare a definire le aree ROI",
                                   style='Muted.TLabel', anchor='w')
        self.status_bar.pack(fill='x', pady=(10, 0))

        # Istruzioni
        help_frame = ttk.Frame(main_container)
        help_frame.pack(fill='x', pady=(5, 0))
        
        ttk.Label(help_frame, 
                 text="[AIUTO] Disegna un rettangolo sul PDF per definire una nuova ROI | "
                      "Frecce <- -> per navigare | Rotella mouse per zoom | "
                      "Attiva 'Cancellazione' per rimuovere ROI esistenti",
                 style='Muted.TLabel').pack()

    def _bind_events(self):
        """Collega gli eventi."""
        self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)
        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)
        self.canvas.bind("<Motion>", self.on_mouse_motion)

        # Pan con Ctrl+Click
        self.canvas.bind("<Control-ButtonPress-1>", self.start_pan)
        self.canvas.bind("<Control-B1-Motion>", self.pan)

        self.root.bind("<Left>", lambda e: self.prev_page())
        self.root.bind("<Right>", lambda e: self.next_page())
        self.root.bind("<plus>", lambda e: self.zoom_in())
        self.root.bind("<minus>", lambda e: self.zoom_out())
        self.root.bind("<Key-0>", lambda e: self.zoom_reset())

    def _update_rules_list(self):
        """Aggiorna la lista delle regole nella sidebar."""
        self.config = config_manager.load_config()
        self.rules_listbox.delete(0, 'end')
        
        for rule in self.config.get("classification_rules", []):
            name = rule.get("category_name", "N/A")
            roi_count = len(rule.get("rois", []))
            color = rule.get("color", "#FFFFFF")
            self.rules_listbox.insert('end', f"  {name} ({roi_count} ROI)")

    def toggle_delete_mode(self):
        """Attiva/disattiva la modalita' cancellazione."""
        if self.delete_mode.get():
            self.canvas.config(cursor="X_cursor")
            self.mode_indicator.config(text="[CANCELLA] Modalita' attiva", foreground=COLORS['danger'])
            self.status_bar.config(text="[!] Modalita' Cancellazione: Clicca su una ROI per eliminarla")
        else:
            self.canvas.config(cursor="crosshair")
            self.mode_indicator.config(text="[DISEGNO] Modalita' attiva", foreground=COLORS['success'])
            self.status_bar.config(text="[OK] Modalita' Disegno: Trascina per creare una nuova ROI")

    def on_mouse_motion(self, event):
        """Mostra le coordinate del mouse."""
        if self.pdf_doc:
            x = self.canvas.canvasx(event.x)
            y = self.canvas.canvasy(event.y)
            factor = 72 / (150 * self.zoom_level)
            pdf_x = int(x * factor)
            pdf_y = int(y * factor)
            coord_text = f"Coordinate PDF: ({pdf_x}, {pdf_y})"
            if not self.delete_mode.get():
                self.status_bar.config(text=f"[DISEGNO] Modalita' attiva | {coord_text}")

    def zoom_in(self):
        """Aumenta lo zoom."""
        self.zoom_level = min(4.0, self.zoom_level * 1.2)
        self.zoom_label.config(text=f"{int(self.zoom_level * 100)}%")
        if self.pdf_doc:
            self.render_page(self.current_page_index)

    def zoom_out(self):
        """Diminuisce lo zoom."""
        self.zoom_level = max(0.25, self.zoom_level / 1.2)
        self.zoom_label.config(text=f"{int(self.zoom_level * 100)}%")
        if self.pdf_doc:
            self.render_page(self.current_page_index)

    def zoom_reset(self):
        """Resetta lo zoom."""
        self.zoom_level = 1.0
        self.zoom_label.config(text="100%")
        if self.pdf_doc:
            self.render_page(self.current_page_index)

    def on_mouse_wheel(self, event):
        """Gestisce lo zoom con la rotella."""
        if event.state & 0x0004:  # Ctrl pressed
            if event.delta > 0:
                self.zoom_in()
            else:
                self.zoom_out()
        else:
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def open_pdf(self):
        """Apre un file PDF."""
        filepath = filedialog.askopenfilename(
            title="Seleziona un PDF di esempio",
            filetypes=[("PDF Files", "*.pdf")])
        
        if not filepath:
            return

        try:
            self.pdf_doc = fitz.open(filepath)
            
            if self.pdf_doc.page_count > 0:
                self.current_page_index = 0
                self.nav_frame.pack(side='left', padx=10)
                self.zoom_level = 1.0
                self.zoom_label.config(text="100%")
                self.render_page(self.current_page_index)
                self.status_bar.config(
                    text=f"[OK] PDF caricato: {os.path.basename(filepath)} "
                         f"({self.pdf_doc.page_count} pagine)")
            else:
                messagebox.showwarning("Attenzione", 
                                      "Il PDF selezionato non contiene pagine.")
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile aprire il PDF:\n{e}")

    def render_page(self, page_index):
        """Renderizza una pagina del PDF."""
        if not self.pdf_doc or not (0 <= page_index < self.pdf_doc.page_count):
            return

        self.current_page_index = page_index
        page = self.pdf_doc[page_index]
        
        # Calcola DPI in base allo zoom
        dpi = int(150 * self.zoom_level)
        pix = page.get_pixmap(dpi=dpi)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        self.tk_image = ImageTk.PhotoImage(img)

        self.canvas.delete("all")
        self.canvas.config(scrollregion=(0, 0, pix.width, pix.height))
        self.canvas.create_image(0, 0, anchor='nw', image=self.tk_image)

        self.draw_existing_rois()
        self.update_nav_controls()

    def draw_existing_rois(self):
        """Disegna le ROI esistenti."""
        self.config = config_manager.load_config()
        self.canvas.delete("roi")
        self.roi_item_map.clear()
        
        factor = (150 * self.zoom_level) / 72

        for rule_index, rule in enumerate(self.config.get("classification_rules", [])):
            category_name = rule.get("category_name", "N/A")
            color = rule.get("color", "#FF0000")

            for roi_index, roi in enumerate(rule.get("rois", [])):
                if not all(isinstance(c, int) for c in roi) or len(roi) != 4:
                    continue

                x0, y0, x1, y1 = [c * factor for c in roi]

                # Rettangolo ROI con stile migliorato
                rect_id = self.canvas.create_rectangle(
                    x0, y0, x1, y1,
                    outline=color, width=3, activewidth=5,
                    dash=(8, 4), tags="roi",
                    fill="", stipple="gray25"
                )

                # Etichetta categoria con sfondo
                text_bg = self.canvas.create_rectangle(
                    x0, y0, x0 + len(category_name) * 8 + 10, y0 + 18,
                    fill=color, outline="", tags="roi"
                )
                
                # Calcola contrasto testo
                h = color.lstrip('#')
                try:
                    rgb = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
                    brightness = (rgb[0] * 299 + rgb[1] * 587 + rgb[2] * 114) / 1000
                    text_color = "white" if brightness < 128 else "black"
                except:
                    text_color = "white"

                text_id = self.canvas.create_text(
                    x0 + 5, y0 + 9,
                    text=category_name, fill=text_color,
                    font=('Segoe UI', 9, 'bold'), anchor="w", tags="roi"
                )

                # Mappa per cancellazione
                roi_info = {"rule_index": rule_index, "roi_index": roi_index}
                self.roi_item_map[rect_id] = roi_info
                self.roi_item_map[text_id] = roi_info
                self.roi_item_map[text_bg] = roi_info

    def start_pan(self, event):
        """Inizia il panning."""
        self.canvas.scan_mark(event.x, event.y)

    def pan(self, event):
        """Esegue il panning."""
        self.canvas.scan_dragto(event.x, event.y, gain=1)

    def on_button_press(self, event):
        """Gestisce il click del mouse."""
        # Se Ctrl e' premuto, stiamo facendo panning, ignora disegno
        if event.state & 0x0004:
            return

        if self.delete_mode.get():
            self.handle_delete_click(event)
        else:
            self.start_x = self.canvas.canvasx(event.x)
            self.start_y = self.canvas.canvasy(event.y)
            if self.rect:
                self.canvas.delete(self.rect)
            self.rect = self.canvas.create_rectangle(
                self.start_x, self.start_y, self.start_x, self.start_y,
                outline=COLORS['accent'], width=2, dash=(5, 3)
            )

    def on_mouse_drag(self, event):
        """Gestisce il trascinamento del mouse."""
        # Se Ctrl e' premuto, ignora
        if event.state & 0x0004:
            return

        if not self.delete_mode.get() and self.rect:
            cur_x = self.canvas.canvasx(event.x)
            cur_y = self.canvas.canvasy(event.y)
            self.canvas.coords(self.rect, self.start_x, self.start_y, cur_x, cur_y)

    def on_button_release(self, event):
        """Gestisce il rilascio del mouse."""
        if not self.delete_mode.get():
            if self.start_x is None or self.start_y is None:
                return

            end_x = self.canvas.canvasx(event.x)
            end_y = self.canvas.canvasy(event.y)

            # Controlla dimensione minima
            dist = math.hypot(end_x - self.start_x, end_y - self.start_y)
            if dist < 10:
                if self.rect:
                    self.canvas.delete(self.rect)
                    self.rect = None
                return

            # Converti coordinate
            factor = 72 / (150 * self.zoom_level)
            x0, y0 = min(self.start_x, end_x), min(self.start_y, end_y)
            x1, y1 = max(self.start_x, end_x), max(self.start_y, end_y)
            roi_pdf_coords = [int(c * factor) for c in [x0, y0, x1, y1]]

            self.prompt_and_save_roi(roi_pdf_coords)
            
            if self.rect:
                self.canvas.delete(self.rect)
                self.rect = None

    def handle_delete_click(self, event):
        """Gestisce il click in modalita' cancellazione."""
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        item_ids = self.canvas.find_overlapping(x, y, x, y)

        if not item_ids:
            return

        for item_id in reversed(item_ids):
            if item_id in self.roi_item_map:
                roi_info = self.roi_item_map[item_id]
                rule_index = roi_info["rule_index"]
                roi_index = roi_info["roi_index"]

                if (rule_index < len(self.config["classification_rules"]) and
                    roi_index < len(self.config["classification_rules"][rule_index].get("rois", []))):

                    rule = self.config["classification_rules"][rule_index]
                    category_name = rule.get("category_name", "N/A")

                    if messagebox.askyesno(
                        "Conferma Cancellazione",
                        f"Eliminare questa ROI per la categoria '{category_name}'?",
                        parent=self.root):
                        
                        del rule["rois"][roi_index]
                        self.save_and_refresh()
                        self.status_bar.config(text=f"[OK] ROI eliminata da '{category_name}'")
                        return

    def prompt_and_save_roi(self, roi_coords):
        """Mostra il dialog per salvare la ROI."""
        categories = [rule["category_name"] 
                     for rule in self.config.get("classification_rules", [])]

        if not categories:
            messagebox.showwarning(
                "Nessuna Categoria",
                "Non ci sono categorie definite.\nCrea prima una categoria nell'applicazione principale.",
                parent=self.root)
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("Salva Nuova ROI")
        dialog.configure(bg=COLORS['bg_primary'])
        dialog.geometry("550x250")  # Aumentato per visibilità bottoni
        dialog.resizable(True, True)
        dialog.transient(self.root)
        dialog.grab_set()

        # Centra il dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() - dialog.winfo_width()) // 2
        y = (dialog.winfo_screenheight() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")

        main_frame = ttk.Frame(dialog, padding=20)
        main_frame.pack(fill='both', expand=True)

        ttk.Label(main_frame, text="Associa ROI alla categoria:",
                 font=FONTS['subheading']).pack(pady=(0, 15))

        category_var = tk.StringVar()
        category_combo = ttk.Combobox(main_frame, textvariable=category_var,
                                      values=categories, state='readonly',
                                      font=FONTS['body'], width=35)
        category_combo.pack(pady=10)
        if categories:
            category_combo.set(categories[0])

        # Info coordinate
        coords_text = f"Coordinate: ({roi_coords[0]}, {roi_coords[1]}) -> ({roi_coords[2]}, {roi_coords[3]})"
        ttk.Label(main_frame, text=coords_text, style='Muted.TLabel').pack(pady=10)

        def save():
            selected_category = category_var.get()
            if not selected_category:
                return
            
            for rule in self.config["classification_rules"]:
                if rule["category_name"] == selected_category:
                    rule.setdefault("rois", []).append(roi_coords)
                    break
            
            self.save_and_refresh()
            self.status_bar.config(text=f"[OK] ROI aggiunta a '{selected_category}'")
            dialog.destroy()

        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=15)

        ttk.Button(btn_frame, text="Salva ROI", command=save).pack(side='left', padx=10)
        ttk.Button(btn_frame, text="Annulla", command=dialog.destroy).pack(side='left', padx=10)

    def save_and_refresh(self):
        """Salva la configurazione e aggiorna la vista."""
        try:
            config_manager.save_config(self.config)
            
            # Crea il file segnale per l'app principale
            with open(SIGNAL_FILE, "w") as f:
                f.write("update")
            
            self.render_page(self.current_page_index)
            self._update_rules_list()
            
        except Exception as e:
            messagebox.showerror("Errore", 
                               f"Impossibile salvare la configurazione:\n{e}",
                               parent=self.root)

    def prev_page(self):
        """Va alla pagina precedente."""
        if self.current_page_index > 0:
            self.render_page(self.current_page_index - 1)

    def next_page(self):
        """Va alla pagina successiva."""
        if self.pdf_doc and self.current_page_index < self.pdf_doc.page_count - 1:
            self.render_page(self.current_page_index + 1)

    def update_nav_controls(self):
        """Aggiorna i controlli di navigazione."""
        if not self.pdf_doc:
            return
        
        total_pages = self.pdf_doc.page_count
        self.page_label.config(text=f"Pagina {self.current_page_index + 1} / {total_pages}")
        
        self.prev_page_button.config(
            state='normal' if self.current_page_index > 0 else 'disabled')
        self.next_page_button.config(
            state='normal' if self.current_page_index < total_pages - 1 else 'disabled')


def run_utility():
    """Entry point programmatico per l'utility."""
    print("+====================================================================+")
    print("|            INTELLEO - UTILITY GESTIONE ROI                         |")
    print("+====================================================================+")
    print("|  Usa questa utility per definire le aree di ricerca OCR.           |")
    print("|  Le modifiche verranno sincronizzate con l'app principale.         |")
    print("+====================================================================+")
    print()

    root = tk.Tk()
    app = ROIDrawingApp(root)
    root.mainloop()


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================
if __name__ == "__main__":
    run_utility()
