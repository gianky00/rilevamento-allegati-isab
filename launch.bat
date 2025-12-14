@echo off
TITLE Intelleo PDF Splitter v2.0
COLOR 0B
cls

echo.
echo  +====================================================================+
echo  ^|           INTELLEO PDF SPLITTER - LAUNCHER                        ^|
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

:: 4. Launch App using pythonw (no console) and exit
echo  ======================================================================
echo  [AVVIO] Avvio applicazione...
echo  ======================================================================
echo.

:: Use START with pythonw to launch GUI without keeping console open
:: pythonw runs Python without a console window
start "" "%VENV_DIR%\Scripts\pythonw.exe" src/main.py %*

:: Exit immediately - the app runs independently
exit /b 0
