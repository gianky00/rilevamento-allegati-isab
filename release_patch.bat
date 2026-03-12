@echo off
echo ========================================================
echo      INTELLEO PDF SPLITTER - FULL AUTOMATED RELEASE
echo ========================================================
set VENV_DIR=.venv

:: 1. Environment Prep (VENV)
echo [1/5] Checking Environment (%VENV_DIR%)...
if not exist "%VENV_DIR%\Scripts\activate.bat" (
    if exist "%VENV_DIR%" (
        echo Corrupt venv detected. Cleaning...
        rmdir /s /q "%VENV_DIR%"
    )
    echo Creating virtual environment...
    python -m venv %VENV_DIR%

    if not exist "%VENV_DIR%\Scripts\activate.bat" (
        echo ERROR: Could not create virtual environment. Check Python installation.
        pause
        exit /b 1
    )
)
call "%VENV_DIR%\Scripts\activate.bat"

echo Updating dependencies...
python -m pip install --upgrade pip
pip install -r src/requirements.txt
if %errorlevel% neq 0 (
    echo Error installing dependencies!
    pause
    exit /b %errorlevel%
)

:: 2. Run Tests
echo.
echo [2/5] Running Unit Tests...
pytest
if %errorlevel% neq 0 (
    echo TESTS FAILED! Aborting release.
    echo Please fix the errors before deploying.
    pause
    exit /b %errorlevel%
)
echo Tests passed.

:: Clean previous builds
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
echo Cleaned previous build artifacts.

:: 3. Bump Version
echo.
echo [3/5] Incrementing Patch Version...
python "admin/Crea Setup/bump_version.py" patch
if %errorlevel% neq 0 (
    echo Error bumping version!
    pause
    exit /b %errorlevel%
)

:: 4. Build & Full Deploy (Network + Web)
echo.
echo [4/5] Building and Uploading to NETWORK and NETLIFY...
echo This may take a few minutes...
python "admin/Crea Setup/build_dist.py"
if %errorlevel% neq 0 (
    echo Error during build or deployment process!
    pause
    exit /b %errorlevel%
)

:: 5. Finalizing
echo.
echo [5/5] Release Process Completed!
echo.
echo New version is live on NETWORK and NETLIFY.
pause
