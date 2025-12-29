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
    import json
    logger.info("Tutti i moduli importati con successo")
except Exception as e:
    logger.critical(f"Errore durante l'importazione dei moduli: {e}", exc_info=True)
    # Non rilanciare l'eccezione, permette all'app di partire anche se un modulo opzionale manca
    pass

# Segnale per comunicazione tra utility ROI e app principale
SIGNAL_FILE = ".update_signal"


# Costanti per la gestione della sessione
APP_DATA_DIR = os.path.join(os.getenv('APPDATA'), 'Intelleo PDF Splitter')
SESSION_FILE = os.path.join(APP_DATA_DIR, "session.json")


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
    """Dialog per la revisione manuale (Splitter) dei file sconosciuti."""
    
    def __init__(self, parent, review_tasks, on_finish=None):
        super().__init__(parent)
        self.title("Revisione Manuale - Divisione Allegati")
        self.state('zoomed')
        self.configure(bg=COLORS['bg_primary'])

        self.review_tasks = review_tasks
        self.on_finish = on_finish
        
        self.task_index = 0
        self.current_doc = None
        self.current_doc_path = None
        self.available_pages = [] 
        self.preview_page_index = 0
        self.zoom_level = 1.0
        self.image_ref = None

        self._setup_styles()
        self._create_widgets()
        
        self.load_task(0)
        
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def _setup_styles(self):
        style = ttk.Style()
        style.configure('Review.TFrame', background=COLORS['bg_primary'])

    def _create_widgets(self):
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        left_panel = ttk.Frame(self, padding=10, style='Review.TFrame')
        left_panel.grid(row=0, column=0, sticky='nsew', padx=(0, 5))
        left_panel.rowconfigure(1, weight=1)

        self.lbl_file_info = ttk.Label(left_panel, text="Caricamento...", 
                                      font=FONTS['subheading'], wraplength=250)
        self.lbl_file_info.grid(row=0, column=0, sticky='w', pady=(0, 10))

        list_frame = ttk.Frame(left_panel)
        list_frame.grid(row=1, column=0, sticky='nsew')
        
        ttk.Label(list_frame, text="Seleziona le pagine da unire:", 
                 font=FONTS['body_bold']).pack(anchor='w')
        
        self.pages_listbox = tk.Listbox(list_frame, selectmode='extended', font=FONTS['body'],
                                       activestyle='none', height=20, bg=COLORS['bg_secondary'],
                                       selectbackground=COLORS['accent'], selectforeground='white')
        self.pages_listbox.pack(side='left', fill='both', expand=True, pady=5)
        
        sb = ttk.Scrollbar(list_frame, orient='vertical', command=self.pages_listbox.yview)
        sb.pack(side='right', fill='y', pady=5)
        self.pages_listbox.config(yscrollcommand=sb.set)
        
        self.pages_listbox.bind('<<ListboxSelect>>', self._on_page_select)

        action_frame = ttk.LabelFrame(left_panel, text=" Azione ", padding=10)
        action_frame.grid(row=2, column=0, sticky='ew', pady=10)

        ttk.Button(action_frame, text="RINOMINA (Estrai Pagine)", 
                  command=self.extract_and_rename, style='Accent.TButton').pack(fill='x', pady=5)
        
        ttk.Label(action_frame, text="Crea un nuovo file con le pagine selezionate.", 
                 font=FONTS['small'], foreground=COLORS['text_secondary']).pack()

        nav_frame = ttk.Frame(left_panel)
        nav_frame.grid(row=3, column=0, sticky='ew', pady=10)
        
        self.btn_skip = ttk.Button(nav_frame, text="Salta File >>", command=self.skip_task)
        self.btn_skip.pack(fill='x')

        right_panel = ttk.Frame(self, padding=10, style='Review.TFrame')
        right_panel.grid(row=0, column=1, sticky='nsew')
        right_panel.rowconfigure(0, weight=1)
        right_panel.columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(right_panel, bg=COLORS['bg_tertiary'],
                               highlightthickness=1, highlightbackground=COLORS['border'])
        self.canvas.grid(row=0, column=0, sticky='nsew')
        
        v_scroll = ttk.Scrollbar(right_panel, orient='vertical', command=self.canvas.yview)
        v_scroll.grid(row=0, column=1, sticky='ns')
        h_scroll = ttk.Scrollbar(right_panel, orient='horizontal', command=self.canvas.xview)
        h_scroll.grid(row=1, column=0, sticky='ew')
        self.canvas.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        self.canvas.bind('<MouseWheel>', self.on_mouse_wheel)
        self.canvas.bind("<Control-ButtonPress-1>", self.start_pan)
        self.canvas.bind("<Control-B1-Motion>", self.pan)

    def load_task(self, index):
        if index >= len(self.review_tasks):
            messagebox.showinfo("Completato", "Tutti i file sono stati revisionati con successo!")
            if self.on_finish:
                self.on_finish()
            self.destroy()
            return

        self.task_index = index
        self.task = self.review_tasks[index]
        self.current_doc_path = self.task['unknown_path']
        
        if self.current_doc: self.current_doc.close()
        
        try:
            self.current_doc = fitz.open(self.current_doc_path)
            self.available_pages = list(range(self.current_doc.page_count))
            self.lbl_file_info.config(text=f"File {index+1}/{len(self.review_tasks)}\n{os.path.basename(self.current_doc_path)}")
            self._refresh_pages_list()
            if self.available_pages:
                self.pages_listbox.selection_set(0)
                self._on_page_select(None)
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile aprire il file: {e}")
            self.skip_task()

    def _refresh_pages_list(self):
        self.pages_listbox.delete(0, 'end')
        for real_idx in self.available_pages:
            self.pages_listbox.insert('end', f"Pagina {real_idx + 1}")

    def _on_page_select(self, event):
        selection = self.pages_listbox.curselection()
        if not selection: return
        list_idx = selection[-1]
        if list_idx < len(self.available_pages):
            self.preview_page_index = self.available_pages[list_idx]
            self._render_preview()

    def _render_preview(self):
        if not self.current_doc: return
        try:
            page = self.current_doc[self.preview_page_index]
            mat = fitz.Matrix(self.zoom_level, self.zoom_level)
            pix = page.get_pixmap(matrix=mat)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            self.image_ref = ImageTk.PhotoImage(img)
            self.canvas.delete("all")
            cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
            x, y = max(0, (cw - pix.width) // 2), max(0, (ch - pix.height) // 2)
            self.canvas.create_image(x, y, anchor='nw', image=self.image_ref)
            self.canvas.config(scrollregion=(0, 0, pix.width, pix.height))
        except Exception as e:
            print(f"Render error: {e}")

    def extract_and_rename(self):
        selection = self.pages_listbox.curselection()
        if not selection:
            messagebox.showwarning("Attenzione", "Seleziona almeno una pagina.", parent=self)
            return

        dialog = tk.Toplevel(self)
        dialog.title("Definisci Nome File")
        dialog.geometry("400x200")
        dialog.transient(self)
        dialog.grab_set()
        dialog.configure(bg=COLORS['bg_primary'])
        result = {}
        main_frame = ttk.Frame(dialog, padding=20)
        main_frame.pack(fill='both', expand=True)
        main_frame.columnconfigure(1, weight=1)
        ttk.Label(main_frame, text="Codice ODC:", font=FONTS['body_bold']).grid(row=0, column=0, sticky='w', pady=5)
        odc_entry = ttk.Entry(main_frame, font=FONTS['body'])
        odc_entry.grid(row=0, column=1, sticky='ew', pady=5)
        odc_entry.focus_set()
        ttk.Label(main_frame, text="Suffisso:", font=FONTS['body_bold']).grid(row=1, column=0, sticky='w', pady=5)
        suffix_entry = ttk.Entry(main_frame, font=FONTS['body'])
        suffix_entry.grid(row=1, column=1, sticky='ew', pady=5)

        def on_ok():
            result['odc'] = odc_entry.get().strip()
            result['suffix'] = suffix_entry.get().strip()
            if not result['odc'] or not result['suffix']:
                messagebox.showwarning("Dati Mancanti", "Sia ODC che Suffisso sono obbligatori.", parent=dialog)
                return
            dialog.destroy()

        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=20)
        ttk.Button(btn_frame, text="OK", command=on_ok).pack(side='left', padx=10)
        ttk.Button(btn_frame, text="Annulla", command=dialog.destroy).pack(side='left', padx=10)
        self.wait_window(dialog)

        if not result.get('odc') or not result.get('suffix'): return

        selected_real_indices = [self.available_pages[i] for i in selection]
        new_filename = f"{result['odc']}_{result['suffix']}.pdf"
        dir_path = os.path.dirname(self.current_doc_path)
        output_path = os.path.join(dir_path, new_filename)

        if os.path.exists(output_path) and not messagebox.askyesno("Sovrascrivi", "File esistente. Sovrascrivere?", parent=self):
            return
        
        try:
            if os.path.exists(output_path): os.remove(output_path)
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile sovrascrivere file esistente:\n{e}")
            return

        try:
            new_doc = fitz.open()
            for idx in selected_real_indices:
                new_doc.insert_pdf(self.current_doc, from_page=idx, to_page=idx)
            new_doc.save(output_path)
            new_doc.close()
            self.available_pages = [p for p in self.available_pages if p not in selected_real_indices]
            self._refresh_pages_list()
            if not self.available_pages:
                self.finish_task()
            else:
                if self.pages_listbox.size() > 0:
                    self.pages_listbox.selection_set(0)
                    self._on_page_select(None)
        except Exception as e:
            messagebox.showerror("Errore", f"Errore durante il salvataggio del file:\n{e}")

    def finish_task(self):
        if self.current_doc: self.current_doc.close()
        self.current_doc = None
        try:
            if os.path.exists(self.current_doc_path):
                os.remove(self.current_doc_path)
        except Exception as e:
            logger.error(f"Impossibile cancellare file temp {self.current_doc_path}: {e}")
        
        if 0 <= self.task_index < len(self.review_tasks):
            del self.review_tasks[self.task_index]
            self.load_task(self.task_index)
        else:
            self.load_task(0) 

    def skip_task(self):
        self.load_task(self.task_index + 1)

    def on_mouse_wheel(self, event):
        self.zoom_level *= 1.1 if event.delta > 0 else 0.9
        self._render_preview()

    def start_pan(self, event): self.canvas.scan_mark(event.x, event.y)
    def pan(self, event): self.canvas.scan_dragto(event.x, event.y, gain=1)
    def on_close(self):
        if self.current_doc: self.current_doc.close()
        self.destroy()

class MainApp:
    def __init__(self, root, auto_file_path=None):
        logger.info("Inizializzazione MainApp...")
        self.root = root
        self.root.title(f"Intelleo PDF Splitter v{version.__version__}")
        self.root.state('zoomed')
        self.root.configure(bg=COLORS['bg_primary'])
        self.setup_icon()
        
        self.config, self.pdf_files, self.log_queue = {}, [], queue.Queue()
        self.processing_start_time, self.files_processed_count, self.pages_processed_count = None, 0, 0

        logger.info("Configurazione stili e UI...")
        self._setup_styles()
        self._setup_ui_layout()
        self._setup_dashboard_tab()
        self._setup_processing_tab()
        self._setup_config_tab()
        self._setup_help_tab()
        
        logger.info("Configurazione Drag & Drop...")
        self._setup_drag_drop()

        logger.info("Avvio logica applicazione...")
        self.update_last_access()
        self.load_settings()
        self._display_license_info()
        self.root.after(100, self._process_log_queue)
        self.root.after(150, self._check_for_updates)
        self.root.after(500, self._check_for_restore)
        self.root.after(3000, lambda: app_updater.check_for_updates(silent=True, on_confirm=self._auto_save_settings))

        if auto_file_path and os.path.exists(auto_file_path):
            self.root.after(500, lambda: self._handle_cli_start(auto_file_path))
        logger.info("MainApp inizializzata con successo")

    def update_last_access(self):
        """Aggiorna la data dell'ultimo accesso nella configurazione."""
        try:
            config = config_manager.load_config()
            config['last_access'] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            config_manager.save_config(config)
        except Exception as e:
            logger.error(f"Impossibile aggiornare l'ultimo accesso: {e}")

    def setup_icon(self):
        try:
            icon_path = os.path.join(os.path.dirname(__file__), "resources", "icon.ico")
            if hasattr(sys, '_MEIPASS'):
                icon_path = os.path.join(sys._MEIPASS, "resources", "icon.ico")
            if os.path.exists(icon_path):
                self.root.iconbitmap(default=icon_path)
        except Exception as e:
            logger.warning(f"Impossibile caricare icona: {e}")

    def _setup_ui_layout(self):
        self.notebook = ttk.Notebook(self.root, style='Main.TNotebook')
        self.notebook.pack(expand=True, fill='both', padx=15, pady=15)
        self.dashboard_tab = ttk.Frame(self.notebook, style='Card.TFrame')
        self.processing_tab = ttk.Frame(self.notebook, style='Card.TFrame')
        self.config_tab = ttk.Frame(self.notebook, style='Card.TFrame')
        self.help_tab = ttk.Frame(self.notebook, style='Card.TFrame')
        self.notebook.add(self.dashboard_tab, text=' Dashboard ')
        self.notebook.add(self.processing_tab, text=' Elaborazione ')
        self.notebook.add(self.config_tab, text=' Configurazione ')
        self.notebook.add(self.help_tab, text=' Guida ')
    
    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Main.TNotebook', background=COLORS['bg_primary'], borderwidth=0)
        style.configure('Main.TNotebook.Tab', font=FONTS['body_bold'], padding=[20, 10], background=COLORS['bg_secondary'], foreground=COLORS['text_primary'])
        style.map('Main.TNotebook.Tab', background=[('selected', COLORS['accent'])], foreground=[('selected', COLORS['bg_primary'])])
        style.configure('Card.TFrame', background=COLORS['bg_primary'])
        style.configure('TLabelframe', background=COLORS['bg_primary'], bordercolor=COLORS['border'])
        style.configure('TLabelframe.Label', font=FONTS['subheading'], foreground=COLORS['text_primary'], background=COLORS['bg_primary'])
        style.configure('TLabel', background=COLORS['bg_primary'], font=FONTS['body'], foreground=COLORS['text_primary'])
        style.configure('Header.TLabel', font=FONTS['heading'], foreground=COLORS['accent'])
        style.configure('Muted.TLabel', font=FONTS['small'], foreground=COLORS['text_secondary'])
        style.configure('TButton', font=FONTS['body'], padding=[15, 8])
        style.configure('Accent.TButton', font=FONTS['body_bold'])
        style.map('TButton', background=[('active', COLORS['accent_hover'])], foreground=[('active', COLORS['bg_primary'])])
        style.configure('TEntry', font=FONTS['body'], padding=8)
        style.configure('Treeview', font=FONTS['body'], rowheight=30, background=COLORS['bg_primary'], fieldbackground=COLORS['bg_primary'])
        style.configure('Treeview.Heading', font=FONTS['body_bold'], background=COLORS['bg_secondary'], foreground=COLORS['text_primary'])
        style.map('Treeview', background=[('selected', COLORS['accent'])], foreground=[('selected', COLORS['bg_primary'])])
        style.configure('TSeparator', background=COLORS['border'])
        
        # Stile Barra di Progresso Verde
        style.configure("Green.Horizontal.TProgressbar", 
                        troughcolor=COLORS['bg_tertiary'], 
                        background=COLORS['success'], 
                        thickness=20, 
                        borderwidth=0)

    def _setup_drag_drop(self):
        if hasattr(self.root, 'drop_target_register'):
            try:
                # Bypass UAC per Drag & Drop se su Windows ed elevato
                if sys.platform == 'win32':
                    try:
                        import ctypes
                        from ctypes import wintypes
                        
                        # Definizioni Windows API
                        WM_DROPFILES = 0x0233
                        WM_COPYDATA = 0x004A
                        WM_COPYGLOBALDATA = 0x0049
                        MSGFLT_ALLOW = 1
                        
                        change_msg_filter = ctypes.windll.user32.ChangeWindowMessageFilterEx
                        hwnd = self.root.winfo_id()
                        
                        # Verifica se hwnd è un intero valido (non un mock durante i test)
                        if isinstance(hwnd, int):
                            change_msg_filter(hwnd, WM_DROPFILES, MSGFLT_ALLOW, None)
                            change_msg_filter(hwnd, WM_COPYDATA, MSGFLT_ALLOW, None)
                            change_msg_filter(hwnd, WM_COPYGLOBALDATA, MSGFLT_ALLOW, None)
                            logger.info("UAC Message Filter bypass applicato per Drag & Drop")
                        else:
                            logger.debug("Bypass UAC saltato: hwnd non è un intero (probabile mock in test)")
                    except Exception as e:
                        logger.warning(f"Impossibile applicare bypass UAC: {e}")

                target_widget = getattr(self, 'hint_frame', self.processing_tab)
                target_widget.drop_target_register(DND_FILES)
                target_widget.dnd_bind('<<Drop>>', self._on_drop)
                for child in target_widget.winfo_children():
                    child.drop_target_register(DND_FILES)
                    child.dnd_bind('<<Drop>>', self._on_drop)
                logger.info(f"Drag & Drop registrato su {target_widget.__class__.__name__} e figli.")
            except Exception as e:
                logger.warning(f"Drag & Drop non disponibile: {e}", exc_info=True)

    def _setup_dashboard_tab(self):
        main_frame = ttk.Frame(self.dashboard_tab, style='Card.TFrame', padding=20)
        main_frame.pack(fill='both', expand=True)
        header_frame = ttk.Frame(main_frame, style='Card.TFrame')
        header_frame.pack(fill='x', pady=(0, 20))
        ttk.Label(header_frame, text="Dashboard", style='Header.TLabel').pack(side='left')
        self.clock_label = ttk.Label(header_frame, text="", style='Muted.TLabel')
        self.clock_label.pack(side='right')
        self._update_clock()
        cards_frame = ttk.Frame(main_frame, style='Card.TFrame')
        cards_frame.pack(fill='x', pady=10)
        cards_frame.columnconfigure((0, 1, 2, 3), weight=1, uniform='card')
        self._create_stat_card(cards_frame, 0, "Licenza", "license_status", "Verificando...")
        self._create_stat_card(cards_frame, 1, "File Elaborati", "files_count", "0")
        self._create_stat_card(cards_frame, 2, "Pagine Totali", "pages_count", "0")
        self._create_stat_card(cards_frame, 3, "Regole Attive", "rules_count", "0")
        actions_frame = ttk.LabelFrame(main_frame, text=" Azioni Rapide ", padding=15)
        actions_frame.pack(fill='x', pady=20)
        btn_frame = ttk.Frame(actions_frame)
        btn_frame.pack()
        ttk.Button(btn_frame, text="Seleziona PDF", command=self._quick_select_pdf).pack(side='left', padx=10)
        ttk.Button(btn_frame, text="Configura Regole", command=lambda: self.notebook.select(self.config_tab)).pack(side='left', padx=10)
        ttk.Button(btn_frame, text="Apri Utility ROI", command=self._launch_roi_utility).pack(side='left', padx=10)
        ttk.Separator(btn_frame, orient='vertical').pack(side='left', fill='y', padx=15, pady=5)
        self.restore_btn = ttk.Button(btn_frame, text="Ripristina Sessione", command=self._restore_session, state='disabled')
        self.restore_btn.pack(side='left', padx=10)
        license_frame = ttk.LabelFrame(main_frame, text=" Informazioni Licenza ", padding=15)
        license_frame.pack(fill='x', pady=10)
        self.license_info_text = tk.Text(license_frame, height=5, font=FONTS['mono'], bg=COLORS['bg_secondary'], fg=COLORS['text_primary'], relief='flat', state='disabled', wrap='word')
        self.license_info_text.pack(fill='x')
        recent_frame = ttk.LabelFrame(main_frame, text=" Attivita' Recente ", padding=15)
        recent_frame.pack(fill='both', expand=True, pady=10)
        self.recent_log = scrolledtext.ScrolledText(recent_frame, height=8, font=FONTS['mono'], bg=COLORS['bg_secondary'], fg=COLORS['text_primary'], relief='flat', state='disabled', wrap='word')
        self.recent_log.pack(fill='both', expand=True)
        self.recent_log.tag_config("INFO", foreground=COLORS['text_primary'])
        self.recent_log.tag_config("SUCCESS", foreground=COLORS['success'])
        self.recent_log.tag_config("WARNING", foreground=COLORS['warning'])
        self.recent_log.tag_config("ERROR", foreground=COLORS['danger'])

    def _create_stat_card(self, parent, col, title, var_name, initial_value):
        card = tk.Frame(parent, bg=COLORS['bg_secondary'], relief='flat', bd=0, highlightthickness=1, highlightbackground=COLORS['border'])
        card.grid(row=0, column=col, padx=8, pady=5, sticky='nsew')
        tk.Label(card, text=title, font=FONTS['small'], bg=COLORS['bg_secondary'], fg=COLORS['text_secondary']).pack(pady=(15, 5))
        value_label = tk.Label(card, text=initial_value, font=('Segoe UI', 18, 'bold'), bg=COLORS['bg_secondary'], fg=COLORS['accent'])
        value_label.pack(pady=(0, 15))
        setattr(self, f'{var_name}_label', value_label)

    def _update_clock(self):
        self.clock_label.config(text=datetime.now().strftime("%d/%m/%Y  %H:%M:%S"))
        self.root.after(1000, self._update_clock)

    def _quick_select_pdf(self):
        self.notebook.select(self.processing_tab)
        self.root.after(100, self._select_pdf)

    def _setup_processing_tab(self):
        main_frame = ttk.Frame(self.processing_tab, style='Card.TFrame', padding=20)
        main_frame.pack(fill='both', expand=True)
        ttk.Label(main_frame, text="Elaborazione PDF", style='Header.TLabel').pack(anchor='w', pady=(0, 20))
        input_frame = ttk.LabelFrame(main_frame, text=" Input ", padding=15)
        input_frame.pack(fill='x', pady=(0, 15))
        odc_frame = ttk.Frame(input_frame)
        odc_frame.pack(fill='x', pady=5)
        ttk.Label(odc_frame, text="Codice ODC (default):", font=FONTS['body_bold'], width=20).pack(side='left')
        self.odc_var = tk.StringVar(value="5400")
        odc_entry = ttk.Entry(odc_frame, textvariable=self.odc_var, width=30, font=FONTS['body'])
        odc_entry.pack(side='left', padx=10)
        file_frame = ttk.Frame(input_frame)
        file_frame.pack(fill='x', pady=10)
        ttk.Button(file_frame, text="Seleziona PDF...", command=self._select_pdf).pack(side='left', padx=(0, 5))
        ttk.Button(file_frame, text="Seleziona Cartella...", command=self._select_folder).pack(side='left')
        self.pdf_path_label = ttk.Label(file_frame, text="Nessun file selezionato", style='Muted.TLabel', font=FONTS['body'])
        self.pdf_path_label.pack(side='left', padx=15)
        self.hint_frame = tk.Frame(input_frame, bg=COLORS['bg_tertiary'], relief='flat')
        self.hint_frame.pack(fill='x', pady=10)
        tk.Label(self.hint_frame, text="Trascina file o cartelle qui per avviare l'elaborazione automatica", font=FONTS['small'], bg=COLORS['bg_tertiary'], fg=COLORS['text_secondary'], pady=10).pack()
        self.progress_frame = ttk.LabelFrame(main_frame, text=" Progresso ", padding=15)
        self.progress_frame.pack(fill='x', pady=10)
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(self.progress_frame, variable=self.progress_var, maximum=100, length=400, mode='determinate', style="Green.Horizontal.TProgressbar")
        self.progress_bar.pack(fill='x', pady=5)
        self.progress_label = ttk.Label(self.progress_frame, text="In attesa...", style='Muted.TLabel')
        self.progress_label.pack()
        log_frame = ttk.LabelFrame(main_frame, text=" Log Elaborazione ", padding=15)
        log_frame.pack(fill='both', expand=True, pady=10)
        self.log_area = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, state='disabled', font=FONTS['mono'], bg=COLORS['bg_secondary'], fg=COLORS['text_primary'], relief='flat')
        self.log_area.pack(expand=True, fill='both')
        for tag, color in [("ERROR", COLORS['danger']), ("WARNING", '#E67E22'), ("SUCCESS", COLORS['success']), ("PROGRESS", COLORS['accent']), ("HEADER", COLORS['accent'])]:
            self.log_area.tag_config(tag, foreground=color)
    
    def _setup_config_tab(self):
        main_frame = ttk.Frame(self.config_tab, style='Card.TFrame', padding=20)
        main_frame.pack(fill='both', expand=True)
        ttk.Label(main_frame, text="Configurazione", style='Header.TLabel').pack(anchor='w', pady=(0, 20))
        path_frame = ttk.LabelFrame(main_frame, text=" Tesseract OCR ", padding=15)
        path_frame.pack(fill='x', pady=(0, 15))
        path_frame.columnconfigure(1, weight=1)
        ttk.Label(path_frame, text="Percorso:", font=FONTS['body_bold']).grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.tesseract_path_var = tk.StringVar()
        self.tesseract_path_var.trace("w", self._on_tesseract_path_change)
        ttk.Entry(path_frame, textvariable=self.tesseract_path_var, font=FONTS['body']).grid(row=0, column=1, padx=5, pady=5, sticky='ew')
        btn_frame = ttk.Frame(path_frame)
        btn_frame.grid(row=0, column=2, padx=5)
        ttk.Button(btn_frame, text="Sfoglia", command=self._browse_tesseract).pack(side='left', padx=2)
        ttk.Button(btn_frame, text="Auto-Rileva", command=self._auto_detect_tesseract).pack(side='left', padx=2)
        rules_frame = ttk.LabelFrame(main_frame, text=" Regole di Classificazione ", padding=15)
        rules_frame.pack(expand=True, fill='both', pady=10)
        rules_frame.columnconfigure(1, weight=1)
        rules_frame.rowconfigure(0, weight=1)
        tree_container = ttk.Frame(rules_frame)
        tree_container.grid(row=0, column=0, sticky='nsew', padx=(0, 10))
        tree_container.columnconfigure(0, weight=1)
        tree_container.rowconfigure(0, weight=1)
        self.rules_tree = ttk.Treeview(tree_container, columns=("ColorCode", "Category", "Suffix"), show='headings', height=12)
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
        self.rule_details_frame = ttk.LabelFrame(rules_frame, text=" Dettagli Regola ", padding=15)
        self.rule_details_frame.grid(row=0, column=1, sticky='nsew')
        self.rule_details_frame.columnconfigure(0, weight=1)
        ttk.Label(self.rule_details_frame, text="Keywords:", font=FONTS['body_bold']).grid(row=0, column=0, sticky='w', pady=(0, 5))
        self.keywords_text = tk.Text(self.rule_details_frame, height=5, font=FONTS['body'], bg=COLORS['bg_secondary'], fg=COLORS['text_primary'], relief='flat', state='disabled', wrap='word')
        self.keywords_text.grid(row=1, column=0, sticky='nsew', pady=(0, 15))
        ttk.Label(self.rule_details_frame, text="Aree ROI:", font=FONTS['body_bold']).grid(row=2, column=0, sticky='w', pady=(0, 5))
        self.roi_details_var = tk.StringVar()
        ttk.Label(self.rule_details_frame, textvariable=self.roi_details_var, style='Muted.TLabel').grid(row=3, column=0, sticky='w')
        buttons_frame = ttk.Frame(rules_frame)
        buttons_frame.grid(row=0, column=2, sticky='n', padx=(10, 0))
        ttk.Button(buttons_frame, text="Aggiungi", command=self._add_rule).pack(fill='x', pady=3)
        ttk.Button(buttons_frame, text="Modifica", command=self._modify_rule).pack(fill='x', pady=3)
        ttk.Button(buttons_frame, text="Rimuovi", command=self._remove_rule).pack(fill='x', pady=3)
        ttk.Separator(buttons_frame, orient='horizontal').pack(fill='x', pady=15)
        ttk.Button(buttons_frame, text="Utility ROI", command=self._launch_roi_utility).pack(fill='x', pady=3)

    def _setup_help_tab(self):
        main_frame = ttk.Frame(self.help_tab, style='Card.TFrame', padding=20)
        main_frame.pack(fill='both', expand=True)
        
        header_frame = ttk.Frame(main_frame, style='Card.TFrame')
        header_frame.pack(fill='x', pady=(0, 15))
        ttk.Label(header_frame, text="Guida all'Uso", style='Header.TLabel').pack(side='left')
        
        ttk.Button(header_frame, text="Apri Cartella Dati", 
                  command=lambda: os.startfile(APP_DATA_DIR)).pack(side='right')

        # Sottoschede per la Guida
        help_notebook = ttk.Notebook(main_frame)
        help_notebook.pack(fill='both', expand=True)

        # Tab: Introduzione
        intro_frame = ttk.Frame(help_notebook, style='Card.TFrame', padding=15)
        help_notebook.add(intro_frame, text=" Introduzione ")
        intro_text = """
Benvenuto in Intelleo PDF Splitter. 
Questa applicazione ti permette di dividere documenti PDF multipagina in base a regole OCR predefinite.

FUNZIONALITÀ PRINCIPALI:
• Suddivisione automatica basata su parole chiave.
• Rilevamento aree specifiche (ROI) tramite OCR Tesseract.
• Revisione manuale dei file non riconosciuti.
• Supporto Drag & Drop per file e cartelle.
"""
        st = scrolledtext.ScrolledText(intro_frame, wrap='word', font=FONTS['body'], bg=COLORS['bg_secondary'], relief='flat')
        st.insert('1.0', intro_text)
        st.config(state='disabled')
        st.pack(fill='both', expand=True)

        # Tab: Configurazione
        setup_frame = ttk.Frame(help_notebook, style='Card.TFrame', padding=15)
        help_notebook.add(setup_frame, text=" Configurazione ")
        setup_text = """
1. TESSERACT OCR:
Assicurati che Tesseract sia installato e il percorso sia corretto nella tab 'Configurazione'.

2. REGOLE DI CLASSIFICAZIONE:
Le regole definiscono come il software riconosce i documenti. Ogni regola ha:
• Nome Categoria: Identifica il tipo di documento.
• Suffisso: Verrà aggiunto al nome del file generato.
• Keywords: Parole che il software cercherà nel testo estratto.
• Colore: Usato per identificare visivamente la regola.

3. UTILITY ROI:
Usa l'Utility ROI per disegnare rettangoli sulle zone del PDF dove il software deve cercare le parole chiave. Questo aumenta drasticamente la precisione.
"""
        st = scrolledtext.ScrolledText(setup_frame, wrap='word', font=FONTS['body'], bg=COLORS['bg_secondary'], relief='flat')
        st.insert('1.0', setup_text)
        st.config(state='disabled')
        st.pack(fill='both', expand=True)

        # Tab: Elaborazione
        proc_frame = ttk.Frame(help_notebook, style='Card.TFrame', padding=15)
        help_notebook.add(proc_frame, text=" Elaborazione ")
        proc_text = """
1. Trascina i file PDF o le cartelle nella zona tratteggiata della tab 'Elaborazione'.
2. Oppure usa i pulsanti 'Seleziona PDF' o 'Seleziona Cartella'.
3. Inserisci il codice ODC desiderato (es. 5400).
4. Il software processerà ogni pagina e creerà nuovi file nella stessa cartella dell'originale.
5. Se una pagina non viene riconosciuta, al termine apparirà una finestra di 'Revisione Manuale'.
"""
        st = scrolledtext.ScrolledText(proc_frame, wrap='word', font=FONTS['body'], bg=COLORS['bg_secondary'], relief='flat')
        st.insert('1.0', proc_text)
        st.config(state='disabled')
        st.pack(fill='both', expand=True)

    def _display_license_info(self):
        try:
            payload = license_validator.get_license_info()
            hw_id = license_validator.get_hardware_id()
            
            # Carica ultimo accesso dal config
            config = config_manager.load_config()
            last_access = config.get('last_access', 'N/A')

            if payload:
                self.license_status_label.config(text="[OK] Valida", fg=COLORS['success'])
                info_text = (f"Cliente: {payload.get('Cliente', 'N/A')}\n"
                           f"Scadenza: {payload.get('Scadenza Licenza', 'N/A')}\n"
                           f"Hardware ID: {hw_id}\n"
                           f"Ultimo Accesso: {last_access}")
                
                self.license_info_text.config(state='normal')
                self.license_info_text.delete('1.0', 'end')
                self.license_info_text.insert('1.0', info_text)
                self.license_info_text.config(state='disabled')
            else:
                self.license_status_label.config(text="[!] Non trovata", fg=COLORS['warning'])
                info_text = (f"Hardware ID: {hw_id}\n"
                           f"Ultimo Accesso: {last_access}")
                self.license_info_text.config(state='normal')
                self.license_info_text.delete('1.0', 'end')
                self.license_info_text.insert('1.0', info_text)
                self.license_info_text.config(state='disabled')
        except Exception as e:
            self.license_status_label.config(text="[X] Errore", fg=COLORS['danger'])

    def _add_recent_log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.recent_log.config(state='normal')
        self.recent_log.insert('end', f"[{timestamp}] {message}\n", level)
        self.recent_log.config(state='disabled')
        self.recent_log.see('end')

    def _add_log_message(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_area.config(state='normal')
        if level == "PROGRESS":
            last_idx = self.log_area.index("end-2l")
            last_line = self.log_area.get(last_idx, "end-1c")
            if "Elaborazione pagina" in last_line:
                self.log_area.delete(last_idx, "end-1c")
        prefix = ""
        if level == "ERROR": prefix = "[X] "
        elif level == "WARNING": prefix = "[!] "
        elif level == "SUCCESS": prefix = "[OK] "
        elif level == "HEADER": prefix = "=== "
        self.log_area.insert('end', f"[{timestamp}] {prefix}{message}\n", level)
        self.log_area.config(state='disabled')
        self.log_area.see('end')
        if level in ["SUCCESS", "ERROR", "WARNING"]:
            self._add_recent_log(message, level)

    def _process_log_queue(self):
        try:
            while True:
                item = self.log_queue.get_nowait()
                if isinstance(item, tuple):
                    self._add_log_message(item[0], item[1])
                elif isinstance(item, dict):
                    action = item.get('action')
                    if action == 'show_unknown_dialog':
                        self._show_unknown_dialog(item['files'], item.get('odc', ''))
                    elif action == 'update_progress':
                        self.progress_var.set(item.get('value', 0))
                        self.progress_label.config(text=item.get('text', ''))
                    elif action == 'increment_pages':
                        self.pages_processed_count += item.get('count', 1)
                        self.pages_count_label.config(text=str(self.pages_processed_count))
                else:
                    self._add_log_message(str(item))
        except queue.Empty:
            pass
        finally:
            self.root.after(50, self._process_log_queue)

    def _check_for_updates(self):
        if os.path.exists(SIGNAL_FILE):
            try:
                os.remove(SIGNAL_FILE)
                self.load_settings()
                self._add_log_message("Configurazione aggiornata dall'utility ROI", "SUCCESS")
            except OSError as e:
                logger.error(f"Gestione signal file: {e}")
        self.root.after(150, self._check_for_updates)

    def _on_drop(self, event):
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
        odc = simpledialog.askstring("Input ODC", "Inserisci il codice ODC:", parent=self.root)
        if odc:
            self.odc_var.set(odc)
            self.notebook.select(self.processing_tab)
            self._start_processing()

    def _select_pdf(self):
        paths = filedialog.askopenfilenames(title="Seleziona file PDF", filetypes=[("PDF Files", "*.pdf")])
        if paths:
            self.pdf_files = list(paths)
            self.pdf_path_label.config(text=f"{len(self.pdf_files)} file selezionati" if len(self.pdf_files) > 1 else os.path.basename(self.pdf_files[0]))
            self._start_processing()

    def _select_folder(self):
        folder_path = filedialog.askdirectory(title="Seleziona Cartella")
        if not folder_path: return
        found_pdfs = [os.path.join(r, f) for r, d, fs in os.walk(folder_path) for f in fs if f.lower().endswith('.pdf')]
        if found_pdfs:
            self.pdf_files = found_pdfs
            self.pdf_path_label.config(text=f"{len(found_pdfs)} file trovati")
            self.notebook.select(self.processing_tab)
            self._start_processing()
        else:
            messagebox.showinfo("Info", "Nessun file PDF trovato.")
    
    def _update_restore_button_state(self):
        """Aggiorna lo stato del pulsante di ripristino."""
        if os.path.exists(SESSION_FILE):
            self.restore_btn.config(state='normal')
        else:
            self.restore_btn.config(state='disabled')

    def _check_for_restore(self):
        """Verifica se esiste una sessione da ripristinare."""
        self._update_restore_button_state()
        if os.path.exists(SESSION_FILE):
            if messagebox.askyesno("Ripristino Sessione", "Trovata una sessione precedente non completata.\nVuoi ripristinare i file da revisionare?"):
                 self._restore_session()

    def _clear_session(self):
        """Rimuove il file di sessione."""
        if os.path.exists(SESSION_FILE):
            try:
                os.remove(SESSION_FILE)
            except OSError as e:
                logger.error(f"Errore rimozione session file: {e}")
        self._update_restore_button_state()

    def _restore_session(self):
        """Ripristina la sessione precedente."""
        if not os.path.exists(SESSION_FILE):
            return
        
        try:
            with open(SESSION_FILE, 'r') as f:
                data = json.load(f)
            
            if data:
                # Recupera l'ODC se salvato, o chiedi
                odc = "Unknown" # TODO: salvare ODC nella sessione
                self._show_unknown_dialog(data, odc)
            else:
                self._clear_session()
                
        except Exception as e:
            logger.error(f"Errore ripristino sessione: {e}")
            messagebox.showerror("Errore", f"Impossibile ripristinare la sessione:\n{e}")
            self._clear_session()

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
        self._add_log_message(f"File da elaborare: {len(self.pdf_files)}", "INFO")
        self._add_log_message("-" * 60, "INFO")
        self.processing_start_time = datetime.now()
        thread = threading.Thread(target=self._processing_worker, args=(list(self.pdf_files), self.odc_var.get(), self.config))
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

        UnknownFilesReviewDialog(self.root, files, on_close)

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
        dialog.geometry("500x400")  # Aumentato leggermente
        dialog.minsize(450, 350)
        dialog.resizable(True, True)  # Abilitato ridimensionamento
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