import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext, colorchooser, simpledialog
# Removed unused imports: PIL (Image, ImageTk, ImageDraw)
import config_manager
import pdf_processor
import subprocess
import os
import sys
import threading
import queue
import license_validator

# Un file semplice usato come segnale per comunicare tra l'utility e l'app principale
SIGNAL_FILE = ".update_signal"

class MainApp:
    """
    Applicazione principale per la divisione di file PDF basata su regole OCR.
    """
    def __init__(self, root, auto_file_path=None):
        self.root = root
        self.root.title("PDF Splitter")
        self.root.state('zoomed')

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(expand=True, fill='both', padx=10, pady=10)

        self.processing_tab = ttk.Frame(self.notebook)
        self.config_tab = ttk.Frame(self.notebook)

        self.notebook.add(self.processing_tab, text='Elaborazione')
        self.notebook.add(self.config_tab, text='Configurazione')

        self.config = {}
        self.pdf_path = ""
        self.log_queue = queue.Queue()
        # Removed unused color_icons cache

        self.setup_config_tab()
        self.setup_processing_tab()
        self.display_license_info() # Aggiunta per mostrare la licenza

        self.load_settings()
        self.root.after(100, self.process_log_queue)
        # Avvia il controllo per gli aggiornamenti dalla utility ROI (intervallo ridotto a 200ms)
        self.root.after(200, self.check_for_updates)

        # Gestione avvio automatico con file da CLI
        if auto_file_path and os.path.exists(auto_file_path):
             self.root.after(500, lambda: self.handle_cli_start(auto_file_path))

    def handle_cli_start(self, file_path):
        """Gestisce l'avvio con file passato da riga di comando."""
        self.pdf_path = file_path
        self.pdf_path_label.config(text=os.path.basename(file_path))

        # Chiedi ODC
        odc = simpledialog.askstring("Input ODC", "Inserisci il codice ODC (es. 5400xxxxxx):", parent=self.root)

        if odc:
            self.odc_var.set(odc)
            # Avvia elaborazione
            self.start_processing()
        else:
            messagebox.showinfo("Annullato", "Elaborazione annullata.")

    def check_for_updates(self):
        """
        Controlla se l'utility ROI ha creato il file segnale.
        Se esiste, ricarica le impostazioni e rimuove il file.
        """
        if os.path.exists(SIGNAL_FILE):
            try:
                os.remove(SIGNAL_FILE)
                self.load_settings()
                self.add_log_message("Configurazione aggiornata dall'utility ROI.")
            except OSError as e:
                print(f"Errore nella gestione del file segnale: {e}")
        # Ripianifica il controllo con frequenza più alta per maggiore reattività
        self.root.after(200, self.check_for_updates)

    # REMOVED: _on_details_resize (Text widget handles wrapping automatically)

    def display_license_info(self):
        try:
            payload = license_validator.get_license_info()
            if payload:
                cliente = payload.get('Cliente', 'N/A')
                scadenza = payload.get('Scadenza Licenza', 'N/A')
                hw_id = payload.get('Hardware ID', 'N/A')

                info_text = (f"=== INFO LICENZA ===\n"
                             f"Cliente: {cliente}\n"
                             f"Scadenza: {scadenza}\n"
                             f"Hardware ID: {hw_id}\n"
                             f"====================")
                self.add_log_message(info_text)
            else:
                self.add_log_message("File licenza 'config.dat' non trovato o illeggibile.")

        except Exception as e:
            self.add_log_message(f"Errore nel caricamento info licenza: {e}")

    def setup_processing_tab(self):
        input_frame = ttk.LabelFrame(self.processing_tab, text="Input")
        input_frame.pack(fill=tk.X, padx=10, pady=10)
        ttk.Label(input_frame, text="ODC:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.odc_var = tk.StringVar(value="5400") # Valore predefinito
        ttk.Entry(input_frame, textvariable=self.odc_var, width=40).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(input_frame, text="Seleziona PDF...", command=self.select_pdf).grid(row=1, column=0, padx=5, pady=5)
        self.pdf_path_label = ttk.Label(input_frame, text="Nessun file selezionato")
        self.pdf_path_label.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)

        # REMOVED: start_button

        log_frame = ttk.LabelFrame(self.processing_tab, text="Log")
        log_frame.pack(expand=True, fill='both', padx=10, pady=10)
        self.log_area = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, state='disabled', height=15)
        self.log_area.pack(expand=True, fill='both', padx=5, pady=5)

    def select_pdf(self):
        path = filedialog.askopenfilename(title="Seleziona file PDF", filetypes=[("PDF Files", "*.pdf")])
        if path:
            self.pdf_path = path
            self.pdf_path_label.config(text=os.path.basename(path))
            # Auto-start processing
            self.start_processing()

    def add_log_message(self, message):
        self.log_area.config(state='normal')
        self.log_area.insert(tk.END, message + "\n")
        self.log_area.config(state='disabled')
        self.log_area.yview(tk.END)

    def process_log_queue(self):
        try:
            while True:
                message = self.log_queue.get_nowait()
                self.add_log_message(message)
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.process_log_queue)

    def start_processing(self):
        odc_input = self.odc_var.get().strip()

        # Validazione dell'input ODC
        if not odc_input.startswith("5400"):
            messagebox.showerror("Errore ODC", "L'ODC deve iniziare con '5400'.")
            return

        remaining_digits = odc_input[4:]
        if not (remaining_digits.isdigit() and len(remaining_digits) == 6):
            messagebox.showerror("Errore ODC", "Dopo '5400', devi inserire esattamente 6 cifre numeriche.")
            return

        full_odc = odc_input

        if not self.pdf_path:
            messagebox.showerror("Errore", "Per favore, seleziona un file PDF.")
            return

        self.log_area.config(state='normal')
        self.log_area.delete('1.0', tk.END)
        self.log_area.config(state='disabled')

        thread = threading.Thread(target=self.processing_worker, args=(self.pdf_path, full_odc, self.config))
        thread.daemon = True
        thread.start()

    def processing_worker(self, pdf_path, odc, config):
        def progress_callback(message):
            self.log_queue.put(message)
        success, message = pdf_processor.process_pdf(pdf_path, odc, config, progress_callback)
        if not success:
            self.log_queue.put(f"ERRORE FINALE: {message}")

        # Reset ODC to default on main thread after processing finishes
        self.root.after(0, lambda: self.odc_var.set("5400"))

    # REMOVED: unused create_color_swatch

    def setup_config_tab(self):
        path_frame = ttk.LabelFrame(self.config_tab, text="Impostazioni Generali")
        path_frame.pack(fill=tk.X, padx=10, pady=10)
        path_frame.columnconfigure(1, weight=1)
        ttk.Label(path_frame, text="Path Tesseract:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.tesseract_path_var = tk.StringVar()
        self.tesseract_path_var.trace("w", self.on_tesseract_path_change) # Auto-save trigger

        ttk.Entry(path_frame, textvariable=self.tesseract_path_var).grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)
        ttk.Button(path_frame, text="Sfoglia...", command=self.browse_tesseract).grid(row=0, column=2, padx=5, pady=5)
        ttk.Button(path_frame, text="Rileva Automaticamente", command=self.auto_detect_tesseract).grid(row=0, column=3, padx=5, pady=5)

        rules_frame = ttk.LabelFrame(self.config_tab, text="Regole di Classificazione")
        rules_frame.pack(expand=True, fill='both', padx=10, pady=10)

        # CHANGED: Weights to stabilize layout
        rules_frame.columnconfigure(1, weight=1)
        rules_frame.columnconfigure(0, weight=0)
        rules_frame.rowconfigure(0, weight=1)

        # -- Contenitore per Treeview e Scrollbar --
        tree_container = ttk.Frame(rules_frame)
        tree_container.grid(row=0, column=0, sticky='nsew', padx=5, pady=5)
        tree_container.columnconfigure(0, weight=1)
        tree_container.rowconfigure(0, weight=1)

        # Added "ColorSwatch" column
        self.rules_tree = ttk.Treeview(tree_container, columns=("ColorCode", "Category", "Suffix"), show='headings')

        # Make the "ColorCode" column hold the visual swatch
        self.rules_tree.heading("ColorCode", text="Colore")
        self.rules_tree.column("ColorCode", width=80, anchor='center', stretch=False)

        self.rules_tree.heading("Category", text="Categoria")
        self.rules_tree.column("Category", width=150)
        self.rules_tree.heading("Suffix", text="Suffisso")
        self.rules_tree.column("Suffix", width=100)

        self.rules_tree.grid(row=0, column=0, sticky='nsew')
        # Scrollbar
        scrollbar = ttk.Scrollbar(tree_container, orient="vertical", command=self.rules_tree.yview)
        self.rules_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky='ns')
        # -- Pannello Dettagli Regola --
        self.rule_details_frame = ttk.LabelFrame(rules_frame, text="Dettagli Regola")
        self.rule_details_frame.grid(row=0, column=1, sticky='nsew', padx=(0, 5), pady=5)
        self.rule_details_frame.columnconfigure(0, weight=1)

        # REMOVED: keywords_details_var
        self.roi_details_var = tk.StringVar()

        ttk.Label(self.rule_details_frame, text="Keywords:", font="-weight bold").grid(row=0, column=0, sticky='w', padx=5, pady=(5, 0))

        # CHANGED: Replaced Label with Text widget for wrapping
        self.keywords_text = tk.Text(self.rule_details_frame, height=5, width=40, wrap=tk.WORD, state=tk.DISABLED, bg=self.root.cget("bg"), relief=tk.GROOVE)
        self.keywords_text.grid(row=1, column=0, sticky='nsew', padx=5, pady=(0, 10))

        ttk.Label(self.rule_details_frame, text="ROI:", font="-weight bold").grid(row=2, column=0, sticky='w', padx=5, pady=(5, 0))
        ttk.Label(self.rule_details_frame, textvariable=self.roi_details_var, justify=tk.LEFT).grid(row=3, column=0, sticky='w', padx=5, pady=(0, 10))

        # REMOVED: Binding for resize

        # -- Contenitore Pulsanti --
        buttons_container = ttk.Frame(rules_frame)
        buttons_container.grid(row=0, column=2, sticky='ns', padx=(5, 0), pady=5)
        ttk.Button(buttons_container, text="Aggiungi...", command=self.add_rule).pack(fill=tk.X, pady=2)
        ttk.Button(buttons_container, text="Modifica...", command=self.modify_rule).pack(fill=tk.X, pady=2)
        ttk.Button(buttons_container, text="Rimuovi", command=self.remove_rule).pack(fill=tk.X, pady=2)
        ttk.Separator(buttons_container, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        ttk.Button(buttons_container, text="Avvia Utility ROI", command=self.launch_roi_utility).pack(fill=tk.X, pady=2)
        self.rules_tree.bind("<<TreeviewSelect>>", self.update_rule_details_panel)

    def on_tesseract_path_change(self, *args):
        # Update config directly
        self.config["tesseract_path"] = self.tesseract_path_var.get()
        self.auto_save_settings()

    def browse_tesseract(self):
        path = filedialog.askopenfilename(title="Seleziona l'eseguibile di Tesseract", filetypes=[("Executable", "*.exe")])
        if path:
            self.tesseract_path_var.set(path)
            # This will trigger trace which saves

    def auto_detect_tesseract(self):
        search_paths = [
            os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "Tesseract-OCR", "tesseract.exe"),
            os.path.join(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"), "Tesseract-OCR", "tesseract.exe"),
            os.path.join(os.environ.get("LOCALAPPDATA"), "Tesseract-OCR", "tesseract.exe")
        ]
        for path in search_paths:
            if os.path.exists(path):
                self.tesseract_path_var.set(path)
                messagebox.showinfo("Successo", f"Tesseract trovato in:\n{path}")
                return
        messagebox.showwarning("Non Trovato", "Impossibile trovare Tesseract. Indicalo manualmente.")

    def populate_rules_tree(self):
        # Pulisce sia la Treeview che il pannello dei dettagli
        self.keywords_text.config(state=tk.NORMAL)
        self.keywords_text.delete("1.0", tk.END)
        self.keywords_text.config(state=tk.DISABLED)
        self.roi_details_var.set("")
        for item in self.rules_tree.get_children():
            self.rules_tree.delete(item)

        # REMOVED: Loop with tag_names() which caused AttributeError

        # Popola la Treeview con le nuove colonne
        for rule in self.config.get("classification_rules", []):
            color = rule.get("color", "#FFFFFF")
            suffix = rule.get("filename_suffix", rule["category_name"])

            tag_name = f"color_{color}"
            self.rules_tree.tag_configure(tag_name, background=color)

            # Calculate contrast text color
            h = color.lstrip('#')
            try:
                rgb = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
                brightness = (rgb[0] * 299 + rgb[1] * 587 + rgb[2] * 114) / 1000
                text_color = "black" if brightness > 128 else "white"
            except:
                text_color = "black"

            self.rules_tree.tag_configure(tag_name, background=color, foreground=text_color)

            self.rules_tree.insert("", tk.END, values=(color, rule["category_name"], suffix), tags=(tag_name,))

    def update_rule_details_panel(self, event=None):
        selected_item = self.rules_tree.focus()
        if not selected_item:
            self.keywords_text.config(state=tk.NORMAL)
            self.keywords_text.delete("1.0", tk.END)
            self.keywords_text.config(state=tk.DISABLED)
            self.roi_details_var.set("")
            return

        item_values = self.rules_tree.item(selected_item, "values")
        category_name = item_values[1] # La categoria è il secondo valore

        rule = next((r for r in self.config.get("classification_rules", []) if r["category_name"] == category_name), None)

        if rule:
            keywords_str = ", ".join(rule.get("keywords", ["N/A"]))
            rois_count = len(rule.get("rois", []))
            roi_summary = f"[{rois_count} Aree ROI definite]"

            self.keywords_text.config(state=tk.NORMAL)
            self.keywords_text.delete("1.0", tk.END)
            self.keywords_text.insert(tk.END, keywords_str)
            self.keywords_text.config(state=tk.DISABLED)

            self.roi_details_var.set(roi_summary)
        else:
            self.keywords_text.config(state=tk.NORMAL)
            self.keywords_text.delete("1.0", tk.END)
            self.keywords_text.insert(tk.END, "Regola non trovata.")
            self.keywords_text.config(state=tk.DISABLED)
            self.roi_details_var.set("")

    def load_settings(self):
        self.config = config_manager.load_config()
        # Temporarily disable trace to avoid re-saving during load
        if hasattr(self, 'tesseract_path_var'):
            try:
                trace_info = self.tesseract_path_var.trace_vinfo()
                if trace_info:
                    trace_id = trace_info[0][1]
                    self.tesseract_path_var.trace_vdelete("w", trace_id)
            except Exception:
                pass

            self.tesseract_path_var.set(self.config.get("tesseract_path", ""))
            self.tesseract_path_var.trace("w", self.on_tesseract_path_change)

        self.populate_rules_tree()

    def auto_save_settings(self):
        """
        Salva automaticamente le impostazioni su file senza bloccare l'UI.
        """
        try:
            config_manager.save_config(self.config)
            # Optional: visual indicator or log? Keeping it silent for max reactivity.
        except Exception as e:
            # We log error but don't popup to interrupt flow unless critical?
            print(f"Errore Auto-Save: {e}")

    def add_rule(self):
        self.show_rule_editor()

    def modify_rule(self):
        selected_item = self.rules_tree.focus()
        if not selected_item:
            messagebox.showwarning("Nessuna Selezione", "Selezionare una regola da modificare.")
            return
        item_values = self.rules_tree.item(selected_item, "values")
        rule_to_edit = next((r for r in self.config["classification_rules"] if r["category_name"] == item_values[1]), None) # Categoria è al secondo posto
        if rule_to_edit:
            self.show_rule_editor(rule_to_edit)

    def remove_rule(self):
        selected_item = self.rules_tree.focus()
        if not selected_item:
            messagebox.showwarning("Nessuna Selezione", "Selezionare una regola da rimuovere.")
            return
        category_name = self.rules_tree.item(selected_item, "values")[1] # Categoria è al secondo posto
        if messagebox.askyesno("Conferma", f"Sei sicuro di voler rimuovere la regola '{category_name}'?"):
            self.config["classification_rules"] = [r for r in self.config["classification_rules"] if r["category_name"] != category_name]
            self.populate_rules_tree()
            self.auto_save_settings()

    def show_rule_editor(self, rule=None):
        dialog = tk.Toplevel(self.root)
        dialog.title("Modifica Regola" if rule else "Aggiungi Regola")
        dialog.attributes('-topmost', True) # Ensure topmost

        category_var = tk.StringVar(value=rule["category_name"] if rule else "")

        # Suffix handling
        default_suffix = rule.get("filename_suffix", rule["category_name"]) if rule else ""
        suffix_var = tk.StringVar(value=default_suffix)

        keywords_str = ", ".join(rule.get("keywords", [])) if rule else ""
        keywords_var = tk.StringVar(value=keywords_str)
        # Colore di default nero se non specificato
        chosen_color = tk.StringVar(value=rule.get("color", "#000000") if rule else "#000000")

        # Layout
        main_frame = ttk.Frame(dialog, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")

        row = 0
        ttk.Label(main_frame, text="Nome Categoria:").grid(row=row, column=0, padx=5, pady=5, sticky=tk.W)
        category_entry = ttk.Entry(main_frame, textvariable=category_var)
        category_entry.grid(row=row, column=1, columnspan=2, padx=5, pady=5, sticky="ew")
        if rule:
            category_entry.config(state='readonly')

        row += 1
        ttk.Label(main_frame, text="Suffisso File:").grid(row=row, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Entry(main_frame, textvariable=suffix_var).grid(row=row, column=1, columnspan=2, padx=5, pady=5, sticky="ew")

        row += 1
        ttk.Label(main_frame, text="Keywords (separate da virgola):").grid(row=row, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Entry(main_frame, textvariable=keywords_var, width=40).grid(row=row, column=1, columnspan=2, padx=5, pady=5, sticky="ew")

        row += 1
        ttk.Label(main_frame, text="Colore:").grid(row=row, column=0, padx=5, pady=5, sticky=tk.W)
        color_swatch = tk.Label(main_frame, text="      ", bg=chosen_color.get())
        color_swatch.grid(row=row, column=1, padx=5, pady=5, sticky="w")

        def _choose_color():
            color_code = colorchooser.askcolor(title="Scegli un colore", initialcolor=chosen_color.get())
            if color_code and color_code[1]:
                chosen_color.set(color_code[1])
                color_swatch.config(bg=color_code[1])

        ttk.Button(main_frame, text="Scegli...", command=_choose_color).grid(row=row, column=2, padx=5, pady=5)

        row += 1
        ttk.Label(main_frame, text="Aree ROI:").grid(row=row, column=0, padx=5, pady=5, sticky=tk.W)
        roi_count = len(rule.get("rois", [])) if rule else 0
        ttk.Label(main_frame, text=f"[{roi_count} aree definite]").grid(row=row, column=1, columnspan=2, padx=5, pady=5, sticky=tk.W)

        def on_save():
            category_name = category_var.get().strip()
            suffix = suffix_var.get().strip()
            keywords_list = [k.strip() for k in keywords_var.get().split(',') if k.strip()]
            color = chosen_color.get()

            if not category_name or not keywords_list:
                messagebox.showerror("Errore", "Nome categoria e almeno una keyword sono obbligatori.", parent=dialog)
                return

            # Se suffisso è vuoto, usa categoria come default (ma salviamo vuoto? No, meglio esplicito o default)
            # L'utente vuole poterlo modificare. Se lo lascia vuoto, assumiamo che voglia il nome categoria.
            if not suffix:
                suffix = category_name

            new_rule_data = {
                "category_name": category_name,
                "filename_suffix": suffix,
                "keywords": keywords_list,
                "color": color
            }

            if rule: # Modifica
                # Mantieni la chiave 'rotate_roi' e 'rois'
                new_rule_data['rotate_roi'] = rule.get('rotate_roi', 0)
                new_rule_data['rois'] = rule.get('rois', [])
                rule.update(new_rule_data)
            else: # Aggiunta
                if any(r["category_name"] == category_name for r in self.config.get("classification_rules", [])):
                    messagebox.showerror("Errore", "Categoria già esistente.", parent=dialog)
                    return
                new_rule_data["rois"] = [] # Inizializza con una lista vuota di ROI
                self.config.setdefault("classification_rules", []).append(new_rule_data)

            self.populate_rules_tree()
            self.auto_save_settings()
            dialog.destroy()

        row += 1
        ttk.Button(main_frame, text="Salva", command=on_save).grid(row=row, column=0, columnspan=3, pady=10)

    def launch_roi_utility(self):
        script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'roi_utility.py')
        try:
            subprocess.Popen([sys.executable, script_path])
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile avviare l'utility ROI: {e}")

if __name__ == "__main__":
    # --- LICENSE CHECK ---
    is_valid, msg = license_validator.verify_license()
    if not is_valid:
        # Mostra GUI minima per errore se Tk non è ancora avviato
        root = tk.Tk()
        root.withdraw()

        # Copia Hardware ID
        hw_id = license_validator.get_hardware_id()

        err_msg = f"{msg}\n\nIl tuo Hardware ID è:\n{hw_id}\n\n(Copiato negli appunti. Invialo all'amministratore.)"
        root.clipboard_clear()
        root.clipboard_append(hw_id)

        messagebox.showerror("Licenza Non Valida", err_msg)
        sys.exit(1)
    # ---------------------

    if os.path.exists(SIGNAL_FILE):
        os.remove(SIGNAL_FILE) # Pulisce il file segnale all'avvio

    root = tk.Tk()

    # Check CLI args
    cli_file_path = None
    if len(sys.argv) > 1:
        potential_path = sys.argv[1]
        if os.path.exists(potential_path) and potential_path.lower().endswith('.pdf'):
            cli_file_path = potential_path

    app = MainApp(root, auto_file_path=cli_file_path)
    root.mainloop()
