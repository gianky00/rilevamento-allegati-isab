@echo off
TITLE Intelleo PDF Splitter - Reset Ambiente
COLOR 0E
cls

echo.
echo  +====================================================================+
echo  ^|       INTELLEO PDF SPLITTER - RESET AMBIENTE VIRTUALE             ^|
echo  +====================================================================+
echo.
echo  [!] ATTENZIONE: Questo script rimuovera' l'ambiente virtuale
echo                  e lo ricreera' da zero.
echo.
echo  Premi un tasto per continuare o chiudi la finestra per annullare...
pause >nul

set VENV_DIR=.venv

echo.
echo  [RESET] Rimozione ambiente virtuale esistente...

if exist "%VENV_DIR%" (
    rmdir /s /q "%VENV_DIR%"
    if exist "%VENV_DIR%" (
        echo  [ERRORE] Impossibile rimuovere la cartella %VENV_DIR%
        echo           Chiudi eventuali programmi che la stanno usando.
        pause
        exit /b 1
    )
    echo  [RESET] [OK] Ambiente virtuale rimosso
) else (
    echo  [RESET] [OK] Nessun ambiente virtuale esistente
)

echo.
echo  [RESET] Creazione nuovo ambiente virtuale...
python -m venv %VENV_DIR%

if not exist "%VENV_DIR%\Scripts\activate.bat" (
    echo  [ERRORE] Impossibile creare l'ambiente virtuale.
    pause
    exit /b 1
)

echo  [RESET] [OK] Ambiente virtuale creato
echo.
echo  [RESET] Attivazione ambiente virtuale...
call "%VENV_DIR%\Scripts\activate.bat"

echo  [RESET] Installazione dipendenze...
pip install -r src/requirements.txt

if %errorlevel% neq 0 (
    echo.
    echo  [ERRORE] Installazione dipendenze fallita.
    pause
    exit /b 1
)

echo.
echo  +====================================================================+
echo  [OK] Reset completato con successo!
echo  +====================================================================+
echo.
echo  Usa launch.bat per avviare l'applicazione.
echo.
pause
