# PROMPT 7: PYSIDE6 MODERNIZATION & MIGRATION PLAN

Questo prompt guida la migrazione di un'applicazione Python (Tkinter, PyQt5 o script CLI) verso un'architettura **PySide6** di classe enterprise, focalizzandosi su UX moderna, animazioni fluide e robustezza strutturale.

## 🎯 OBIETTIVO
Trasformare l'interfaccia utente in un'esperienza professionale "Intelligente", eliminando la latenza percepita e introducendo un design contemporaneo, borderless e animato.

## 🛠️ FASE 1: ANALISI ARCHITETTURALE
1.  **Disaccoppiamento (SoC):** Isolare tutta la logica di business in un `AppController` (QObject). La GUI deve solo emettere segnali e reagire a cambiamenti di stato.
2.  **Service Layer:** Identificare i compiti pesanti (I/O, OCR, Elaborazione) e delegarli a `Worker` thread-safe tramite `QThread` o `ThreadPoolExecutor`.
3.  **Audit Dipendenze:** Verificare la compatibilità di PySide6 con le librerie esistenti e preparare il file `requirements.txt`.

## 🎨 FASE 2: DESIGN & THEMING (Unified Look)
1.  **Single Source of Truth:** Creare un modulo `gui/theme.py` con:
    *   Palette colori (Primary, Accent, Background, Danger, Success).
    *   Preset di Font (Segoe UI / Consolas per i log).
    *   `GLOBAL_QSS`: Un unico foglio di stile CSS per definire il look borderless, arrotondato e piatto.
2.  **UI Factory:** Implementare una fabbrica (`UIFactory`) per generare componenti standardizzati (Stat Cards, Info Rows, Custom Buttons) riducendo il boilerplate.

## ✨ FASE 3: MODERN UX (Splash & Animations)
1.  **Splash Screen Animato:**
    *   Finestra `Frameless` con ombra (`QGraphicsDropShadowEffect`).
    *   Logo pulsante (`QPropertyAnimation` su opacità).
    *   Barra di progresso reale che monitora l'inizializzazione dei moduli e la licenza.
2.  **Transizioni Fluide:**
    *   **Tab Switching:** Animazione "Slide & Fade" per il cambio tra le sezioni del notebook.
    *   **Feedback Visivo:** `AnimatedButton` con transizioni di colore fluide su hover e press.
    *   **Reveal Sequenziale:** Effetto staggered per la comparsa dei componenti nella dashboard.

## 🚀 FASE 4: INTEGRAZIONE E PERFORMANCE
1.  **Sistema di Logging Live:** Implementare un terminale in-app (`QTextEdit`) con messaggi colorati e supporto per `replace_last` (per barre di progresso testuali).
2.  **Gestione Risorse:** Assicurare il rilascio immediato degli handle dei file (PDF/Immagini) per evitare lock del filesystem, specialmente su Windows.
3.  **Signal/Slot Mapping:** Collegare i segnali del Controller ai widget della View usando decoratori `@Slot()` per massimizzare le performance.

## ✅ CRITERI DI VALIDAZIONE
*   **Stabilità:** Nessun crash durante l'inizializzazione (lock del main thread evitati).
*   **Fluidità:** Le animazioni devono girare a 60fps senza scatti.
*   **Pulizia:** Il codice deve superare i controlli Mypy (Type Safety) e Ruff (Style).
*   **Packaging:** PyInstaller deve includere correttamente tutti i moduli GUI (`hidden_imports`).

---
*Usa questo piano per guidare l'esecuzione passo-passo, validando ogni fase prima di procedere alla successiva.*
