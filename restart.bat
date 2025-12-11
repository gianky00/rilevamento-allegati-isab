@echo off
TITLE PDF Splitter - Ripristino Ambiente

echo.
echo ===================================================
echo  ATTENZIONE: Questo script disinstallera' tutte le
echo  librerie Python correnti e le reinstallera'.
echo ===================================================
echo.
pause

REM Check Python
python --version >nul 2>nul
if %errorlevel% neq 0 (
    echo Python non trovato nel PATH.
    pause
    exit /b
)

echo.
echo 1. Disinstallazione librerie correnti...
echo.

REM Genera lista pacchetti installati
pip freeze > temp_uninstall_list.txt

REM Se la lista non è vuota, disinstalla
for %%A in (temp_uninstall_list.txt) do if %%~zA==0 (
    echo Nessuna libreria da disinstallare.
) else (
    pip uninstall -r temp_uninstall_list.txt -y
)

REM Pulizia
if exist temp_uninstall_list.txt del temp_uninstall_list.txt

echo.
echo 2. Reinstallazione dipendenze da requirements.txt...
echo.

pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo.
    echo ERRORE durante la reinstallazione.
    pause
    exit /b
)

echo.
echo ===================================
echo  Ripristino completato con successo!
echo ===================================
echo.
pause
exit /b
