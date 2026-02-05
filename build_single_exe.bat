@echo off
setlocal enabledelayedexpansion
echo ========================================
echo  BidScraper OneDir Build Script
echo ========================================
echo.

REM Check if conda is available
where conda >nul 2>nul
if errorlevel 1 (
    echo [ERROR] conda not found in PATH. Please install Anaconda/Miniconda or add it to PATH.
    pause
    exit /b 1
)

echo [INFO] Activating conda environment 'work'...
call conda activate work
if errorlevel 1 (
    echo [ERROR] Failed to activate conda environment 'work'.
    echo        Please create it first with: conda create -n work python=3.10
    pause
    exit /b 1
)

echo [INFO] Cleaning up previous build...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo.
echo [INFO] Running PyInstaller...
pyinstaller single_exe.spec --log-level=INFO
if errorlevel 1 (
    echo.
    echo [ERROR] PyInstaller failed! Please check the error messages above.
    pause
    exit /b 1
)

echo.
echo [INFO] Copying data files to root of dist\BidScraper...

REM Copy data files to dist\BidScraper root if they're not already there
if exist "public.pem" xcopy /Y /I "public.pem" "dist\BidScraper\" >nul
if exist "README.md" xcopy /Y /I "README.md" "dist\BidScraper\" >nul
if exist "config" xcopy /Y /E /I "config" "dist\BidScraper\config\" >nul
if exist "web" xcopy /Y /E /I "web" "dist\BidScraper\web\" >nul

REM Copy Playwright browsers if found
set BROWSERS_FOUND=0

REM Check user-local installation
if exist "%LOCALAPPDATA%\ms-playwright" (
    echo [INFO] Copying Playwright browsers from %%LOCALAPPDATA%%\ms-playwright...
    xcopy /Y /E /I "%LOCALAPPDATA%\ms-playwright" "dist\BidScraper\browsers\" >nul 2>&1
    if exist "dist\BidScraper\browsers" set BROWSERS_FOUND=1
)

REM Check system-wide installation
if exist "C:\ms-playwright" (
    echo [INFO] Copying Playwright browsers from C:\ms-playwright...
    xcopy /Y /E /I "C:\ms-playwright" "dist\BidScraper\browsers\" >nul 2>&1
    if exist "dist\BidScraper\browsers" set BROWSERS_FOUND=1
)

REM Check home directory
if exist "%USERPROFILE%\AppData\Local\ms-playwright" (
    if not exist "dist\BidScraper\browsers" (
        echo [INFO] Copying Playwright browsers from USERPROFILE...
        xcopy /Y /E /I "%USERPROFILE%\AppData\Local\ms-playwright" "dist\BidScraper\browsers\" >nul 2>&1
        if exist "dist\BidScraper\browsers" set BROWSERS_FOUND=1
    )
)

if %BROWSERS_FOUND%==0 (
    echo [WARNING] Playwright browsers not found! Please run: playwright install
    echo [WARNING] The packaged program will NOT be able to browse web pages!
) else (
    echo [INFO] Browsers copied successfully.
)

echo.
echo ========================================
echo  Build Complete!
echo ========================================
echo.
echo Output structure:
echo   dist\BidScraper\
echo   ├─ BidScraper.exe        (Main program - RUN THIS)
echo   ├─ public.pem            (Public key for verification)
echo   ├─ README.md             (Documentation)
echo   ├─ config\               (Config files)
echo   ├─ web\                  (Web UI files)
echo   ├─ browsers\             (Playwright browsers - if found)
echo   └─ _internal\            (Python runtime and dependencies)
echo.
echo Files EXCLUDED from the package:
echo   - keygen.py (license key generator)
echo   - private.pem (private key for signing)
echo   - license_db.json (license database)
echo.
echo ========================================
echo  Testing Instructions
echo ========================================
echo.
echo To test in Windows Sandbox:
echo.
echo 1. Copy the entire dist\BidScraper folder
echo 2. Paste it into Windows Sandbox
echo 3. Double-click BidScraper.exe to run
echo 4. Open browser to http://localhost:8000
echo 5. Verify the license prompt appears
echo.
echo For distribution:
echo   - Zip the entire BidScraper folder
echo   - Users extract and run BidScraper.exe
echo   - No Python installation required
echo.
echo ========================================
pause
