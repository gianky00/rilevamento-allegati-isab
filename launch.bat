@echo off
TITLE PDF Splitter Launcher

REM Controlla se pip è installato
pip --version >nul 2>nul
if %errorlevel% neq 0 (
    echo pip non è installato o non è nel PATH.
    echo Assicurati che Python sia installato correttamente e aggiunto al PATH.
    pause
    exit /b
)

echo.
echo ===================================
echo  Installazione dipendenze in corso...
echo ===================================
echo.
pip install -r requirements.txt

echo.
echo ===================================
echo  Avvio dell'applicazione...
echo ===================================
echo.
start "" pythonw main.py
exit
