import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import config_manager
import pdf_processor
import subprocess
import os
import sys
import threading
import queue

class MainApp:
    """
    Applicazione principale per la divisione di file PDF basata su regole OCR.
    """
    def __init__(self, root):
        self.root = root
        self.root.title("PDF Splitter")
        self.root.geometry("800x600")

        # Setup del notebook per le schede
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(expand=True, fill='both', padx=10, pady=10)

        # Creazione delle schede
        self.processing_tab = ttk.Frame(self.notebook)
        self.config_tab = ttk.Frame(self.notebook)

        self.notebook.add(self.processing_tab, text='Elaborazione')
        self.notebook.add(self.config_tab, text='Configurazione')

        # Inizializzazione delle variabili di stato
        self.config = {}
        self.pdf_path = ""
        self.log_queue = queue.Queue()

        # Setup delle interfacce utente
        self.setup_config_tab()
        self.setup_processing_tab()

        # Caricamento delle impostazioni e avvio del polling della coda di log
        self.load_settings()
        self.root.after(100, self.process_log_queue)

        # Associa l'evento di cambio tab per ricaricare le impostazioni
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

    def on_tab_changed(self, event):
        """
        Ricarica le impostazioni quando la scheda di configurazione viene selezionata,
        garantendo che le modifiche esterne (es. dall'utility ROI) siano visibili.
        """
        selected_tab_index = self.notebook.index(self.notebook.select())
        # L'indice della scheda di configurazione è 1 (0 è Elaborazione)
        if selected_tab_index == 1:
            self.load_settings()

    def setup_processing_tab(self):
        """
        Configura la scheda 'Elaborazione' con i widget per l'input e il logging.
        """
        # Frame per gli input dell'utente
        input_frame = ttk.LabelFrame(self.processing_tab, text="Input")
        input_frame.pack(fill=tk.X, padx=10, pady=10)

        # Campo per l'ODC
        ttk.Label(input_frame, text="ODC:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.odc_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.odc_var, width=40).grid(row=0, column=1, padx=5, pady=5)

        # Pulsante per la selezione del PDF
        ttk.Button(input_frame, text="Seleziona PDF...", command=self.select_pdf).grid(row=1, column=0, padx=5, pady=5)
        self.pdf_path_label = ttk.Label(input_frame, text="Nessun file selezionato")
        self.pdf_path_label.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)

        # Pulsante per avviare l'elaborazione
        start_button = ttk.Button(self.processing_tab, text="Avvia Divisione", command=self.start_processing)
        start_button.pack(pady=10)

        # Area di testo per i log
        log_frame = ttk.LabelFrame(self.processing_tab, text="Log")
        log_frame.pack(expand=True, fill='both', padx=10, pady=10)

        self.log_area = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, state='disabled', height=15)
        self.log_area.pack(expand=True, fill='both', padx=5, pady=5)

    def select_pdf(self):
        """
        Apre un dialogo per la selezione del file PDF da elaborare.
        """
        path = filedialog.askopenfilename(title="Seleziona file PDF", filetypes=[("PDF Files", "*.pdf")])
        if path:
            self.pdf_path = path
            self.pdf_path_label.config(text=os.path.basename(path))

    def add_log_message(self, message):
        """
        Aggiunge un messaggio all'area di log in modo sicuro per i thread.
        """
        self.log_area.config(state='normal')
        self.log_area.insert(tk.END, message + "\n")
        self.log_area.config(state='disabled')
        self.log_area.yview(tk.END)

    def process_log_queue(self):
        """
        Controlla periodicamente la coda di log e aggiorna la GUI.
        """
        try:
            while True:
                message = self.log_queue.get_nowait()
                self.add_log_message(message)
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.process_log_queue)

    def start_processing(self):
        """
        Avvia il processo di elaborazione del PDF in un thread separato.
        """
        odc = self.odc_var.get().strip()
        if not odc:
            messagebox.showerror("Errore", "Per favore, inserisci un ODC.")
            return

        if not self.pdf_path:
            messagebox.showerror("Errore", "Per favore, seleziona un file PDF.")
            return

        # Pulisce l'area di log prima di iniziare
        self.log_area.config(state='normal')
        self.log_area.delete('1.0', tk.END)
        self.log_area.config(state='disabled')

        # Crea e avvia il thread di elaborazione
        thread = threading.Thread(target=self.processing_worker, args=(self.pdf_path, odc, self.config))
        thread.daemon = True
        thread.start()

    def processing_worker(self, pdf_path, odc, config):
        """
        Funzione eseguita dal thread che chiama il processore PDF.
        """
        def progress_callback(message):
            self.log_queue.put(message)

        success, message = pdf_processor.process_pdf(pdf_path, odc, config, progress_callback)

        if not success:
            self.log_queue.put(f"ERRORE FINALE: {message}")

    # --- Metodi per la scheda di configurazione ---

    def setup_config_tab(self):
        """
        Configura la scheda 'Configurazione' con tutti i widget per la gestione delle impostazioni.
        """
        path_frame = ttk.LabelFrame(self.config_tab, text="Impostazioni Generali")
        path_frame.pack(fill=tk.X, padx=10, pady=10)

        path_frame.columnconfigure(1, weight=1)

        ttk.Label(path_frame, text="Path Tesseract:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.tesseract_path_var = tk.StringVar()
        ttk.Entry(path_frame, textvariable=self.tesseract_path_var).grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)
        ttk.Button(path_frame, text="Sfoglia...", command=self.browse_tesseract).grid(row=0, column=2, padx=5, pady=5)
        ttk.Button(path_frame, text="Rileva Automaticamente", command=self.auto_detect_tesseract).grid(row=0, column=3, padx=5, pady=5)

        ttk.Label(path_frame, text="Template Nome File:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.output_template_var = tk.StringVar()
        ttk.Entry(path_frame, textvariable=self.output_template_var).grid(row=1, column=1, columnspan=3, padx=5, pady=5, sticky=tk.EW)

        rules_frame = ttk.LabelFrame(self.config_tab, text="Regole di Classificazione")
        rules_frame.pack(expand=True, fill='both', padx=10, pady=10)
        self.rules_tree = ttk.Treeview(rules_frame, columns=("Category", "Keywords", "ROI"), show='headings')
        self.rules_tree.heading("Category", text="Categoria")
        self.rules_tree.heading("Keywords", text="Keywords (separate da virgola)")
        self.rules_tree.heading("ROI", text="ROI (x0, y0, x1, y1)")
        self.rules_tree.pack(side=tk.LEFT, expand=True, fill='both', padx=5, pady=5)
        rules_buttons_frame = ttk.Frame(rules_frame)
        rules_buttons_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5)
        ttk.Button(rules_buttons_frame, text="Aggiungi...", command=self.add_rule).pack(fill=tk.X, pady=5)
        ttk.Button(rules_buttons_frame, text="Modifica...", command=self.modify_rule).pack(fill=tk.X, pady=5)
        ttk.Button(rules_buttons_frame, text="Rimuovi", command=self.remove_rule).pack(fill=tk.X, pady=5)
        ttk.Separator(rules_buttons_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        ttk.Button(rules_buttons_frame, text="Avvia Utility ROI", command=self.launch_roi_utility).pack(fill=tk.X, pady=5)
        save_frame = ttk.Frame(self.config_tab)
        save_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=10, pady=10)
        ttk.Button(save_frame, text="Salva Impostazioni", command=self.save_settings).pack(side=tk.RIGHT)

    def browse_tesseract(self):
        """
        Apre un dialogo per selezionare il percorso dell'eseguibile di Tesseract.
        """
        path = filedialog.askopenfilename(title="Seleziona l'eseguibile di Tesseract", filetypes=[("Executable", "*.exe")])
        if path:
            self.tesseract_path_var.set(path)

    def auto_detect_tesseract(self):
        """
        Cerca Tesseract in percorsi comuni su Windows.
        """
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
        messagebox.showwarning("Non Trovato", "Impossibile trovare automaticamente Tesseract. Per favore, indicalo manualmente.")

    def populate_rules_tree(self):
        """
        Popola la Treeview con le regole di classificazione dal file di configurazione.
        """
        for item in self.rules_tree.get_children():
            self.rules_tree.delete(item)
        for rule in self.config.get("classification_rules", []):
            keywords_str = ", ".join(rule.get("keywords", []))
            self.rules_tree.insert("", tk.END, values=(rule["category_name"], keywords_str, str(rule["roi"])))

    def load_settings(self):
        """
        Carica le impostazioni dal file config.json e aggiorna la GUI.
        """
        self.config = config_manager.load_config()
        self.tesseract_path_var.set(self.config.get("tesseract_path", ""))
        self.output_template_var.set(self.config.get("output_template", "{ODC}_{category}.pdf"))
        self.populate_rules_tree()

    def save_settings(self):
        """
        Salva le impostazioni correnti nel file config.json.
        """
        self.config["tesseract_path"] = self.tesseract_path_var.get()
        self.config["output_template"] = self.output_template_var.get()
        try:
            config_manager.save_config(self.config)
            messagebox.showinfo("Successo", "Impostazioni salvate con successo.")
            self.load_settings()
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile salvare le impostazioni: {e}")

    def add_rule(self):
        """
        Apre la finestra di dialogo per aggiungere una nuova regola.
        """
        self.show_rule_editor()

    def modify_rule(self):
        """
        Apre la finestra di dialogo per modificare la regola selezionata.
        """
        selected_item = self.rules_tree.focus()
        if not selected_item:
            messagebox.showwarning("Nessuna Selezione", "Selezionare una regola da modificare.")
            return
        item_values = self.rules_tree.item(selected_item, "values")
        rule_to_edit = next((r for r in self.config["classification_rules"] if r["category_name"] == item_values[0]), None)
        if rule_to_edit:
            self.show_rule_editor(rule_to_edit)

    def remove_rule(self):
        """
        Rimuove la regola di classificazione selezionata.
        """
        selected_item = self.rules_tree.focus()
        if not selected_item:
            messagebox.showwarning("Nessuna Selezione", "Selezionare una regola da rimuovere.")
            return
        category_name = self.rules_tree.item(selected_item, "values")[0]
        if messagebox.askyesno("Conferma", f"Sei sicuro di voler rimuovere la regola '{category_name}'?"):
            self.config["classification_rules"] = [r for r in self.config["classification_rules"] if r["category_name"] != category_name]
            self.populate_rules_tree()

    def show_rule_editor(self, rule=None):
        """
        Mostra una finestra di dialogo per aggiungere o modificare una regola.
        """
        dialog = tk.Toplevel(self.root)
        dialog.title("Modifica Regola" if rule else "Aggiungi Regola")

        category_var = tk.StringVar(value=rule["category_name"] if rule else "")
        keywords_str = ", ".join(rule.get("keywords", [])) if rule else ""
        keywords_var = tk.StringVar(value=keywords_str)

        ttk.Label(dialog, text="Nome Categoria:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        category_entry = ttk.Entry(dialog, textvariable=category_var)
        category_entry.grid(row=0, column=1, padx=5, pady=5)
        if rule:
            category_entry.config(state='readonly')

        ttk.Label(dialog, text="Keywords (separate da virgola):").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Entry(dialog, textvariable=keywords_var, width=40).grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(dialog, text="ROI:").grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Label(dialog, text=str(rule["roi"]) if rule else "[Verrà impostato con l'utility ROI]").grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)

        def on_save():
            category_name = category_var.get().strip()
            keywords_list = [k.strip() for k in keywords_var.get().split(',') if k.strip()]

            if not category_name or not keywords_list:
                messagebox.showerror("Errore", "Nome categoria e almeno una keyword sono obbligatori.", parent=dialog)
                return

            if rule: # Modifica
                rule["keywords"] = keywords_list
            else: # Aggiunta
                if any(r["category_name"] == category_name for r in self.config.get("classification_rules", [])):
                    messagebox.showerror("Errore", "Categoria già esistente.", parent=dialog)
                    return
                self.config.setdefault("classification_rules", []).append({
                    "category_name": category_name, "keywords": keywords_list, "roi": [0,0,0,0]
                })

            self.populate_rules_tree()
            dialog.destroy()

        ttk.Button(dialog, text="Salva", command=on_save).grid(row=3, columnspan=2, pady=10)

    def launch_roi_utility(self):
        """
        Lancia l'utility per la selezione della ROI come processo separato.
        """
        script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'roi_utility.py')
        try:
            subprocess.Popen([sys.executable, script_path])
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile avviare l'utility ROI: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = MainApp(root)
    root.mainloop()
