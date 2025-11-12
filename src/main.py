import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext, colorchooser
import config_manager
import pdf_processor
import subprocess
import os
import sys
import threading
import queue

# Un file semplice usato come segnale per comunicare tra l'utility e l'app principale
SIGNAL_FILE = ".update_signal"

class MainApp:
    """
    Applicazione principale per la divisione di file PDF basata su regole OCR.
    """
    def __init__(self, root):
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

        self.setup_config_tab()
        self.setup_processing_tab()
        self.display_license_info() # Aggiunta per mostrare la licenza

        self.load_settings()
        self.root.after(100, self.process_log_queue)
        # Avvia il controllo per gli aggiornamenti dalla utility ROI
        self.root.after(1000, self.check_for_updates)

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
        # Ripianifica il controllo
        self.root.after(1000, self.check_for_updates)

    def _on_details_resize(self, event):
        self.keywords_label.config(wraplength=event.width - 10) # 10px di margine

    def display_license_info(self):
        try:
            with open("infoLicense.txt", "r", encoding="utf-8") as f:
                license_text = f.read()
                self.add_log_message(license_text)
        except FileNotFoundError:
            self.add_log_message("File 'infoLicense.txt' non trovato.")
        except Exception as e:
            self.add_log_message(f"Errore nel caricamento della licenza: {e}")

    def setup_processing_tab(self):
        input_frame = ttk.LabelFrame(self.processing_tab, text="Input")
        input_frame.pack(fill=tk.X, padx=10, pady=10)
        ttk.Label(input_frame, text="ODC:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.odc_var = tk.StringVar(value="5400") # Valore predefinito
        ttk.Entry(input_frame, textvariable=self.odc_var, width=40).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(input_frame, text="Seleziona PDF...", command=self.select_pdf).grid(row=1, column=0, padx=5, pady=5)
        self.pdf_path_label = ttk.Label(input_frame, text="Nessun file selezionato")
        self.pdf_path_label.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)
        start_button = ttk.Button(self.processing_tab, text="Avvia Divisione", command=self.start_processing)
        start_button.pack(pady=10)
        log_frame = ttk.LabelFrame(self.processing_tab, text="Log")
        log_frame.pack(expand=True, fill='both', padx=10, pady=10)
        self.log_area = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, state='disabled', height=15)
        self.log_area.pack(expand=True, fill='both', padx=5, pady=5)

    def select_pdf(self):
        path = filedialog.askopenfilename(title="Seleziona file PDF", filetypes=[("PDF Files", "*.pdf")])
        if path:
            self.pdf_path = path
            self.pdf_path_label.config(text=os.path.basename(path))
            # Non pulire il campo ODC

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

    def setup_config_tab(self):
        path_frame = ttk.LabelFrame(self.config_tab, text="Impostazioni Generali")
        path_frame.pack(fill=tk.X, padx=10, pady=10)
        path_frame.columnconfigure(1, weight=1)
        ttk.Label(path_frame, text="Path Tesseract:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.tesseract_path_var = tk.StringVar()
        ttk.Entry(path_frame, textvariable=self.tesseract_path_var).grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)
        ttk.Button(path_frame, text="Sfoglia...", command=self.browse_tesseract).grid(row=0, column=2, padx=5, pady=5)
        ttk.Button(path_frame, text="Rileva Automaticamente", command=self.auto_detect_tesseract).grid(row=0, column=3, padx=5, pady=5)

        rules_frame = ttk.LabelFrame(self.config_tab, text="Regole di Classificazione")
        rules_frame.pack(expand=True, fill='both', padx=10, pady=10)
        rules_frame.columnconfigure(1, weight=3) # Dà più peso alla colonna dei dettagli
        rules_frame.columnconfigure(0, weight=1)
        rules_frame.rowconfigure(0, weight=1)
        # -- Contenitore per Treeview e Scrollbar --
        tree_container = ttk.Frame(rules_frame)
        tree_container.grid(row=0, column=0, sticky='nsew', padx=5, pady=5)
        tree_container.columnconfigure(0, weight=1)
        tree_container.rowconfigure(0, weight=1)
        self.rules_tree = ttk.Treeview(tree_container, columns=("Color", "Category"), show='headings')
        self.rules_tree.heading("Color", text="Colore")
        self.rules_tree.column("Color", width=60, anchor='center', stretch=False)
        self.rules_tree.heading("Category", text="Categoria")
        self.rules_tree.column("Category", width=150)
        self.rules_tree.grid(row=0, column=0, sticky='nsew')
        # Scrollbar
        scrollbar = ttk.Scrollbar(tree_container, orient="vertical", command=self.rules_tree.yview)
        self.rules_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky='ns')
        # -- Pannello Dettagli Regola --
        self.rule_details_frame = ttk.LabelFrame(rules_frame, text="Dettagli Regola")
        self.rule_details_frame.grid(row=0, column=1, sticky='nsew', padx=(0, 5), pady=5)
        self.rule_details_frame.columnconfigure(0, weight=1)
        self.keywords_details_var = tk.StringVar()
        self.roi_details_var = tk.StringVar()
        ttk.Label(self.rule_details_frame, text="Keywords:", font="-weight bold").grid(row=0, column=0, sticky='w', padx=5, pady=(5, 0))
        self.keywords_label = ttk.Label(self.rule_details_frame, textvariable=self.keywords_details_var, justify=tk.LEFT, anchor="nw")
        self.keywords_label.grid(row=1, column=0, sticky='nsew', padx=5, pady=(0, 10))
        ttk.Label(self.rule_details_frame, text="ROI:", font="-weight bold").grid(row=2, column=0, sticky='w', padx=5, pady=(5, 0))
        ttk.Label(self.rule_details_frame, textvariable=self.roi_details_var, justify=tk.LEFT).grid(row=3, column=0, sticky='w', padx=5, pady=(0, 10))
        # Abilita il wrapping dinamico
        self.rule_details_frame.bind("<Configure>", self._on_details_resize)
        # -- Contenitore Pulsanti --
        buttons_container = ttk.Frame(rules_frame)
        buttons_container.grid(row=0, column=2, sticky='ns', padx=(5, 0), pady=5)
        ttk.Button(buttons_container, text="Aggiungi...", command=self.add_rule).pack(fill=tk.X, pady=2)
        ttk.Button(buttons_container, text="Modifica...", command=self.modify_rule).pack(fill=tk.X, pady=2)
        ttk.Button(buttons_container, text="Rimuovi", command=self.remove_rule).pack(fill=tk.X, pady=2)
        ttk.Separator(buttons_container, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        ttk.Button(buttons_container, text="Avvia Utility ROI", command=self.launch_roi_utility).pack(fill=tk.X, pady=2)
        self.rules_tree.bind("<<TreeviewSelect>>", self.update_rule_details_panel)
        save_frame = ttk.Frame(self.config_tab)
        save_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=10, pady=10)
        ttk.Button(save_frame, text="Salva Impostazioni", command=self.save_settings).pack(side=tk.RIGHT)

    def browse_tesseract(self):
        path = filedialog.askopenfilename(title="Seleziona l'eseguibile di Tesseract", filetypes=[("Executable", "*.exe")])
        if path:
            self.tesseract_path_var.set(path)

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
        self.keywords_details_var.set("")
        self.roi_details_var.set("")
        for item in self.rules_tree.get_children():
            self.rules_tree.delete(item)

        # Popola la Treeview con le nuove colonne
        for rule in self.config.get("classification_rules", []):
            color = rule.get("color", "#FFFFFF")
            # Inseriamo solo i dati per le colonne visibili
            self.rules_tree.insert("", tk.END, values=(color, rule["category_name"]))

    def update_rule_details_panel(self, event=None):
        selected_item = self.rules_tree.focus()
        if not selected_item:
            self.keywords_details_var.set("")
            self.roi_details_var.set("")
            return

        item_values = self.rules_tree.item(selected_item, "values")
        category_name = item_values[1] # La categoria è il secondo valore

        rule = next((r for r in self.config.get("classification_rules", []) if r["category_name"] == category_name), None)

        if rule:
            keywords_str = ", ".join(rule.get("keywords", ["N/A"]))
            rois_count = len(rule.get("rois", []))
            roi_summary = f"[{rois_count} Aree ROI definite]"

            self.keywords_details_var.set(keywords_str)
            self.roi_details_var.set(roi_summary)
        else:
            self.keywords_details_var.set("Regola non trovata.")
            self.roi_details_var.set("")

    def load_settings(self):
        self.config = config_manager.load_config()
        self.tesseract_path_var.set(self.config.get("tesseract_path", ""))
        self.populate_rules_tree()

    def save_settings(self):
        self.config["tesseract_path"] = self.tesseract_path_var.get()
        try:
            config_manager.save_config(self.config)
            messagebox.showinfo("Successo", "Impostazioni salvate con successo.")
            self.load_settings()
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile salvare le impostazioni: {e}")

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

    def show_rule_editor(self, rule=None):
        dialog = tk.Toplevel(self.root)
        dialog.title("Modifica Regola" if rule else "Aggiungi Regola")

        category_var = tk.StringVar(value=rule["category_name"] if rule else "")
        keywords_str = ", ".join(rule.get("keywords", [])) if rule else ""
        keywords_var = tk.StringVar(value=keywords_str)
        # Colore di default nero se non specificato
        chosen_color = tk.StringVar(value=rule.get("color", "#000000") if rule else "#000000")

        # Layout
        main_frame = ttk.Frame(dialog, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")

        ttk.Label(main_frame, text="Nome Categoria:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        category_entry = ttk.Entry(main_frame, textvariable=category_var)
        category_entry.grid(row=0, column=1, columnspan=2, padx=5, pady=5, sticky="ew")
        if rule:
            category_entry.config(state='readonly')

        ttk.Label(main_frame, text="Keywords (separate da virgola):").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Entry(main_frame, textvariable=keywords_var, width=40).grid(row=1, column=1, columnspan=2, padx=5, pady=5, sticky="ew")

        ttk.Label(main_frame, text="Colore:").grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        color_swatch = tk.Label(main_frame, text="      ", bg=chosen_color.get())
        color_swatch.grid(row=2, column=1, padx=5, pady=5, sticky="w")

        def _choose_color():
            color_code = colorchooser.askcolor(title="Scegli un colore", initialcolor=chosen_color.get())
            if color_code and color_code[1]:
                chosen_color.set(color_code[1])
                color_swatch.config(bg=color_code[1])

        ttk.Button(main_frame, text="Scegli...", command=_choose_color).grid(row=2, column=2, padx=5, pady=5)

        ttk.Label(main_frame, text="Aree ROI:").grid(row=3, column=0, padx=5, pady=5, sticky=tk.W)
        roi_count = len(rule.get("rois", [])) if rule else 0
        ttk.Label(main_frame, text=f"[{roi_count} aree definite]").grid(row=3, column=1, columnspan=2, padx=5, pady=5, sticky=tk.W)

        def on_save():
            category_name = category_var.get().strip()
            keywords_list = [k.strip() for k in keywords_var.get().split(',') if k.strip()]
            color = chosen_color.get()

            if not category_name or not keywords_list:
                messagebox.showerror("Errore", "Nome categoria e almeno una keyword sono obbligatori.", parent=dialog)
                return

            new_rule_data = {
                "category_name": category_name,
                "keywords": keywords_list,
                "color": color
            }

            if rule: # Modifica
                # Mantieni la chiave 'rotate_roi' se esiste, ma non la esponiamo più
                new_rule_data['rotate_roi'] = rule.get('rotate_roi', 0)
                rule.update(new_rule_data)
            else: # Aggiunta
                if any(r["category_name"] == category_name for r in self.config.get("classification_rules", [])):
                    messagebox.showerror("Errore", "Categoria già esistente.", parent=dialog)
                    return
                new_rule_data["rois"] = [] # Inizializza con una lista vuota di ROI
                self.config.setdefault("classification_rules", []).append(new_rule_data)

            self.populate_rules_tree()
            dialog.destroy()

        ttk.Button(main_frame, text="Salva", command=on_save).grid(row=4, column=0, columnspan=3, pady=10)

    def launch_roi_utility(self):
        script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'roi_utility.py')
        try:
            subprocess.Popen([sys.executable, script_path])
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile avviare l'utility ROI: {e}")

if __name__ == "__main__":
    if os.path.exists(SIGNAL_FILE):
        os.remove(SIGNAL_FILE) # Pulisce il file segnale all'avvio
    root = tk.Tk()
    app = MainApp(root)
    root.mainloop()
