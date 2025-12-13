@echo off
TITLE Intelleo PDF Splitter - RESET AMBIENTE
set VENV_DIR=.venv

echo ATTENZIONE: Questo comando cancellera' e reinstallera' l'intero ambiente Python dell'applicazione.
echo Utile se l'app non parte o ci sono errori di dipendenze.
echo.
pause

if exist %VENV_DIR% (
    echo Rimozione ambiente esistente...
    rmdir /s /q %VENV_DIR%
)

echo.
echo Ambiente pulito. Riavvio procedura di installazione...
call launch.bat
