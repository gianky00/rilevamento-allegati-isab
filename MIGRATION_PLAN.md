# 🔄 Piano di Migrazione da Tkinter a PySide6 — Intelleo PDF Splitter

**Versione piano:** 1.0  
**Data:** 05/03/2026  
**Versione app:** 2.0.30  
**Branch dedicato:** `feature/pyside6-migration`

---

## 📋 Sommario Esecutivo

Migrazione completa della GUI da **Tkinter + tkinterdnd2** a **PySide6** (Qt6) per il progetto Intelleo PDF Splitter. L'obiettivo è ottenere un'interfaccia più moderna, performante e manutenibile, eliminando tutte le dipendenze obsolete legate a Tkinter.

---

## 🏗️ Architettura Attuale — Audit Completo

### File con dipendenze dirette Tkinter (DA MIGRARE)

| File                      | Righe | Classi GUI                            | Widget usati                                                                                                                                                                                      | Complessità  |
| ------------------------- | ----- | ------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------ |
| `main.py`                 | 1695  | `MainApp`, `UnknownFilesReviewDialog` | `tk.Tk`, `ttk.Notebook`, `ttk.Treeview`, `tk.Canvas`, `scrolledtext.ScrolledText`, `messagebox`, `filedialog`, `colorchooser`, `simpledialog`, `tk.Listbox`, `ttk.Progressbar`, `ttk.PanedWindow` | 🔴 **ALTA**  |
| `roi_utility.py`          | 619   | `ROIDrawingApp`                       | `tk.Tk`, `tk.Canvas`, `ttk.Frame/Button/Label/Combobox/Scrollbar/Style/Checkbutton`, `filedialog`, `messagebox`, `ImageTk`                                                                        | 🟡 **MEDIA** |
| `notification_manager.py` | 100   | `NotificationManager`                 | `tk.Toplevel`, `tk.Label`, `ttk.Frame`                                                                                                                                                            | 🟢 **BASSA** |
| `app_updater.py`          | 208   | - (solo funzioni)                     | `messagebox`, `tk.Toplevel`, `ttk.Progressbar`, `ttk.Label`, `ttk.Frame`                                                                                                                          | 🟢 **BASSA** |

### File SENZA dipendenze Tkinter (NON toccare)

| File                   | Righe | Note                                |
| ---------------------- | ----- | ----------------------------------- |
| `pdf_processor.py`     | 404   | Pura logica OCR/PDF — **INVARIATO** |
| `config_manager.py`    | 122   | JSON config — **INVARIATO**         |
| `license_validator.py` | 247   | Crittografia/HW ID — **INVARIATO**  |
| `license_updater.py`   | 212   | GitHub API — **INVARIATO**          |
| `app_logger.py`        | 301   | Logging su file — **INVARIATO**     |
| `generate_icon.py`     | 127   | Pillow only — **INVARIATO**         |
| `version.py`           | 5     | Costante versione — **INVARIATO**   |

### Dipendenze da Rimuovere (Obsolete)

| Dipendenza                                       | Motivo Rimozione           | Sostituto PySide6                          |
| ------------------------------------------------ | -------------------------- | ------------------------------------------ |
| `tkinterdnd2`                                    | Drag & Drop nativo Tkinter | `QDragEnterEvent` / `QDropEvent` nativo Qt |
| `PIL.ImageTk`                                    | Bridge Pillow→Tkinter      | `QPixmap.fromImage()` / `QImage` nativo Qt |
| Hook PyInstaller `hook-tkinterdnd2.py`           | Non più necessario         | Nessuno (Qt bundled natively)              |
| Bypass UAC `ChangeWindowMessageFilterEx` per DnD | Workaround tkinterdnd2     | Non necessario con Qt nativo               |

### Test Esistenti (DA ADATTARE)

| File Test                    | Righe | Cosa testa                                   | Impatto migrazione                                               |
| ---------------------------- | ----- | -------------------------------------------- | ---------------------------------------------------------------- |
| `test_main.py`               | 167   | `MainApp`, log queue, processing worker, DnD | 🔴 **ALTO** — Mock di `tkinter.*` da sostituire con mock PySide6 |
| `test_roi_utility.py`        | 103   | `ROIDrawingApp`, Canvas, ROI draw/save       | 🔴 **ALTO** — Mock di `tkinter.*` da sostituire                  |
| `test_pdf_processor.py`      | ~250  | Logica OCR pura                              | 🟢 **ZERO** — Non usa GUI                                        |
| `test_config_manager.py`     | ~100  | Load/save config JSON                        | 🟢 **ZERO**                                                      |
| `test_license_*.py`          | ~250  | Validazione/update licenza                   | 🟢 **ZERO**                                                      |
| `test_app_logger.py`         | ~250  | Logging                                      | 🟢 **ZERO**                                                      |
| `test_session_management.py` | ~100  | Sessione JSON                                | 🟢 **ZERO**                                                      |

---

## 🗺️ Mapping API: Tkinter → PySide6

### Widget Principali

| Tkinter                     | PySide6                                            | Note                           |
| --------------------------- | -------------------------------------------------- | ------------------------------ |
| `tk.Tk()`                   | `QMainWindow` + `QApplication`                     | Entry point diverso            |
| `tk.Toplevel()`             | `QDialog`                                          | Per dialoghi modali/non-modali |
| `tk.Frame`                  | `QFrame` / `QWidget`                               | Container base                 |
| `ttk.Frame`                 | `QFrame` con stylesheet                            | Tema via QSS                   |
| `ttk.Notebook`              | `QTabWidget`                                       | Tab-based layout               |
| `ttk.Label`                 | `QLabel`                                           | Testo e icone                  |
| `ttk.Button`                | `QPushButton`                                      | Con icone e stili              |
| `ttk.Entry`                 | `QLineEdit`                                        | Input singola riga             |
| `tk.Text`                   | `QTextEdit`                                        | Testo multi-riga               |
| `scrolledtext.ScrolledText` | `QTextEdit`                                        | Scroll nativo in Qt            |
| `ttk.Treeview`              | `QTreeWidget` / `QTableWidget`                     | Vista ad albero/tabella        |
| `ttk.Progressbar`           | `QProgressBar`                                     | Barra di progresso             |
| `ttk.Combobox`              | `QComboBox`                                        | Selezione dropdown             |
| `ttk.Scrollbar`             | Integrato in `QScrollArea` / `QAbstractScrollArea` | Scroll nativo                  |
| `ttk.Separator`             | `QFrame` con `setFrameShape(HLine)`                | Linea separatrice              |
| `ttk.PanedWindow`           | `QSplitter`                                        | Layout resizabile              |
| `ttk.Checkbutton`           | `QCheckBox`                                        | Checkbox                       |
| `tk.Canvas`                 | `QGraphicsView` + `QGraphicsScene`                 | Per ROI drawing                |
| `tk.Listbox`                | `QListWidget`                                      | Lista con selezione            |
| `ttk.Style`                 | `QSS` (Qt Style Sheets)                            | Tema globale via CSS-like      |

### Dialog e Utility

| Tkinter                         | PySide6                              | Note |
| ------------------------------- | ------------------------------------ | ---- |
| `messagebox.showerror()`        | `QMessageBox.critical()`             |      |
| `messagebox.showwarning()`      | `QMessageBox.warning()`              |      |
| `messagebox.showinfo()`         | `QMessageBox.information()`          |      |
| `messagebox.askyesno()`         | `QMessageBox.question()`             |      |
| `filedialog.askopenfilename()`  | `QFileDialog.getOpenFileName()`      |      |
| `filedialog.askopenfilenames()` | `QFileDialog.getOpenFileNames()`     |      |
| `filedialog.askdirectory()`     | `QFileDialog.getExistingDirectory()` |      |
| `colorchooser.askcolor()`       | `QColorDialog.getColor()`            |      |
| `simpledialog.askstring()`      | `QInputDialog.getText()`             |      |

### Variabili e Binding

| Tkinter                   | PySide6                                       | Note                   |
| ------------------------- | --------------------------------------------- | ---------------------- |
| `tk.StringVar`            | Binding diretto / proprietà widget            | Es. `lineEdit.text()`  |
| `tk.IntVar` / `DoubleVar` | Proprietà widget + Signals                    | `signal.connect(slot)` |
| `tk.BooleanVar`           | Proprietà widget                              | `checkbox.isChecked()` |
| `.bind("<evento>")`       | `signal.connect(slot)`                        | Sistema Signal/Slot Qt |
| `.after(ms, callback)`    | `QTimer.singleShot(ms, callback)`             | Timer asincroni        |
| `.pack()` / `.grid()`     | `QVBoxLayout` / `QHBoxLayout` / `QGridLayout` | Layout managers        |
| `.configure(bg=...)`      | `setStyleSheet("background-color: ...")`      |                        |
| `.winfo_*`                | `geometry()` / `size()` / `screen()`          | Proprietà geometria    |

### Drag & Drop

| Tkinter (tkinterdnd2)             | PySide6                                          |
| --------------------------------- | ------------------------------------------------ |
| `TkinterDnD.Tk()`                 | `QMainWindow` con `setAcceptDrops(True)`         |
| `drop_target_register(DND_FILES)` | Override `dragEnterEvent()` + `dropEvent()`      |
| `dnd_bind('<<Drop>>', handler)`   | `dropEvent(event)` con `event.mimeData().urls()` |

### Immagini

| Tkinter                       | PySide6                                                  |
| ----------------------------- | -------------------------------------------------------- |
| `PIL.ImageTk.PhotoImage(img)` | `QPixmap.fromImage(ImageQt(img))` oppure `QPixmap(path)` |
| `canvas.create_image(...)`    | `QGraphicsScene.addPixmap(...)`                          |
| `root.iconbitmap(path)`       | `setWindowIcon(QIcon(path))`                             |

---

## 📐 Strategia di Migrazione a Fasi

### Principi Anti-Regressione

> [!IMPORTANT]
>
> 1. **Mai rompere il build** — Ogni fase produce codice funzionante e testabile
> 2. **Test PRIMA, codice DOPO** — Adattare i test prima di migrare il codice
> 3. **File per file** — Mai migrare più di un file alla volta
> 4. **Commit granulari** — Un commit per ogni unità logica completata
> 5. **Feature-parity** — L'utente NON deve notare differenze funzionali

---

### FASE 0: Setup e Branch (Pre-migrazione)

**Obiettivo:** Preparare l'ambiente e creare il branch dedicato.

- [ ] Creare branch `feature/pyside6-migration` da `main`
- [ ] Aggiungere `PySide6` a `requirements.txt`
- [ ] Verificare installazione PySide6 nel venv
- [ ] Creare file `src/compat.py` — Layer di compatibilità per transizione graduale
- [ ] Commit: `chore: setup branch migrazione PySide6`

**`compat.py` — Scopo:**

```python
"""
Layer di compatibilità Tkinter → PySide6.
Importare da qui i costrutti comuni durante la transizione.
Questo file verrà eliminato a migrazione completata.
"""
```

---

### FASE 1: Moduli a Bassa Complessità (notification_manager.py, app_updater.py)

**Obiettivo:** Migrare i 2 file più semplici per consolidare i pattern di conversione.

#### 1A — `notification_manager.py` (100 righe, 🟢)

Conversioni necessarie:

- `tk.Toplevel` → `QDialog` (non-modale, con `setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)`)
- `tk.Label` → `QLabel`
- `ttk.Frame` → `QFrame`
- `.pack()` → `QVBoxLayout`
- `.attributes("-alpha", ...)` → `setWindowOpacity()` per fade-in
- `.attributes("-topmost", True)` → `Qt.WindowStaysOnTopHint`
- `.overrideredirect(True)` → `Qt.FramelessWindowHint`
- `self.root.after(ms, fn)` → `QTimer.singleShot(ms, fn)`
- `.winfo_screenwidth()` → `QApplication.primaryScreen().geometry().width()`
- `.winfo_exists()` → `isVisible()` / null-check
- `.place(relx=..., rely=...)` → Layout positioning o `move()`

**Test:**

- Nessun test specifico esistente per `notification_manager` → creare test unitari base per PySide6
- Commit: `feat(migration): migra notification_manager a PySide6`

#### 1B — `app_updater.py` (208 righe, 🟢)

Conversioni necessarie:

- `messagebox.showerror/showinfo/askyesno` → `QMessageBox.critical/information/question`
- `tk.Toplevel` → `QDialog`
- `ttk.Progressbar` → `QProgressBar`
- `ttk.Label/Frame` → `QLabel/QFrame`
- `.pack()` → `QVBoxLayout`
- `.protocol("WM_DELETE_WINDOW", ...)` → Non necessario, gestito da `closeEvent()`
- `webbrowser.open(url)` → `QDesktopServices.openUrl(QUrl(url))`

**Test:**

- Verificare che `check_for_updates()` e `perform_auto_update()` funzionino correttamente con i nuovi dialog
- Commit: `feat(migration): migra app_updater a PySide6`

---

### FASE 2: ROI Utility (roi_utility.py)

**Obiettivo:** Migrare la seconda GUI più complessa — l'utility di disegno ROI.

#### Conversioni Critiche:

| Area             | Da                                            | A                                                          |
| ---------------- | --------------------------------------------- | ---------------------------------------------------------- |
| **Canvas PDF**   | `tk.Canvas` + `ImageTk.PhotoImage`            | `QGraphicsView` + `QGraphicsScene` + `QGraphicsPixmapItem` |
| **Disegno ROI**  | `canvas.create_rectangle()`                   | `scene.addRect()` con `QGraphicsRectItem`                  |
| **Mouse Events** | `.bind("<Button-1>")`, `.bind("<B1-Motion>")` | Override `mousePressEvent()`, `mouseMoveEvent()`           |
| **Zoom**         | Manuale con matrice                           | `QGraphicsView.setTransform()` / `scale()`                 |
| **Panning**      | `canvas.scan_mark/scan_dragto`                | `setDragMode(QGraphicsView.ScrollHandDrag)`                |
| **Lista regole** | `ttk.Combobox`                                | `QComboBox`                                                |
| **Modal dialog** | `tk.Toplevel` con `.grab_set()`               | `QDialog.exec()`                                           |
| **File dialog**  | `filedialog.askopenfilename`                  | `QFileDialog.getOpenFileName`                              |

#### Canvas → QGraphicsView — Dettaglio:

```python
# PRIMA (Tkinter)
self.canvas = tk.Canvas(parent, bg='white')
pix = page.get_pixmap(matrix=mat)
img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
self.tk_image = ImageTk.PhotoImage(img)
self.canvas.create_image(0, 0, anchor='nw', image=self.tk_image)

# DOPO (PySide6)
self.scene = QGraphicsScene()
self.view = QGraphicsView(self.scene)
pix = page.get_pixmap(matrix=mat)
qimage = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888)
pixmap_item = self.scene.addPixmap(QPixmap.fromImage(qimage))
```

**Test:** Adattare `test_roi_utility.py` — sostituire mock `tkinter.*` con mock PySide6.

- Commit: `feat(migration): migra roi_utility a PySide6`

---

### FASE 3: Main Application (main.py) — Il Monolite

**Obiettivo:** Migrare il cuore dell'applicazione. Questa è la fase più critica.

> [!CAUTION]
> `main.py` ha 1695 righe e mischia GUI e logica business. **Prima di migrare**, è opportuno refactorizzare estraendo la logica in moduli separati per ridurre la complessità e facilitare il testing isolato.

#### 3A — Refactoring Pre-Migrazione (Opzionale ma raccomandato)

Estrarre da `main.py`:

- **`session_manager.py`** — Logica salvataggio/ripristino sessione (pure Python, senza GUI)
- **`processing_engine.py`** — `_processing_worker()` e logica di orchestrazione PDF

Questo riduce il rischio e permette di testare la logica business INDIPENDENTEMENTE dalla GUI.

#### 3B — Migrazione `UnknownFilesReviewDialog`

| Area             | Da                             | A                                                 |
| ---------------- | ------------------------------ | ------------------------------------------------- |
| **Base class**   | `tk.Toplevel`                  | `QDialog`                                         |
| **Preview PDF**  | `tk.Canvas` + `ImageTk`        | `QGraphicsView` + `QGraphicsScene`                |
| **Lista pagine** | `tk.Listbox`                   | `QListWidget` con `QListWidget.ExtendedSelection` |
| **Selezione**    | `curselection()`               | `selectedItems()` / `selectedIndexes()`           |
| **Binding**      | `<<ListboxSelect>>`            | `itemSelectionChanged` signal                     |
| **Scroll**       | `ttk.Scrollbar`                | Integrato in `QListWidget`                        |
| **Zoom rotella** | `<MouseWheel>` event con delta | Override `wheelEvent()`                           |
| **Wait window**  | `self.wait_window(dialog)`     | `dialog.exec()`                                   |
| **Grab**         | `dialog.grab_set()`            | `dialog.setModal(True)`                           |

#### 3C — Migrazione `MainApp`

| Area             | Da                                               | A                                                              |
| ---------------- | ------------------------------------------------ | -------------------------------------------------------------- |
| **Base**         | Classe non-widget (composizione con `self.root`) | `QMainWindow`                                                  |
| **Tab**          | `ttk.Notebook`                                   | `QTabWidget`                                                   |
| **Dashboard**    | `tk.Frame` con `tk.Label` per card               | `QWidget` con `QGridLayout`                                    |
| **Stat cards**   | `tk.Frame` + `tk.Label` manuali                  | `QFrame` con QSS styling                                       |
| **Log area**     | `scrolledtext.ScrolledText`                      | `QTextEdit` (readonly=True)                                    |
| **Progress bar** | `ttk.Progressbar` + `tk.DoubleVar`               | `QProgressBar.setValue()`                                      |
| **Treeview**     | `ttk.Treeview` con heading/columns               | `QTreeWidget` con `QTreeWidgetItem`                            |
| **Entry fields** | `ttk.Entry` + `tk.StringVar`                     | `QLineEdit`                                                    |
| **Orologio**     | `root.after(1000, _update_clock)`                | `QTimer(interval=1000)`                                        |
| **Log queue**    | `root.after(100, _process_log_queue)`            | `QTimer` + `QApplication.processEvents()`                      |
| **Stili**        | `ttk.Style()` con `.configure()`                 | QSS (Qt Style Sheets) globali                                  |
| **DnD**          | `tkinterdnd2` + bypass UAC                       | `setAcceptDrops(True)` + override `dragEnterEvent`/`dropEvent` |

#### 3D — Entry Point

```python
# PRIMA (Tkinter)
root = TkinterDnD.Tk()
app = MainApp(root)
root.mainloop()

# DOPO (PySide6)
app = QApplication(sys.argv)
window = MainApp()
window.showMaximized()
sys.exit(app.exec())
```

**Test:** Adattare `test_main.py` — sostituire tutti i mock `tkinter.*` con mock `PySide6.*`.

- Commit: `feat(migration): migra main.py a PySide6`

---

### FASE 4: Pulizia e Rimozione Obsolescenza

**Obiettivo:** Eliminare tutte le tracce di Tkinter e componenti obsoleti.

#### Da Rimuovere

| Elemento                               | Percorso                    | Motivo                                |
| -------------------------------------- | --------------------------- | ------------------------------------- |
| `tkinterdnd2` da requirements.txt      | `src/requirements.txt`      | Sostituito da Qt nativo               |
| `hook-tkinterdnd2.py`                  | `admin/Crea Setup/hooks/`   | Hook PyInstaller non necessario       |
| import `PIL.ImageTk`                   | `main.py`, `roi_utility.py` | Sostituito da `QImage`/`QPixmap`      |
| Bypass UAC DnD                         | `main.py` L523-550          | Workaround non necessario con Qt      |
| `pyarmor` da requirements.txt          | `src/requirements.txt`      | Se non usato attivamente (verificare) |
| `pyinstaller` da requirements.txt      | `src/requirements.txt`      | Tool dev, non produzione (opzionale)  |
| File `compat.py`                       | `src/compat.py`             | Layer temporaneo di transizione       |
| Costanti `COLORS` e `FONTS` dict-based | `main.py`, `roi_utility.py` | Sostituiti da QSS centralizzato       |
| File `.Jules/`                         | Root progetto               | Directory obsoleta (vecchio tool AI?) |

#### Da Aggiornare

| Elemento             | Azione                                                                      |
| -------------------- | --------------------------------------------------------------------------- |
| `requirements.txt`   | Aggiungere `PySide6`, rimuovere `tkinterdnd2`                               |
| `README.md`          | Aggiornare dipendenze (rimuovere `tkinterdnd2`, aggiungere `PySide6`)       |
| `README.md`          | Aggiornare scorciatoie tastiera se cambiate                                 |
| `launch.bat`         | Verificare compatibilità                                                    |
| Pipeline PyInstaller | Rimuovere `--collect-all=tkinterdnd2`, aggiungere `--hidden-import=PySide6` |
| `config.json`        | Invariato (pure JSON)                                                       |
| `version.py`         | Bump a `2.1.0` post-migrazione                                              |

---

### FASE 5: QSS — Tema Visuale Centralizzato

**Obiettivo:** Creare un file `style.qss` che replichi esattamente il tema attuale, poi migliorarlo.

```css
/* style.qss — Replica del tema COLORS/FONTS attuale */
QMainWindow {
  background-color: #ffffff;
}

QTabWidget::pane {
  background-color: #ffffff;
  border: none;
}

QTabBar::tab {
  font: bold 10pt "Segoe UI";
  padding: 10px 20px;
  background-color: #f8f9fa;
  color: #111827;
}

QTabBar::tab:selected {
  background-color: #2563eb;
  color: #ffffff;
}

QPushButton {
  font: 10pt "Segoe UI";
  padding: 8px 15px;
  border: 1px solid #e5e7eb;
  border-radius: 4px;
}

QPushButton:hover {
  background-color: #1d4ed8;
  color: #ffffff;
}

/* ... (completare con tutti gli stili) */
```

---

## 📊 Avanzamento Lavori

| Fase | Descrizione                 | Status     | Commit |
| ---- | --------------------------- | ---------- | ------ |
| 0    | Setup branch + requirements | ⬜ Da fare | —      |
| 1A   | `notification_manager.py`   | ⬜ Da fare | —      |
| 1B   | `app_updater.py`            | ⬜ Da fare | —      |
| 2    | `roi_utility.py`            | ⬜ Da fare | —      |
| 3A   | Refactoring pre-migrazione  | ⬜ Da fare | —      |
| 3B   | `UnknownFilesReviewDialog`  | ⬜ Da fare | —      |
| 3C   | `MainApp`                   | ⬜ Da fare | —      |
| 3D   | Entry point + `__main__`    | ⬜ Da fare | —      |
| 4    | Pulizia obsolescenza        | ⬜ Da fare | —      |
| 5    | QSS tema visuale            | ⬜ Da fare | —      |

---

## ✅ Piano di Verifica

### Test Automatizzati

Dopo **ogni fase**, eseguire:

```bash
cd c:\Users\Coemi\Desktop\SCRIPT\rilevamento-allegati-isab\rilevamento-allegati-isab
.venv\Scripts\python.exe -m pytest tests/ -v --tb=short
```

**Test specifici per GUI PySide6:**

- I test esistenti (`test_main.py`, `test_roi_utility.py`) usano mock pesanti di tkinter. Andranno riscritti per mockare `PySide6.QtWidgets` e `PySide6.QtCore`.
- Pattern di mock PySide6:

```python
# Mock PySide6 nei test (pattern)
with patch("PySide6.QtWidgets.QMessageBox.critical") as mock_error:
    ...
with patch("PySide6.QtWidgets.QFileDialog.getOpenFileName", return_value=("test.pdf", "...")):
    ...
```

### Verifica Manuale (Per l'utente)

Dopo il completamento di ogni fase:

1. **Avviare l'app** con `launch.bat` o `.venv\Scripts\python.exe src\main.py`
2. **Dashboard:** Verificare che tutte le card statistiche, l'orologio, e il pannello licenza funzionino
3. **Elaborazione:** Selezionare un PDF, inserire un codice ODC, e processarlo
4. **Drag & Drop:** Trascinare un file PDF sulla zona di drop
5. **Configurazione:** Verificare che la treeview delle regole, il path Tesseract, e l'editor regole funzionino
6. **ROI Utility:** Aprire un PDF, disegnare una ROI, salvare e verificare
7. **Revisione File Sconosciuti:** Verificare il dialog di revisione manuale con preview PDF
8. **Notifiche Toast:** Verificare che appaiano e spariscano correttamente

---

## ⚠️ Rischi e Mitigazioni

| Rischio                                 | Impatto                                       | Mitigazione                                         |
| --------------------------------------- | --------------------------------------------- | --------------------------------------------------- |
| PySide6 ha rendering diverso da Tkinter | Le UI potrebbero apparire leggermente diverse | QSS per replicare esattamente i colori/font attuali |
| Canvas ROI complesso da migrare         | Possibili regressioni nel disegno ROI         | Test manuali approfonditi + screenshot confronto    |
| PyInstaller con PySide6                 | Bundle più grande (~50MB+)                    | Accettabile, guadagno in qualità UI                 |
| Thread safety Qt vs Tkinter             | Qt è più restrittivo con i thread             | Usare `QThread` + Signals per worker threads        |
| `root.after()` usato ovunque            | Pattern diverso in Qt                         | `QTimer.singleShot()` / `QTimer` persistente        |

---

## User Review Required

> [!IMPORTANT]
> **Decisione richiesta:**
>
> 1. Confermi la creazione del branch `feature/pyside6-migration`?
> 2. Vuoi procedere con il refactoring pre-migrazione (Fase 3A) per estrarre la logica business da `main.py`, o preferisci migrare il monolite direttamente?
> 3. `pyarmor` è ancora usato attivamente? Se no, lo rimuoviamo da `requirements.txt`.
> 4. La directory `.Jules/` è obsoleta e può essere eliminata?
