import tkinter as tk
from tkinter import ttk, filedialog, simpledialog, messagebox
import fitz  # PyMuPDF
from PIL import Image, ImageTk
import os
import config_manager

class ROIDrawingApp:
    """
    Applicazione di utilità per disegnare una Regione di Interesse (ROI) su una pagina PDF
    e salvare le coordinate nel file di configurazione.
    """
    def __init__(self, root):
        self.root = root
        self.root.title("Utility di Rilevamento ROI")
        self.root.geometry("1000x800")

        # Frame per i controlli (es. pulsante "Apri PDF")
        control_frame = ttk.Frame(self.root)
        control_frame.pack(pady=5, padx=10, fill=tk.X)

        ttk.Button(control_frame, text="Apri PDF", command=self.open_pdf).pack(side=tk.LEFT, padx=5)

        # Frame per il canvas e le barre di scorrimento
        canvas_frame = ttk.Frame(self.root)
        canvas_frame.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)

        self.canvas = tk.Canvas(canvas_frame, bg="gray")

        # Barre di scorrimento
        self.h_scroll = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.v_scroll = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.canvas.config(xscrollcommand=self.h_scroll.set, yscrollcommand=self.v_scroll.set)

        self.h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        self.v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)

        # Inizializzazione delle variabili di stato
        self.pdf_doc = None
        self.tk_image = None
        self.rect = None
        self.start_x = None
        self.start_y = None
        self.end_x = None
        self.end_y = None

        # Binding degli eventi del mouse al canvas
        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)

    def open_pdf(self):
        """
        Apre un dialogo per selezionare un file PDF e chiede all'utente di scegliere una pagina.
        """
        filepath = filedialog.askopenfilename(
            title="Seleziona un file PDF",
            filetypes=[("PDF Files", "*.pdf")]
        )
        if not filepath:
            return

        try:
            self.pdf_doc = fitz.open(filepath)
            page_num = simpledialog.askinteger("Seleziona Pagina", "Inserisci il numero di pagina:", parent=self.root, minvalue=1, maxvalue=self.pdf_doc.page_count)
            if page_num is None:
                self.pdf_doc.close()
                return

            self.render_page(page_num - 1)
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile aprire o renderizzare il PDF: {e}")

    def render_page(self, page_index):
        """
        Renderizza una pagina del PDF come immagine e la visualizza sul canvas.
        """
        if not self.pdf_doc:
            return

        page = self.pdf_doc[page_index]
        pix = page.get_pixmap(dpi=300)

        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        self.tk_image = ImageTk.PhotoImage(img)

        # Pulisce il canvas e imposta la nuova immagine
        self.canvas.delete("all")
        self.canvas.config(scrollregion=(0, 0, pix.width, pix.height))
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_image)

        # Resetta le coordinate della ROI
        self.rect = None
        self.start_x = None
        self.start_y = None
        self.end_x = None
        self.end_y = None

    def on_button_press(self, event):
        """
        Gestisce l'evento di pressione del pulsante del mouse per iniziare a disegnare la ROI.
        """
        self.start_x = self.canvas.canvasx(event.x)
        self.start_y = self.canvas.canvasy(event.y)

        if self.rect:
            self.canvas.delete(self.rect)
        self.rect = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline='red', width=2, dash=(4, 2))

    def on_mouse_drag(self, event):
        """
        Gestisce l'evento di trascinamento del mouse per aggiornare il rettangolo della ROI.
        """
        cur_x = self.canvas.canvasx(event.x)
        cur_y = self.canvas.canvasy(event.y)
        self.canvas.coords(self.rect, self.start_x, self.start_y, cur_x, cur_y)

    def on_button_release(self, event):
        """
        Gestisce l'evento di rilascio del pulsante del mouse, finalizza le coordinate
        e avvia il processo di salvataggio.
        """
        self.end_x = self.canvas.canvasx(event.x)
        self.end_y = self.canvas.canvasy(event.y)

        # Normalizza le coordinate
        x0 = min(self.start_x, self.end_x)
        y0 = min(self.start_y, self.end_y)
        x1 = max(self.start_x, self.end_x)
        y1 = max(self.start_y, self.end_y)

        # Converte le coordinate da pixel a punti PDF (1 punto = 1/72 pollici)
        factor = 72 / 300
        roi_pdf_coords = [int(x0 * factor), int(y0 * factor), int(x1 * factor), int(y1 * factor)]

        self.prompt_and_save_roi(roi_pdf_coords)

    def prompt_and_save_roi(self, roi_coords):
        """
        Mostra un dialogo per associare la ROI a una categoria e salvarla nel file di configurazione.
        """
        config = config_manager.load_config()
        categories = [rule["category_name"] for rule in config.get("classification_rules", [])]

        if not categories:
            messagebox.showwarning("Nessuna Categoria", "Non ci sono categorie di classificazione definite nella configurazione. Aggiungine una prima.")
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("Salva ROI")
        dialog.geometry("300x150")

        ttk.Label(dialog, text=f"Coordinate: {roi_coords}").pack(pady=5)
        ttk.Label(dialog, text="Associa alla categoria:").pack(pady=5)

        category_var = tk.StringVar()
        category_combo = ttk.Combobox(dialog, textvariable=category_var, values=categories, state='readonly')
        category_combo.pack(pady=5)
        if categories:
            category_combo.set(categories[0])

        def save():
            selected_category = category_var.get()
            if not selected_category:
                messagebox.showwarning("Selezione Richiesta", "Seleziona una categoria.", parent=dialog)
                return

            # Aggiorna la configurazione con le nuove coordinate ROI
            for rule in config["classification_rules"]:
                if rule["category_name"] == selected_category:
                    rule["roi"] = roi_coords
                    break

            try:
                config_manager.save_config(config)
                messagebox.showinfo("Successo", f"ROI per '{selected_category}' salvata con successo.", parent=self.root)
                dialog.destroy()
            except Exception as e:
                messagebox.showerror("Errore", f"Impossibile salvare la configurazione: {e}", parent=dialog)

        ttk.Button(dialog, text="Salva ROI nel file di Configurazione", command=save).pack(pady=10)

if __name__ == "__main__":
    root = tk.Tk()
    app = ROIDrawingApp(root)
    root.mainloop()
