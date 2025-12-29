@echo off
TITLE Intelleo PDF Splitter v2.0 - DEBUG MODE
COLOR 0B
cls

echo.
echo  +====================================================================+
echo  ^| INTELLEO PDF SPLITTER - LAUNCHER                                   ^|
echo  +====================================================================+
echo.

set VENV_DIR=.venv

:: 1. Check/Create Virtual Environment
if not exist "%VENV_DIR%\Scripts\activate.bat" (
    if exist "%VENV_DIR%" (
        echo  [SETUP] Ambiente virtuale corrotto rilevato. Rimozione...
        rmdir /s /q "%VENV_DIR%"
    )
    echo  [SETUP] Creazione ambiente virtuale Python...
    python -m venv %VENV_DIR%

    if not exist "%VENV_DIR%\Scripts\activate.bat" (
        echo.
        echo  [ERRORE] Impossibile creare l'ambiente virtuale. 
        echo           Assicurati che Python sia installato correttamente.
        pause
        exit /b 1
    )
    echo  [SETUP] [OK] Ambiente virtuale creato
)

:: 2. Activate Virtual Environment
echo  [SETUP] Attivazione ambiente virtuale...
call "%VENV_DIR%\Scripts\activate.bat"

:: 3. Install/Update Dependencies
echo  [SETUP] Verifica dipendenze...
pip install -r src/requirements.txt --quiet --disable-pip-version-check >nul 2>&1
if %errorlevel% neq 0 (
    echo  [SETUP] Installazione dipendenze in corso...
    pip install -r src/requirements.txt
   
    if %errorlevel% neq 0 (
        echo.
        echo  [ERRORE] Impossibile installare le dipendenze.
        pause
        exit /b 1
    )
)
echo  [SETUP] [OK] Dipendenze verificate
echo.

:: 4. Launch App (Modificato per rilevare errori)
echo  ======================================================================
echo  [AVVIO] Avvio applicazione...
echo  ======================================================================
echo.

:: Esecuzione Python e cattura codice di uscita
"%VENV_DIR%\Scripts\python.exe" src/main.py %*
set "EXIT_CODE=%errorlevel%"

echo.
if %EXIT_CODE% neq 0 (
    echo  [CRASH] L'applicazione si e' interrotta con codice %EXIT_CODE%
) else (
    echo  [INFO] Applicazione terminata (Codice 0).
)

:: Pausa incondizionata per leggere eventuali traceback
echo.
echo  Premere un tasto per chiudere la finestra...
pause >nul
exit /b %EXIT_CODE%