"""
Intelleo PDF Splitter - Applicazione principale
Gestisce la divisione di file PDF basata su regole OCR.
"""
# CRITICO: Inizializzare il logging PRIMA di tutto il resto
import app_logger
LOG_PATH = app_logger.initialize()

import logging
logger = logging.getLogger('MAIN')

# Ora importa il resto
try:
    logger.info("Importazione moduli tkinter...")
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox, scrolledtext, colorchooser, simpledialog
    logger.info("Importazione tkinterdnd2...")
    from tkinterdnd2 import DND_FILES, TkinterDnD
    logger.info("Importazione moduli applicazione...")
    import config_manager
    import pdf_processor
    import subprocess
    import os
    import sys
    import threading
    import queue
    import license_validator
    import license_updater
    import app_updater
    import version
    logger.info("Importazione PyMuPDF...")
    import pymupdf as fitz
    logger.info("Importazione PIL...")
    from PIL import Image, ImageTk
    import shutil
    from datetime import datetime
    logger.info("Tutti i moduli importati con successo")
except Exception as e:
    logger.critical(f"Errore durante l'importazione dei moduli: {e}", exc_info=True)
    raise

# Segnale per comunicazione tra utility ROI e app principale
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
    'card_shadow': '#CED4DA',
}

FONTS = {
    'heading': ('Segoe UI', 14, 'bold'),
    'subheading': ('Segoe UI', 11, 'bold'),
    'body': ('Segoe UI', 10),
    'body_bold': ('Segoe UI', 10, 'bold'),
    'small': ('Segoe UI', 9),
    'mono': ('Consolas', 9),
    'mono_bold': ('Consolas', 9, 'bold'),
}


class UnknownFilesReviewDialog(tk.Toplevel):
    """Dialog per la revisione e rinomina dei file sconosciuti."""
    
    def __init__(self, parent, review_tasks, odc, on_close_callback):
        super().__init__(parent)
        self.title("Revisione File Sconosciuti")
        self.state('zoomed')
        self.configure(bg=COLORS['bg_primary'])

        self.review_tasks = review_tasks
        self.odc = odc
        self.callback = on_close_callback
        self.current_index = 0
        self.current_page = 0
        self.zoom_level = 1.0
        self.image_ref = None
        self.current_doc = None
        self.completed_indices = set()

        self._setup_styles()
        self._create_widgets()
        self.load_current_file()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def _setup_styles(self):
        """Configura gli stili ttk per il dialog."""
        style = ttk.Style()
        style.configure('Review.TFrame', background=COLORS['bg_primary'])
        style.configure('Review.TLabel', background=COLORS['bg_primary'], 
                       font=FONTS['body'], foreground=COLORS['text_primary'])
        style.configure('ReviewHeader.TLabel', background=COLORS['bg_primary'],
                       font=FONTS['heading'], foreground=COLORS['accent'])

    def _create_widgets(self):
        """Crea i widget del dialog."""
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        # Area Preview
        self.preview_frame = ttk.Frame(self, style='Review.TFrame')
        self.preview_frame.grid(row=0, column=0, sticky='nsew', padx=10, pady=10)

        self.canvas = tk.Canvas(self.preview_frame, bg=COLORS['bg_tertiary'],
                               highlightthickness=1, highlightbackground=COLORS['border'])
        self.v_scroll = ttk.Scrollbar(self.preview_frame, orient='vertical', command=self.canvas.yview)
        self.h_scroll = ttk.Scrollbar(self.preview_frame, orient='horizontal', command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=self.v_scroll.set, xscrollcommand=self.h_scroll.set)

        self.v_scroll.pack(side='right', fill='y')
        self.h_scroll.pack(side='bottom', fill='x')
        self.canvas.pack(side='left', fill='both', expand=True)

        self.canvas.bind('<MouseWheel>', self.on_mouse_wheel)
        self.bind('<Left>', lambda e: self.go_prev_page())
        self.bind('<Right>', lambda e: self.go_next_page())
        self.bind('<Up>', lambda e: self.go_prev_file())
        self.bind('<Down>', lambda e: self.go_next_file())

        # Area Controlli
        controls_frame = ttk.LabelFrame(self, text=" Controlli ", padding=15)
        controls_frame.grid(row=1, column=0, sticky='ew', padx=10, pady=(0, 10))

        # Navigazione File
        nav_frame = ttk.Frame(controls_frame)
        nav_frame.pack(fill='x', pady=(0, 10))

        self.btn_prev_file = ttk.Button(nav_frame, text="<< File Precedente", command=self.go_prev_file)
        self.btn_prev_file.pack(side='left', padx=5)

        self.lbl_counter = ttk.Label(nav_frame, text="File 1 di N", font=FONTS['body_bold'])
        self.lbl_counter.pack(side='left', padx=20)

        self.btn_next_file = ttk.Button(nav_frame, text="File Successivo >>", command=self.go_next_file)
        self.btn_next_file.pack(side='left', padx=5)

        ttk.Separator(nav_frame, orient='vertical').pack(side='left', fill='y', padx=20)

        self.btn_prev_page = ttk.Button(nav_frame, text="< Pag. Prec.", command=self.go_prev_page)
        self.btn_prev_page.pack(side='left', padx=5)

        self.lbl_page_counter = ttk.Label(nav_frame, text="Pagina 1 di M")
        self.lbl_page_counter.pack(side='left', padx=10)

        self.btn_next_page = ttk.Button(nav_frame, text="Pag. Succ. >", command=self.go_next_page)
        self.btn_next_page.pack(side='left', padx=5)

        # Rinomina
        rename_frame = ttk.Frame(controls_frame)
        rename_frame.pack(fill='x', pady=10)

        ttk.Label(rename_frame, text="Suffisso Nome:", font=FONTS['body_bold']).pack(side='left', padx=5)

        self.var_suffix = tk.StringVar()
        self.var_suffix.trace("w", self.update_preview_label)
        self.entry_suffix = ttk.Entry(rename_frame, textvariable=self.var_suffix, width=35, font=FONTS['body'])
        self.entry_suffix.pack(side='left', padx=5)

        self.lbl_preview_name = ttk.Label(rename_frame, text="Anteprima: ...", foreground=COLORS['text_secondary'])
        self.lbl_preview_name.pack(side='left', padx=15)

        ttk.Button(rename_frame, text="[OK] Rinomina e Salva", command=self.rename_current).pack(side='right', padx=10)

        self.lbl_status = ttk.Label(controls_frame, text="", foreground=COLORS['accent'])
        self.lbl_status.pack(anchor='w', pady=(5, 0))

    def load_current_file(self):
        """Carica il file corrente per la revisione."""
        if not self.review_tasks:
            self.lbl_status.config(text="[INFO] Nessun file da revisionare.")
            return

        if self.current_doc:
            self.current_doc.close()
            self.current_doc = None

        task = self.review_tasks[self.current_index]
        file_path = task['unknown_path']
        filename = os.path.basename(file_path)

        self.current_page = 0
        self.lbl_counter.config(text=f"File {self.current_index + 1} di {len(self.review_tasks)}: {filename}")
        self.btn_prev_file.config(state='normal' if self.current_index > 0 else 'disabled')
        self.btn_next_file.config(state='normal' if self.current_index < len(self.review_tasks) - 1 else 'disabled')

        self.var_suffix.set("")
        self.update_preview_label()
        self.entry_suffix.focus_set()

        if self.current_index in self.completed_indices:
            self.lbl_status.config(text="[OK] File gia' completato.")
            self.entry_suffix.config(state='disabled')
        else:
            self.lbl_status.config(text="[...] File in attesa di revisione.")
            self.entry_suffix.config(state='normal')

        try:
            self.current_doc = fitz.open(file_path)
            self.update_page_controls()
            self.render_pdf()
        except Exception as e:
            self.canvas.delete("all")
            w = self.canvas.winfo_width() or 400
            h = self.canvas.winfo_height() or 300
            self.canvas.create_text(w//2, h//2, text=f"[ERRORE] Apertura PDF:\n{e}", 
                                   fill=COLORS['danger'], justify="center", font=FONTS['body'])
            self.lbl_page_counter.config(text="N/A")
            self.btn_prev_page.config(state='disabled')
            self.btn_next_page.config(state='disabled')

    def update_page_controls(self):
        """Aggiorna i controlli di navigazione pagina."""
        if not self.current_doc:
            return
        total_pages = self.current_doc.page_count
        self.lbl_page_counter.config(text=f"Pagina {self.current_page + 1} di {total_pages}")
        self.btn_prev_page.config(state='normal' if self.current_page > 0 else 'disabled')
        self.btn_next_page.config(state='normal' if self.current_page < total_pages - 1 else 'disabled')

    def render_pdf(self):
        """Renderizza la pagina PDF corrente."""
        if not self.current_doc:
            return

        try:
            if not (0 <= self.current_page < self.current_doc.page_count):
                return

            page = self.current_doc[self.current_page]
            canvas_w = self.canvas.winfo_width() or 800
            canvas_h = self.canvas.winfo_height() or 600

            page_rect = page.rect
            scale_w = (canvas_w - 40) / page_rect.width
            scale_h = (canvas_h - 40) / page_rect.height
            base_scale = min(scale_w, scale_h)
            final_scale = max(base_scale * self.zoom_level, 0.1)

            mat = fitz.Matrix(final_scale, final_scale)
            pix = page.get_pixmap(matrix=mat)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            self.image_ref = ImageTk.PhotoImage(img)
            self.canvas.delete("all")
            self.canvas.create_image(canvas_w//2, canvas_h//2, anchor='center', image=self.image_ref)
            self.canvas.config(scrollregion=self.canvas.bbox("all"))

        except Exception as e:
            self.canvas.delete("all")
            w = self.canvas.winfo_width() or 400
            h = self.canvas.winfo_height() or 300
            self.canvas.create_text(w//2, h//2, text=f"Anteprima non disponibile:\n{e}",
                                   fill=COLORS['danger'], justify="center")

    def on_mouse_wheel(self, event):
        """Gestisce lo zoom con la rotella del mouse."""
        scale_factor = 1.1 if event.delta > 0 else 0.9
        self.zoom_level = max(0.1, min(20.0, self.zoom_level * scale_factor))
        self.render_pdf()

    def go_prev_file(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.zoom_level = 1.0
            self.load_current_file()

    def go_next_file(self):
        if self.current_index < len(self.review_tasks) - 1:
            self.current_index += 1
            self.zoom_level = 1.0
            self.load_current_file()

    def go_prev_page(self):
        if self.current_doc and self.current_page > 0:
            self.current_page -= 1
            self.update_page_controls()
            self.render_pdf()

    def go_next_page(self):
        if self.current_doc and self.current_page < self.current_doc.page_count - 1:
            self.current_page += 1
            self.update_page_controls()
            self.render_pdf()

    def update_preview_label(self, *args):
        suffix = self.var_suffix.get()
        if suffix:
            self.lbl_preview_name.config(text=f"Anteprima: {self.odc}_{suffix}.pdf")
        else:
            self.lbl_preview_name.config(text="Anteprima: ...")

    def rename_current(self):
        """Rinomina il file corrente."""
        task = self.review_tasks[self.current_index]
        current_path = task['unknown_path']
        suffix = self.var_suffix.get().strip()

        if not suffix:
            messagebox.showwarning("Attenzione", "Inserire un suffisso per il nome file.", parent=self)
            return

        new_name = f"{self.odc}_{suffix}.pdf"
        dir_path = os.path.dirname(current_path)
        new_path = os.path.join(dir_path, new_name)

        if os.path.abspath(new_path) == os.path.abspath(current_path):
            messagebox.showinfo("Info", "Nessun cambiamento nel nome.", parent=self)
            return

        if os.path.exists(new_path):
            if not messagebox.askyesno("Sovrascrivi", f"Il file {new_name} esiste gia'. Sovrascrivere?", parent=self):
                return
            try:
                os.remove(new_path)
            except OSError as e:
                messagebox.showerror("Errore", f"Impossibile rimuovere file esistente: {e}", parent=self)
                return

        try:
            os.rename(current_path, new_path)
            self.completed_indices.add(self.current_index)
            task['unknown_path'] = new_path
            self.load_current_file()

            if self.current_index < len(self.review_tasks) - 1:
                self.go_next_file()
            else:
                messagebox.showinfo("Completato", "Ultimo file rinominato con successo!", parent=self)

        except Exception as e:
            messagebox.showerror("Errore Rinomina", str(e), parent=self)

    def on_close(self):
        """Gestisce la chiusura del dialog."""
        if self.current_doc:
            self.current_doc.close()
            self.current_doc = None

        restored_count = 0
        for i, task in enumerate(self.review_tasks):
            if i not in self.completed_indices:
                unknown_path = task['unknown_path']
                source_path = task['source_path']
                siblings = task['siblings']

                try:
                    for path_to_del in [unknown_path] + siblings:
                        if path_to_del and os.path.exists(path_to_del):
                            for attempt in range(3):
                                try:
                                    os.remove(path_to_del)
                                    break
                                except OSError:
                                    self.update()
                                    import time
                                    time.sleep(0.2)

                    if source_path and os.path.exists(source_path):
                        originali_dir = os.path.dirname(source_path)
                        base_dir = os.path.dirname(originali_dir)
                        filename = os.path.basename(source_path)
                        restore_path = os.path.join(base_dir, filename)

                        if os.path.abspath(source_path) != os.path.abspath(restore_path):
                            for attempt in range(3):
                                try:
                                    if os.path.exists(restore_path):
                                        os.replace(source_path, restore_path)
                                    else:
                                        shutil.move(source_path, restore_path)
                                    break
                                except OSError:
                                    self.update()
                                    import time
                                    time.sleep(0.2)

                    restored_count += 1
                except Exception as e:
                    logger.error(f"Errore ripristino file {task.get('unknown_path', '?')}: {e}")

        self.destroy()
        if self.callback:
            self.callback()


class MainApp:
    """Applicazione principale Intelleo PDF Splitter."""

    def __init__(self, root, auto_file_path=None):
        logger.info("Inizializzazione MainApp...")
        self.root = root
        self.root.title(f"Intelleo PDF Splitter v{version.__version__}")
        self.root.state('zoomed')
        self.root.configure(bg=COLORS['bg_primary'])

        # Inizializzazione variabili
        self.config = {}
        self.pdf_files = []
        self.log_queue = queue.Queue()
        self.processing_start_time = None
        self.files_processed_count = 0
        self.pages_processed_count = 0

        logger.info("Configurazione stili...")
        self._setup_styles()

        logger.info("Configurazione Drag & Drop...")
        self._setup_drag_drop()

        logger.info("Creazione interfaccia...")
        # Crea notebook principale
        self.notebook = ttk.Notebook(self.root, style='Main.TNotebook')
        self.notebook.pack(expand=True, fill='both', padx=15, pady=15)

        # Crea le tab
        self.dashboard_tab = ttk.Frame(self.notebook, style='Card.TFrame')
        self.processing_tab = ttk.Frame(self.notebook, style='Card.TFrame')
        self.config_tab = ttk.Frame(self.notebook, style='Card.TFrame')
        self.help_tab = ttk.Frame(self.notebook, style='Card.TFrame')

        self.notebook.add(self.dashboard_tab, text=' Dashboard ')
        self.notebook.add(self.processing_tab, text=' Elaborazione ')
        self.notebook.add(self.config_tab, text=' Configurazione ')
        self.notebook.add(self.help_tab, text=' Guida ')

        # Setup delle singole tab
        self._setup_dashboard_tab()
        self._setup_processing_tab()
        self._setup_config_tab()
        self._setup_help_tab()

        logger.info("Caricamento impostazioni...")
        self.load_settings()
        self._display_license_info()
        self.root.after(100, self._process_log_queue)
        self.root.after(150, self._check_for_updates)
        self.root.after(3000, lambda: app_updater.check_for_updates(silent=True))

        # Gestione avvio da CLI
        if auto_file_path and os.path.exists(auto_file_path):
            self.root.after(500, lambda: self._handle_cli_start(auto_file_path))

        logger.info("MainApp inizializzata con successo")

    def _setup_styles(self):
        """Configura tutti gli stili ttk per il tema chiaro."""
        style = ttk.Style()
        style.theme_use('clam')

        # Notebook principale
        style.configure('Main.TNotebook', background=COLORS['bg_primary'], borderwidth=0)
        style.configure('Main.TNotebook.Tab', font=FONTS['body_bold'], padding=[20, 10],
                       background=COLORS['bg_secondary'], foreground=COLORS['text_primary'])
        style.map('Main.TNotebook.Tab',
                 background=[('selected', COLORS['accent'])],
                 foreground=[('selected', COLORS['bg_primary'])])

        # Frame Card
        style.configure('Card.TFrame', background=COLORS['bg_primary'])
        style.configure('CardInner.TFrame', background=COLORS['bg_secondary'], relief='flat')

        # LabelFrame
        style.configure('TLabelframe', background=COLORS['bg_primary'], bordercolor=COLORS['border'])
        style.configure('TLabelframe.Label', font=FONTS['subheading'], 
                       foreground=COLORS['text_primary'], background=COLORS['bg_primary'])

        # Labels
        style.configure('TLabel', background=COLORS['bg_primary'], 
                       font=FONTS['body'], foreground=COLORS['text_primary'])
        style.configure('Header.TLabel', font=FONTS['heading'], foreground=COLORS['accent'])
        style.configure('Subheader.TLabel', font=FONTS['subheading'], foreground=COLORS['text_primary'])
        style.configure('Muted.TLabel', font=FONTS['small'], foreground=COLORS['text_secondary'])
        style.configure('Success.TLabel', foreground=COLORS['success'])
        style.configure('Warning.TLabel', foreground=COLORS['warning'])
        style.configure('Danger.TLabel', foreground=COLORS['danger'])

        # Buttons
        style.configure('TButton', font=FONTS['body'], padding=[15, 8])
        style.configure('Accent.TButton', font=FONTS['body_bold'])
        style.map('TButton',
                 background=[('active', COLORS['accent_hover'])],
                 foreground=[('active', COLORS['bg_primary'])])

        # Entry
        style.configure('TEntry', font=FONTS['body'], padding=8)

        # Treeview
        style.configure('Treeview', font=FONTS['body'], rowheight=30,
                       background=COLORS['bg_primary'], fieldbackground=COLORS['bg_primary'])
        style.configure('Treeview.Heading', font=FONTS['body_bold'],
                       background=COLORS['bg_secondary'], foreground=COLORS['text_primary'])
        style.map('Treeview', background=[('selected', COLORS['accent'])],
                 foreground=[('selected', COLORS['bg_primary'])])

        # Separator
        style.configure('TSeparator', background=COLORS['border'])

    def _setup_drag_drop(self):
        """Configura il drag & drop."""
        if hasattr(self.root, 'drop_target_register'):
            try:
                self.root.drop_target_register(DND_FILES)
                self.root.dnd_bind('<<Drop>>', self._on_drop)
            except Exception as e:
                logger.warning(f"Drag & Drop non disponibile: {e}")

    def _setup_dashboard_tab(self):
        """Configura la tab Dashboard."""
        main_frame = ttk.Frame(self.dashboard_tab, style='Card.TFrame', padding=20)
        main_frame.pack(fill='both', expand=True)

        # Header
        header_frame = ttk.Frame(main_frame, style='Card.TFrame')
        header_frame.pack(fill='x', pady=(0, 20))

        ttk.Label(header_frame, text="Dashboard", style='Header.TLabel').pack(side='left')
        
        self.clock_label = ttk.Label(header_frame, text="", style='Muted.TLabel')
        self.clock_label.pack(side='right')
        self._update_clock()

        # Cards Container
        cards_frame = ttk.Frame(main_frame, style='Card.TFrame')
        cards_frame.pack(fill='x', pady=10)
        cards_frame.columnconfigure((0, 1, 2, 3), weight=1, uniform='card')

        # Card: Stato Licenza
        self._create_stat_card(cards_frame, 0, "Licenza", "license_status", "Verificando...")
        
        # Card: File Elaborati (sessione)
        self._create_stat_card(cards_frame, 1, "File Elaborati", "files_count", "0")
        
        # Card: Pagine Processate
        self._create_stat_card(cards_frame, 2, "Pagine Totali", "pages_count", "0")
        
        # Card: Regole Attive
        self._create_stat_card(cards_frame, 3, "Regole Attive", "rules_count", "0")

        # Quick Actions
        actions_frame = ttk.LabelFrame(main_frame, text=" Azioni Rapide ", padding=15)
        actions_frame.pack(fill='x', pady=20)

        btn_frame = ttk.Frame(actions_frame)
        btn_frame.pack()

        ttk.Button(btn_frame, text="Seleziona PDF", 
                  command=self._quick_select_pdf).pack(side='left', padx=10)
        ttk.Button(btn_frame, text="Configura Regole", 
                  command=lambda: self.notebook.select(self.config_tab)).pack(side='left', padx=10)
        ttk.Button(btn_frame, text="Apri Utility ROI", 
                  command=self._launch_roi_utility).pack(side='left', padx=10)
        ttk.Button(btn_frame, text="Verifica Aggiornamenti", 
                  command=lambda: app_updater.check_for_updates(silent=False)).pack(side='left', padx=10)

        # Info Licenza dettagliata
        license_frame = ttk.LabelFrame(main_frame, text=" Informazioni Licenza ", padding=15)
        license_frame.pack(fill='x', pady=10)

        self.license_info_text = tk.Text(license_frame, height=4, font=FONTS['mono'],
                                         bg=COLORS['bg_secondary'], fg=COLORS['text_primary'],
                                         relief='flat', state='disabled', wrap='word')
        self.license_info_text.pack(fill='x')

        # Log Recente
        recent_frame = ttk.LabelFrame(main_frame, text=" Attivita' Recente ", padding=15)
        recent_frame.pack(fill='both', expand=True, pady=10)

        self.recent_log = scrolledtext.ScrolledText(recent_frame, height=8, font=FONTS['mono'],
                                                    bg=COLORS['bg_secondary'], fg=COLORS['text_primary'],
                                                    relief='flat', state='disabled', wrap='word')
        self.recent_log.pack(fill='both', expand=True)
        self.recent_log.tag_config("INFO", foreground=COLORS['text_primary'])
        self.recent_log.tag_config("SUCCESS", foreground=COLORS['success'])
        self.recent_log.tag_config("WARNING", foreground=COLORS['warning'])
        self.recent_log.tag_config("ERROR", foreground=COLORS['danger'])

    def _create_stat_card(self, parent, col, title, var_name, initial_value):
        """Crea una card statistica."""
        card = tk.Frame(parent, bg=COLORS['bg_secondary'], relief='flat', bd=0,
                       highlightthickness=1, highlightbackground=COLORS['border'])
        card.grid(row=0, column=col, padx=8, pady=5, sticky='nsew')

        tk.Label(card, text=title, font=FONTS['small'], bg=COLORS['bg_secondary'],
                fg=COLORS['text_secondary']).pack(pady=(15, 5))
        
        value_label = tk.Label(card, text=initial_value, font=('Segoe UI', 18, 'bold'),
                              bg=COLORS['bg_secondary'], fg=COLORS['accent'])
        value_label.pack(pady=(0, 15))
        
        setattr(self, f'{var_name}_label', value_label)

    def _update_clock(self):
        """Aggiorna l'orologio nella dashboard."""
        now = datetime.now().strftime("%d/%m/%Y  %H:%M:%S")
        self.clock_label.config(text=now)
        self.root.after(1000, self._update_clock)

    def _quick_select_pdf(self):
        """Selezione rapida PDF dalla dashboard."""
        self.notebook.select(self.processing_tab)
        self.root.after(100, self._select_pdf)

    def _setup_processing_tab(self):
        """Configura la tab Elaborazione."""
        main_frame = ttk.Frame(self.processing_tab, style='Card.TFrame', padding=20)
        main_frame.pack(fill='both', expand=True)

        # Header
        ttk.Label(main_frame, text="Elaborazione PDF", style='Header.TLabel').pack(anchor='w', pady=(0, 20))

        # Input Frame
        input_frame = ttk.LabelFrame(main_frame, text=" Input ", padding=15)
        input_frame.pack(fill='x', pady=(0, 15))

        # ODC
        odc_frame = ttk.Frame(input_frame)
        odc_frame.pack(fill='x', pady=5)

        ttk.Label(odc_frame, text="Codice ODC:", font=FONTS['body_bold'], width=15).pack(side='left')
        self.odc_var = tk.StringVar(value="5400")
        odc_entry = ttk.Entry(odc_frame, textvariable=self.odc_var, width=30, font=FONTS['body'])
        odc_entry.pack(side='left', padx=10)

        # File Selection
        file_frame = ttk.Frame(input_frame)
        file_frame.pack(fill='x', pady=10)

        ttk.Button(file_frame, text="Seleziona PDF...", command=self._select_pdf).pack(side='left')
        
        self.pdf_path_label = ttk.Label(file_frame, text="Nessun file selezionato", 
                                        style='Muted.TLabel', font=FONTS['body'])
        self.pdf_path_label.pack(side='left', padx=15)

        # Drag & Drop hint
        hint_frame = tk.Frame(input_frame, bg=COLORS['bg_tertiary'], relief='flat')
        hint_frame.pack(fill='x', pady=10)
        tk.Label(hint_frame, text="Trascina file o cartelle qui per avviare l'elaborazione automatica",
                font=FONTS['small'], bg=COLORS['bg_tertiary'], fg=COLORS['text_secondary'],
                pady=10).pack()

        # Progress
        self.progress_frame = ttk.LabelFrame(main_frame, text=" Progresso ", padding=15)
        self.progress_frame.pack(fill='x', pady=10)

        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(self.progress_frame, variable=self.progress_var,
                                            maximum=100, length=400, mode='determinate')
        self.progress_bar.pack(fill='x', pady=5)

        self.progress_label = ttk.Label(self.progress_frame, text="In attesa...", style='Muted.TLabel')
        self.progress_label.pack()

        # Log
        log_frame = ttk.LabelFrame(main_frame, text=" Log Elaborazione ", padding=15)
        log_frame.pack(fill='both', expand=True, pady=10)

        self.log_area = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, state='disabled',
                                                  font=FONTS['mono'], bg=COLORS['bg_secondary'],
                                                  fg=COLORS['text_primary'], relief='flat')
        self.log_area.pack(expand=True, fill='both')

        # Tag configurazione per i colori del log
        self.log_area.tag_config("ERROR", foreground=COLORS['danger'], font=FONTS['mono_bold'])
        self.log_area.tag_config("WARNING", foreground="#E67E22", font=FONTS['mono'])
        self.log_area.tag_config("INFO", foreground=COLORS['text_primary'])
        self.log_area.tag_config("SUCCESS", foreground=COLORS['success'], font=FONTS['mono_bold'])
        self.log_area.tag_config("PROGRESS", foreground=COLORS['accent'])
        self.log_area.tag_config("HEADER", foreground=COLORS['accent'], font=FONTS['mono_bold'])

    def _setup_config_tab(self):
        """Configura la tab Configurazione."""
        main_frame = ttk.Frame(self.config_tab, style='Card.TFrame', padding=20)
        main_frame.pack(fill='both', expand=True)

        # Header
        ttk.Label(main_frame, text="Configurazione", style='Header.TLabel').pack(anchor='w', pady=(0, 20))

        # Tesseract Path
        path_frame = ttk.LabelFrame(main_frame, text=" Tesseract OCR ", padding=15)
        path_frame.pack(fill='x', pady=(0, 15))
        path_frame.columnconfigure(1, weight=1)

        ttk.Label(path_frame, text="Percorso:", font=FONTS['body_bold']).grid(row=0, column=0, padx=5, pady=5, sticky='w')
        
        self.tesseract_path_var = tk.StringVar()
        self.tesseract_path_var.trace("w", self._on_tesseract_path_change)
        
        ttk.Entry(path_frame, textvariable=self.tesseract_path_var, font=FONTS['body']).grid(
            row=0, column=1, padx=5, pady=5, sticky='ew')
        
        btn_frame = ttk.Frame(path_frame)
        btn_frame.grid(row=0, column=2, padx=5)
        ttk.Button(btn_frame, text="Sfoglia", command=self._browse_tesseract).pack(side='left', padx=2)
        ttk.Button(btn_frame, text="Auto-Rileva", command=self._auto_detect_tesseract).pack(side='left', padx=2)

        # Regole
        rules_frame = ttk.LabelFrame(main_frame, text=" Regole di Classificazione ", padding=15)
        rules_frame.pack(expand=True, fill='both', pady=10)
        rules_frame.columnconfigure(1, weight=1)
        rules_frame.rowconfigure(0, weight=1)

        # Treeview Container
        tree_container = ttk.Frame(rules_frame)
        tree_container.grid(row=0, column=0, sticky='nsew', padx=(0, 10))
        tree_container.columnconfigure(0, weight=1)
        tree_container.rowconfigure(0, weight=1)

        self.rules_tree = ttk.Treeview(tree_container, columns=("ColorCode", "Category", "Suffix"), 
                                       show='headings', height=12)
        self.rules_tree.heading("ColorCode", text="Colore")
        self.rules_tree.column("ColorCode", width=80, anchor='center', stretch=False)
        self.rules_tree.heading("Category", text="Categoria")
        self.rules_tree.column("Category", width=150)
        self.rules_tree.heading("Suffix", text="Suffisso")
        self.rules_tree.column("Suffix", width=100)

        self.rules_tree.grid(row=0, column=0, sticky='nsew')
        
        scrollbar = ttk.Scrollbar(tree_container, orient="vertical", command=self.rules_tree.yview)
        self.rules_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky='ns')

        self.rules_tree.bind("<<TreeviewSelect>>", self._update_rule_details_panel)

        # Dettagli Regola
        self.rule_details_frame = ttk.LabelFrame(rules_frame, text=" Dettagli Regola ", padding=15)
        self.rule_details_frame.grid(row=0, column=1, sticky='nsew')
        self.rule_details_frame.columnconfigure(0, weight=1)

        ttk.Label(self.rule_details_frame, text="Keywords:", font=FONTS['body_bold']).grid(
            row=0, column=0, sticky='w', pady=(0, 5))

        self.keywords_text = tk.Text(self.rule_details_frame, height=5, font=FONTS['body'],
                                     bg=COLORS['bg_secondary'], fg=COLORS['text_primary'],
                                     relief='flat', state='disabled', wrap='word')
        self.keywords_text.grid(row=1, column=0, sticky='nsew', pady=(0, 15))

        ttk.Label(self.rule_details_frame, text="Aree ROI:", font=FONTS['body_bold']).grid(
            row=2, column=0, sticky='w', pady=(0, 5))
        
        self.roi_details_var = tk.StringVar()
        ttk.Label(self.rule_details_frame, textvariable=self.roi_details_var, 
                 style='Muted.TLabel').grid(row=3, column=0, sticky='w')

        # Buttons
        buttons_frame = ttk.Frame(rules_frame)
        buttons_frame.grid(row=0, column=2, sticky='n', padx=(10, 0))

        ttk.Button(buttons_frame, text="Aggiungi", command=self._add_rule).pack(fill='x', pady=3)
        ttk.Button(buttons_frame, text="Modifica", command=self._modify_rule).pack(fill='x', pady=3)
        ttk.Button(buttons_frame, text="Rimuovi", command=self._remove_rule).pack(fill='x', pady=3)
        
        ttk.Separator(buttons_frame, orient='horizontal').pack(fill='x', pady=15)
        
        ttk.Button(buttons_frame, text="Utility ROI", command=self._launch_roi_utility).pack(fill='x', pady=3)

    def _setup_help_tab(self):
        """Configura la tab Guida."""
        main_frame = ttk.Frame(self.help_tab, style='Card.TFrame', padding=20)
        main_frame.pack(fill='both', expand=True)

        ttk.Label(main_frame, text="Guida all'Uso", style='Header.TLabel').pack(anchor='w', pady=(0, 20))

        help_text = """
+==============================================================================+
|                        INTELLEO PDF SPLITTER - GUIDA                         |
+==============================================================================+
|                                                                              |
|  COME USARE L'APPLICAZIONE                                                   |
|  ----------------------------------------------------------------------------+
|                                                                              |
|  1. CONFIGURAZIONE INIZIALE                                                  |
|     - Vai nella tab "Configurazione"                                         |
|     - Verifica che il percorso Tesseract sia corretto                        |
|     - Configura le regole di classificazione per i tuoi documenti            |
|                                                                              |
|  2. DEFINIZIONE REGOLE                                                       |
|     - Ogni regola ha un nome categoria (es. "consuntivo", "pdl")             |
|     - Definisci le keyword da cercare nel documento                          |
|     - Usa l'Utility ROI per selezionare le aree dove cercare                 |
|                                                                              |
|  3. ELABORAZIONE                                                             |
|     - Vai nella tab "Elaborazione"                                           |
|     - Inserisci il codice ODC                                                |
|     - Seleziona o trascina i file PDF da elaborare                           |
|     - L'elaborazione parte automaticamente                                   |
|                                                                              |
|  4. OUTPUT                                                                   |
|     - I PDF vengono divisi per categoria nella stessa cartella               |
|     - I file originali vengono spostati in "ORIGINALI"                       |
|     - I file non riconosciuti possono essere rinominati manualmente          |
|                                                                              |
|  SCORCIATOIE                                                                 |
|  ----------------------------------------------------------------------------+
|     - Trascina file/cartelle per elaborazione automatica                     |
|     - Frecce <- -> per navigare le pagine                                    |
|     - Frecce Su/Giu per navigare i file nella revisione                      |
|     - Rotella mouse per zoom nell'anteprima PDF                              |
|                                                                              |
|  SUPPORTO                                                                    |
|  ----------------------------------------------------------------------------+
|     Per assistenza contattare il supporto tecnico Intelleo.                  |
|                                                                              |
+==============================================================================+
"""
        help_area = scrolledtext.ScrolledText(main_frame, wrap='word', font=FONTS['mono'],
                                              bg=COLORS['bg_secondary'], fg=COLORS['text_primary'],
                                              relief='flat', state='normal')
        help_area.pack(fill='both', expand=True)
        help_area.insert('1.0', help_text)
        help_area.config(state='disabled')

    def _display_license_info(self):
        """Mostra le informazioni della licenza."""
        try:
            payload = license_validator.get_license_info()
            if payload:
                cliente = payload.get('Cliente', 'N/A')
                scadenza = payload.get('Scadenza Licenza', 'N/A')
                hw_id = payload.get('Hardware ID', 'N/A')

                self.license_status_label.config(text="[OK] Valida", fg=COLORS['success'])
                
                info_text = f"""+==================================================================+
|  Cliente:      {cliente:<50}|
|  Scadenza:     {scadenza:<50}|
|  Hardware ID:  {hw_id:<50}|
+==================================================================+"""
                
                self.license_info_text.config(state='normal')
                self.license_info_text.delete('1.0', 'end')
                self.license_info_text.insert('1.0', info_text)
                self.license_info_text.config(state='disabled')

                self._add_recent_log(f"Licenza valida per: {cliente}", "SUCCESS")
            else:
                self.license_status_label.config(text="[!] Non trovata", fg=COLORS['warning'])
                self._add_recent_log("File licenza non trovato", "WARNING")

        except Exception as e:
            self.license_status_label.config(text="[X] Errore", fg=COLORS['danger'])
            self._add_recent_log(f"Errore licenza: {e}", "ERROR")

    def _add_recent_log(self, message, level="INFO"):
        """Aggiunge un messaggio al log recente della dashboard."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.recent_log.config(state='normal')
        self.recent_log.insert('end', f"[{timestamp}] {message}\n", level)
        self.recent_log.config(state='disabled')
        self.recent_log.see('end')

    def _add_log_message(self, message, level="INFO"):
        """Aggiunge un messaggio al log principale."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_area.config(state='normal')

        if level == "PROGRESS":
            last_idx = self.log_area.index("end-2l")
            last_line = self.log_area.get(last_idx, "end-1c")
            if "Elaborazione pagina" in last_line:
                self.log_area.delete(last_idx, "end-1c")

        prefix = ""
        if level == "ERROR":
            prefix = "[X] "
        elif level == "WARNING":
            prefix = "[!] "
        elif level == "SUCCESS":
            prefix = "[OK] "
        elif level == "HEADER":
            prefix = "=== "

        self.log_area.insert('end', f"[{timestamp}] {prefix}{message}\n", level)
        self.log_area.config(state='disabled')
        self.log_area.see('end')

        if level in ["SUCCESS", "ERROR", "WARNING"]:
            self._add_recent_log(message, level)

    def _process_log_queue(self):
        """Processa i messaggi in coda per il log."""
        try:
            while True:
                item = self.log_queue.get_nowait()
                if isinstance(item, tuple):
                    self._add_log_message(item[0], item[1])
                elif isinstance(item, dict):
                    if item.get('action') == 'show_unknown_dialog':
                        self._show_unknown_dialog(item['files'], item['odc'])
                    elif item.get('action') == 'update_progress':
                        self.progress_var.set(item.get('value', 0))
                        self.progress_label.config(text=item.get('text', ''))
                    elif item.get('action') == 'increment_pages':
                        self.pages_processed_count += item.get('count', 1)
                        self.pages_count_label.config(text=str(self.pages_processed_count))
                else:
                    self._add_log_message(str(item))
        except queue.Empty:
            pass
        finally:
            self.root.after(50, self._process_log_queue)

    def _check_for_updates(self):
        """Controlla aggiornamenti dalla utility ROI."""
        if os.path.exists(SIGNAL_FILE):
            try:
                os.remove(SIGNAL_FILE)
                self.load_settings()
                self._add_log_message("Configurazione aggiornata dall'utility ROI", "SUCCESS")
            except OSError as e:
                logger.error(f"Gestione signal file: {e}")
        self.root.after(150, self._check_for_updates)

    def _on_drop(self, event):
        """Gestisce il drop di file."""
        files_to_add = []
        try:
            raw_files = self.root.tk.splitlist(event.data)
            for f in raw_files:
                if os.path.exists(f):
                    if os.path.isdir(f):
                        for root_dir, _, files in os.walk(f):
                            for name in files:
                                if name.lower().endswith('.pdf'):
                                    files_to_add.append(os.path.join(root_dir, name))
                    elif f.lower().endswith('.pdf'):
                        files_to_add.append(f)
        except Exception as e:
            self._add_log_message(f"Errore parsing drop: {e}", "ERROR")
            return

        if files_to_add:
            self.pdf_files = files_to_add
            if len(self.pdf_files) == 1:
                self.pdf_path_label.config(text=f"{os.path.basename(self.pdf_files[0])}")
            else:
                self.pdf_path_label.config(text=f"{len(self.pdf_files)} file selezionati")
            
            self.notebook.select(self.processing_tab)
            self._start_processing()

    def _handle_cli_start(self, path):
        """Gestisce l'avvio da riga di comando."""
        found_pdfs = []

        if os.path.isfile(path) and path.lower().endswith('.pdf'):
            found_pdfs.append(path)
        elif os.path.isdir(path):
            for root_dir, _, files in os.walk(path):
                for name in files:
                    if name.lower().endswith('.pdf'):
                        found_pdfs.append(os.path.join(root_dir, name))

        if not found_pdfs:
            messagebox.showerror("Errore", "Nessun file PDF trovato nel percorso specificato.")
            return

        self.pdf_files = found_pdfs
        self.pdf_path_label.config(text=f"{len(found_pdfs)} file trovati")

        odc = simpledialog.askstring("Input ODC", 
                                     "Inserisci il codice ODC:", 
                                     parent=self.root)
        if odc:
            self.odc_var.set(odc)
            self.notebook.select(self.processing_tab)
            self._start_processing()

    def _select_pdf(self):
        """Apre il dialogo di selezione PDF."""
        paths = filedialog.askopenfilenames(title="Seleziona file PDF", 
                                           filetypes=[("PDF Files", "*.pdf")])
        if paths:
            self.pdf_files = list(paths)
            if len(self.pdf_files) == 1:
                self.pdf_path_label.config(text=f"{os.path.basename(self.pdf_files[0])}")
            else:
                self.pdf_path_label.config(text=f"{len(self.pdf_files)} file selezionati")
            self._start_processing()

    def _start_processing(self):
        """Avvia l'elaborazione dei PDF."""
        odc_input = self.odc_var.get().strip()

        if not odc_input:
            messagebox.showerror("Errore", "Inserire un codice ODC valido.")
            return

        if not self.pdf_files:
            messagebox.showerror("Errore", "Seleziona almeno un file PDF.")
            return

        self.log_area.config(state='normal')
        self.log_area.delete('1.0', 'end')
        self.log_area.config(state='disabled')
        self.progress_var.set(0)
        self.progress_label.config(text="Inizializzazione...")

        self._add_log_message("AVVIO ELABORAZIONE", "HEADER")
        self._add_log_message(f"Codice ODC: {odc_input}", "INFO")
        self._add_log_message(f"File da elaborare: {len(self.pdf_files)}", "INFO")
        self._add_log_message("-" * 60, "INFO")

        self.processing_start_time = datetime.now()
        files_to_process = list(self.pdf_files)

        thread = threading.Thread(target=self._processing_worker, 
                                 args=(files_to_process, odc_input, self.config))
        thread.daemon = True
        thread.start()

    def _processing_worker(self, pdf_files, odc, config):
        """Worker thread per l'elaborazione PDF."""
        unknown_files = []
        total_files = len(pdf_files)

        for i, pdf_path in enumerate(pdf_files):
            def progress_callback(message, level="INFO"):
                self.log_queue.put((message, level))
                
                if "Elaborazione pagina" in message:
                    try:
                        parts = message.split()
                        for p in parts:
                            if "/" in p:
                                current, total = p.split("/")
                                page_progress = int(current) / int(total) * 100
                                file_progress = (i / total_files) * 100
                                combined = file_progress + (page_progress / total_files)
                                self.log_queue.put({
                                    'action': 'update_progress',
                                    'value': combined,
                                    'text': f"File {i+1}/{total_files} - Pagina {current}/{total}"
                                })
                                self.log_queue.put({'action': 'increment_pages', 'count': 0})
                                break
                    except:
                        pass

            self.log_queue.put((f"=== FILE {i+1}/{total_files}: {os.path.basename(pdf_path)} ===", "HEADER"))

            success, message, generated, moved_original_path = pdf_processor.process_pdf(
                pdf_path, odc, config, progress_callback)

            if not success:
                self.log_queue.put((f"Errore: {message}", "ERROR"))
            else:
                self.files_processed_count += 1
                self.log_queue.put((f"File completato con successo", "SUCCESS"))

                has_unknown = any(f['category'] == 'sconosciuto' for f in generated)
                if has_unknown:
                    unknown_paths = [f['path'] for f in generated if f['category'] == 'sconosciuto']
                    siblings = [f['path'] for f in generated if f['category'] != 'sconosciuto']

                    for u_path in unknown_paths:
                        unknown_files.append({
                            'unknown_path': u_path,
                            'source_path': moved_original_path,
                            'siblings': siblings
                        })

        self.log_queue.put({'action': 'update_progress', 'value': 100, 'text': 'Completato!'})
        
        elapsed = datetime.now() - self.processing_start_time if self.processing_start_time else None
        elapsed_str = str(elapsed).split('.')[0] if elapsed else "N/A"
        
        self.log_queue.put(("-" * 60, "INFO"))
        self.log_queue.put((f"ELABORAZIONE COMPLETATA in {elapsed_str}", "HEADER"))
        self.log_queue.put((f"File elaborati: {total_files}", "SUCCESS"))

        if unknown_files:
            self.log_queue.put({'action': 'show_unknown_dialog', 'files': unknown_files, 'odc': odc})

        self.root.after(0, lambda: self.files_count_label.config(text=str(self.files_processed_count)))
        self.root.after(0, lambda: self.odc_var.set("5400"))

    def _show_unknown_dialog(self, files, odc):
        """Mostra il dialog per file sconosciuti."""
        if not files:
            return

        def on_close():
            self._add_log_message("Revisione file sconosciuti completata", "SUCCESS")

        UnknownFilesReviewDialog(self.root, files, odc, on_close)

    def load_settings(self):
        """Carica le impostazioni."""
        self.config = config_manager.load_config()
        
        if hasattr(self, 'tesseract_path_var'):
            try:
                for trace in self.tesseract_path_var.trace_info():
                    self.tesseract_path_var.trace_remove(trace[0], trace[1])
            except:
                pass
            
            self.tesseract_path_var.set(self.config.get("tesseract_path", ""))
            self.tesseract_path_var.trace("w", self._on_tesseract_path_change)

        self._populate_rules_tree()
        
        rules_count = len(self.config.get("classification_rules", []))
        if hasattr(self, 'rules_count_label'):
            self.rules_count_label.config(text=str(rules_count))

    def _auto_save_settings(self):
        """Salva automaticamente le impostazioni."""
        try:
            config_manager.save_config(self.config)
        except Exception as e:
            logger.error(f"Auto-Save: {e}")

    def _populate_rules_tree(self):
        """Popola la treeview delle regole."""
        self.keywords_text.config(state='normal')
        self.keywords_text.delete("1.0", 'end')
        self.keywords_text.config(state='disabled')
        self.roi_details_var.set("")

        for item in self.rules_tree.get_children():
            self.rules_tree.delete(item)

        for rule in self.config.get("classification_rules", []):
            color = rule.get("color", "#FFFFFF")
            suffix = rule.get("filename_suffix", rule["category_name"])
            tag_name = f"color_{color}"

            h = color.lstrip('#')
            try:
                rgb = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
                brightness = (rgb[0] * 299 + rgb[1] * 587 + rgb[2] * 114) / 1000
                text_color = "black" if brightness > 128 else "white"
            except:
                text_color = "black"

            self.rules_tree.tag_configure(tag_name, background=color, foreground=text_color)
            self.rules_tree.insert("", 'end', values=(color, rule["category_name"], suffix), tags=(tag_name,))

    def _update_rule_details_panel(self, event=None):
        """Aggiorna il pannello dettagli regola."""
        selected_item = self.rules_tree.focus()
        if not selected_item:
            self.keywords_text.config(state='normal')
            self.keywords_text.delete("1.0", 'end')
            self.keywords_text.config(state='disabled')
            self.roi_details_var.set("")
            return

        item_values = self.rules_tree.item(selected_item, "values")
        category_name = item_values[1]

        rule = next((r for r in self.config.get("classification_rules", []) 
                    if r["category_name"] == category_name), None)

        if rule:
            keywords_str = ", ".join(rule.get("keywords", []))
            rois_count = len(rule.get("rois", []))

            self.keywords_text.config(state='normal')
            self.keywords_text.delete("1.0", 'end')
            self.keywords_text.insert('end', keywords_str)
            self.keywords_text.config(state='disabled')

            self.roi_details_var.set(f"{rois_count} aree ROI definite")

    def _on_tesseract_path_change(self, *args):
        """Gestisce il cambio del path Tesseract."""
        self.config["tesseract_path"] = self.tesseract_path_var.get()
        self._auto_save_settings()

    def _browse_tesseract(self):
        """Apre il dialog per selezionare Tesseract."""
        path = filedialog.askopenfilename(
            title="Seleziona Tesseract", 
            filetypes=[("Executable", "*.exe")])
        if path:
            self.tesseract_path_var.set(path)

    def _auto_detect_tesseract(self):
        """Rileva automaticamente Tesseract."""
        search_paths = [
            os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), 
                        "Tesseract-OCR", "tesseract.exe"),
            os.path.join(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"), 
                        "Tesseract-OCR", "tesseract.exe"),
            os.path.join(os.environ.get("LOCALAPPDATA", ""), 
                        "Tesseract-OCR", "tesseract.exe")
        ]
        
        for path in search_paths:
            if path and os.path.exists(path):
                self.tesseract_path_var.set(path)
                messagebox.showinfo("Trovato", f"Tesseract trovato:\n{path}")
                return
        
        messagebox.showwarning("Non Trovato", 
                              "Tesseract non trovato automaticamente.\nIndicalo manualmente.")

    def _add_rule(self):
        """Aggiunge una nuova regola."""
        self._show_rule_editor()

    def _modify_rule(self):
        """Modifica una regola esistente."""
        selected_item = self.rules_tree.focus()
        if not selected_item:
            messagebox.showwarning("Selezione", "Selezionare una regola da modificare.")
            return
        
        item_values = self.rules_tree.item(selected_item, "values")
        rule = next((r for r in self.config["classification_rules"] 
                    if r["category_name"] == item_values[1]), None)
        if rule:
            self._show_rule_editor(rule)

    def _remove_rule(self):
        """Rimuove una regola."""
        selected_item = self.rules_tree.focus()
        if not selected_item:
            messagebox.showwarning("Selezione", "Selezionare una regola da rimuovere.")
            return
        
        category_name = self.rules_tree.item(selected_item, "values")[1]
        if messagebox.askyesno("Conferma", f"Rimuovere la regola '{category_name}'?"):
            self.config["classification_rules"] = [
                r for r in self.config["classification_rules"] 
                if r["category_name"] != category_name
            ]
            self._populate_rules_tree()
            self._auto_save_settings()
            
            self.rules_count_label.config(
                text=str(len(self.config.get("classification_rules", []))))

    def _show_rule_editor(self, rule=None):
        """Mostra l'editor di regole."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Modifica Regola" if rule else "Nuova Regola")
        dialog.configure(bg=COLORS['bg_primary'])
        dialog.geometry("450x350")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        main_frame = ttk.Frame(dialog, padding=20)
        main_frame.pack(fill='both', expand=True)

        category_var = tk.StringVar(value=rule["category_name"] if rule else "")
        suffix_var = tk.StringVar(value=rule.get("filename_suffix", "") if rule else "")
        keywords_var = tk.StringVar(value=", ".join(rule.get("keywords", [])) if rule else "")
        chosen_color = tk.StringVar(value=rule.get("color", "#0D6EFD") if rule else "#0D6EFD")

        row = 0
        
        ttk.Label(main_frame, text="Nome Categoria:", font=FONTS['body_bold']).grid(
            row=row, column=0, sticky='w', pady=8)
        cat_entry = ttk.Entry(main_frame, textvariable=category_var, width=35)
        cat_entry.grid(row=row, column=1, columnspan=2, pady=8, sticky='ew')
        if rule:
            cat_entry.config(state='readonly')
        
        row += 1
        
        ttk.Label(main_frame, text="Suffisso File:", font=FONTS['body_bold']).grid(
            row=row, column=0, sticky='w', pady=8)
        ttk.Entry(main_frame, textvariable=suffix_var, width=35).grid(
            row=row, column=1, columnspan=2, pady=8, sticky='ew')
        
        row += 1
        
        ttk.Label(main_frame, text="Keywords:", font=FONTS['body_bold']).grid(
            row=row, column=0, sticky='w', pady=8)
        ttk.Entry(main_frame, textvariable=keywords_var, width=35).grid(
            row=row, column=1, columnspan=2, pady=8, sticky='ew')
        ttk.Label(main_frame, text="(separate da virgola)", style='Muted.TLabel').grid(
            row=row+1, column=1, sticky='w')
        
        row += 2
        
        ttk.Label(main_frame, text="Colore:", font=FONTS['body_bold']).grid(
            row=row, column=0, sticky='w', pady=8)
        
        color_swatch = tk.Label(main_frame, text="     ", bg=chosen_color.get(), 
                               relief='solid', bd=1, width=8)
        color_swatch.grid(row=row, column=1, sticky='w', pady=8)

        def choose_color():
            result = colorchooser.askcolor(title="Scegli Colore", 
                                          initialcolor=chosen_color.get())
            if result and result[1]:
                chosen_color.set(result[1])
                color_swatch.config(bg=result[1])

        ttk.Button(main_frame, text="Scegli", command=choose_color).grid(
            row=row, column=2, pady=8)
        
        row += 1
        
        ttk.Label(main_frame, text="Aree ROI:", font=FONTS['body_bold']).grid(
            row=row, column=0, sticky='w', pady=8)
        roi_count = len(rule.get("rois", [])) if rule else 0
        ttk.Label(main_frame, text=f"{roi_count} aree definite", 
                 style='Muted.TLabel').grid(row=row, column=1, sticky='w', pady=8)

        def on_save():
            category = category_var.get().strip()
            suffix = suffix_var.get().strip() or category
            keywords = [k.strip() for k in keywords_var.get().split(',') if k.strip()]
            color = chosen_color.get()

            if not category or not keywords:
                messagebox.showerror("Errore", 
                                    "Nome categoria e almeno una keyword sono obbligatori.", 
                                    parent=dialog)
                return

            new_data = {
                "category_name": category,
                "filename_suffix": suffix,
                "keywords": keywords,
                "color": color
            }

            if rule:
                new_data['rotate_roi'] = rule.get('rotate_roi', 0)
                new_data['rois'] = rule.get('rois', [])
                rule.update(new_data)
            else:
                if any(r["category_name"] == category 
                      for r in self.config.get("classification_rules", [])):
                    messagebox.showerror("Errore", "Categoria gia' esistente.", parent=dialog)
                    return
                new_data["rois"] = []
                self.config.setdefault("classification_rules", []).append(new_data)

            self._populate_rules_tree()
            self._auto_save_settings()
            self.rules_count_label.config(
                text=str(len(self.config.get("classification_rules", []))))
            dialog.destroy()

        ttk.Separator(main_frame, orient='horizontal').grid(
            row=row+1, column=0, columnspan=3, sticky='ew', pady=15)
        
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=row+2, column=0, columnspan=3)
        
        ttk.Button(btn_frame, text="Salva", command=on_save).pack(side='left', padx=10)
        ttk.Button(btn_frame, text="Annulla", command=dialog.destroy).pack(side='left', padx=10)

    def _launch_roi_utility(self):
        """Lancia l'utility ROI."""
        try:
            if getattr(sys, 'frozen', False):
                # Se l'app è congelata (PyInstaller), lancia l'eseguibile con un flag
                subprocess.Popen([sys.executable, "--utility"])
            else:
                # Se è uno script Python, lancia il file roi_utility.py
                script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'roi_utility.py')
                subprocess.Popen([sys.executable, script_path])

            self._add_log_message("Utility ROI avviata", "SUCCESS")
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile avviare l'utility ROI:\n{e}")


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================
if __name__ == "__main__":
    # Check for ROI Utility launch flag (used in frozen builds)
    if "--utility" in sys.argv:
        try:
            import roi_utility
            roi_utility.run_utility()
        except Exception as e:
            logger.critical(f"Failed to launch ROI utility: {e}", exc_info=True)
        sys.exit(0)

    logger.info("="*68)
    logger.info("           INTELLEO PDF SPLITTER - AVVIO APPLICAZIONE")
    logger.info("="*68)
    logger.info(f"  Versione: {version.__version__}")
    logger.info(f"  Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    logger.info("="*68)

    # License Update & Check
    logger.info("Verifica licenza in corso...")
    try:
        license_updater.run_update()
        logger.info("Aggiornamento licenza completato")
    except Exception as e:
        logger.critical(f"Verifica licenza fallita: {e}", exc_info=True)
        messagebox.showerror("Errore Licenza", f"Impossibile verificare la licenza:\n{e}")
        sys.exit(1)

    is_valid, msg = license_validator.verify_license()
    if not is_valid:
        logger.error(f"Licenza non valida: {msg}")
        root = tk.Tk()
        root.withdraw()
        hw_id = license_validator.get_hardware_id()
        err_msg = f"{msg}\n\nHardware ID:\n{hw_id}\n\n(Copiato negli appunti)"
        root.clipboard_clear()
        root.clipboard_append(hw_id)
        messagebox.showerror("Licenza Non Valida", err_msg)
        sys.exit(1)

    logger.info("Licenza valida")
    logger.info("Inizializzazione interfaccia grafica...")

    # Pulizia signal file
    if os.path.exists(SIGNAL_FILE):
        os.remove(SIGNAL_FILE)

    # Inizializzazione Tk con DnD
    try:
        root = TkinterDnD.Tk()
        logger.info("Drag & Drop abilitato")
    except Exception as e:
        logger.warning(f"Drag & Drop non disponibile: {e}")
        root = tk.Tk()

    # Check CLI args
    cli_path = None
    if len(sys.argv) > 1:
        potential_path = sys.argv[1]
        if os.path.exists(potential_path):
            if os.path.isdir(potential_path) or potential_path.lower().endswith('.pdf'):
                cli_path = potential_path
                logger.info(f"Avvio con file: {potential_path}")

    logger.info("Applicazione pronta")

    app = MainApp(root, auto_file_path=cli_path)
    
    logger.info("Avvio mainloop")
    root.mainloop()
    logger.info("Applicazione chiusa normalmente")
