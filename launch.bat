@echo off
TITLE Intelleo PDF Splitter Launcher
set VENV_DIR=.venv

:: 1. Check/Create Virtual Environment
if not exist %VENV_DIR% (
    echo Creazione ambiente virtuale in %VENV_DIR%...
    python -m venv %VENV_DIR%
)

:: 2. Activate Virtual Environment
call %VENV_DIR%\Scripts\activate.bat

:: 3. Install Dependencies (Quietly update)
echo Verifica dipendenze...
pip install -r requirements.txt >nul 2>&1
if %errorlevel% neq 0 (
    echo Errore installazione dipendenze. Tentativo verbose...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo Errore critico dipendenze.
        pause
        exit /b
    )
)

:: 4. Launch App
echo Avvio Intelleo PDF Splitter...
python main.py

if %errorlevel% neq 0 (
    echo.
    echo L'applicazione si e' chiusa con un errore.
    pause
)
