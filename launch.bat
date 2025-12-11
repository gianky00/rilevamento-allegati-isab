@echo off
TITLE PDF Splitter Launcher

REM Controlla se Python è nel PATH
python --version >nul 2>nul
if %errorlevel% neq 0 (
    echo Python non trovato nel PATH.
    echo Assicurati che Python sia installato e aggiunto alle variabili d'ambiente.
    pause
    exit /b
)

REM Controlla se pip è installato
pip --version >nul 2>nul
if %errorlevel% neq 0 (
    echo pip non è installato o non è nel PATH.
    pause
    exit /b
)

echo.
echo ===================================
echo  Installazione dipendenze in corso...
echo ===================================
echo.
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo ERRORE durante l'installazione delle dipendenze.
    pause
    exit /b
)

echo.
echo ===================================
echo  Avvio dell'applicazione...
echo ===================================
echo.

REM Avvia main.py usando python standard (non pythonw) per vedere i log in questa finestra
python main.py

REM Se python termina con errore, metti in pausa
if %errorlevel% neq 0 (
    echo.
    echo ===================================
    echo  L'applicazione si è chiusa con un ERRORE.
    echo  Leggi i messaggi sopra per capire il problema.
    echo ===================================
    pause
) else (
    echo.
    echo Applicazione chiusa correttamente.
    REM Opzionale: pause se vuoi vedere anche la chiusura corretta, altrimenti rimuovi
    REM pause
)
exit /b
