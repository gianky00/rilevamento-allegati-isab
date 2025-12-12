@echo off
echo ========================================================
echo      INTELLEO PDF SPLITTER - AUTOMATED RELEASE
echo ========================================================

:: 1. Environment Check & Prep
echo [1/4] Checking Environment...
pip install --upgrade pip
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo Error installing dependencies!
    pause
    exit /b %errorlevel%
)

:: Clean previous builds
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
echo Cleaned previous build artifacts.

:: 2. Bump Version
echo.
echo [2/4] Incrementing Patch Version...
python admin/bump_version.py patch
if %errorlevel% neq 0 (
    echo Error bumping version!
    pause
    exit /b %errorlevel%
)

:: 3. Build & Deploy
echo.
echo [3/4] Building Application and Installer...
echo This may take a few minutes...
python admin/build_dist.py
if %errorlevel% neq 0 (
    echo Error during build/deploy process!
    pause
    exit /b %errorlevel%
)

:: 4. Finalizing
echo.
echo [4/4] Release Process Completed!
echo.
echo New version is live on Netlify.
pause
