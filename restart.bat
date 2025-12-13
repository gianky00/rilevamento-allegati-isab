@echo off
TITLE Intelleo PDF Splitter - Reset Ambiente
COLOR 0E
cls

echo.
echo  ╔════════════════════════════════════════════════════════════════╗
echo  ║           INTELLEO PDF SPLITTER - RESET AMBIENTE               ║
echo  ╚════════════════════════════════════════════════════════════════╝
echo.
echo  ATTENZIONE: Questo comando cancellera' e reinstallera' l'intero
echo              ambiente Python dell'applicazione.
echo.
echo  Utile se l'app non parte o ci sono errori di dipendenze.
echo.
echo  Premi un tasto per continuare o CTRL+C per annullare...
pause >nul

set VENV_DIR=.venv

if exist %VENV_DIR% (
    echo.
    echo  [RESET] Rimozione ambiente esistente...
    rmdir /s /q %VENV_DIR%
    if %errorlevel% equ 0 (
        echo  [RESET] ✓ Ambiente rimosso
    ) else (
        echo  [ERRORE] Impossibile rimuovere l'ambiente.
        echo           Chiudi tutte le istanze dell'applicazione e riprova.
        pause
        exit /b 1
    )
)

echo.
echo  [RESET] Riavvio procedura di installazione...
echo  ══════════════════════════════════════════════════════════════════
echo.
call launch.bat
