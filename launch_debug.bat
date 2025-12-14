@echo off
TITLE Intelleo PDF Splitter v2.0 - DEBUG MODE
COLOR 0E
cls

echo.
echo  +====================================================================+
echo  ^|       INTELLEO PDF SPLITTER - LAUNCHER (DEBUG MODE)               ^|
echo  +====================================================================+
echo.
echo  [DEBUG] Questa modalita' mantiene il CMD aperto per vedere gli errori.
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

:: 4. Launch App in DEBUG mode (console stays open)
echo  ======================================================================
echo  [DEBUG] Avvio applicazione con console visibile...
echo  ======================================================================
echo.

python src/main.py %*
set APP_EXIT_CODE=%errorlevel%

echo.
echo  ======================================================================
if %APP_EXIT_CODE% equ 0 (
    echo  [DEBUG] Applicazione chiusa normalmente (codice: 0)
) else (
    echo  [ERRORE] Applicazione chiusa con errore (codice: %APP_EXIT_CODE%)
)
echo  ======================================================================
echo.
echo  Premi un tasto per chiudere...
pause >nul
exit /b %APP_EXIT_CODE%
