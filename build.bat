
@echo off
setlocal
echo [INFO] Starting build process...

echo [INFO] Cleaning up...
rmdir /s /q build
rmdir /s /q dist

echo [INFO] Running PyInstaller...
call conda run -n work pyinstaller build.spec
if errorlevel 1 (
    echo [ERROR] PyInstaller failed!
    exit /b 1
)

echo [INFO] Copying Assets...
set "DIST_DIR=dist\BidSystem"

echo [INFO] Copying Browsers...
set "SOURCE_BROWSERS=%USERPROFILE%\AppData\Local\ms-playwright"
if not exist "%SOURCE_BROWSERS%" (
    set "SOURCE_BROWSERS=C:\Users\Administrator\AppData\Local\ms-playwright"
)

if exist "%SOURCE_BROWSERS%" (
    echo [INFO] Found browsers, copying...
    xcopy /E /I /H /Y /Q "%SOURCE_BROWSERS%" "%DIST_DIR%\browsers"
) else (
    echo [WARNING] Playwright browsers not found!
)

echo [INFO] Copying App Data...
xcopy /E /I /H /Y /Q "config" "%DIST_DIR%\config"
xcopy /E /I /H /Y /Q "data" "%DIST_DIR%\data"
xcopy /E /I /H /Y /Q "web" "%DIST_DIR%\web"
copy /Y "README.md" "%DIST_DIR%\"
copy /Y "public.pem" "%DIST_DIR%\"

echo [INFO] Verifying exclusions...
if exist "%DIST_DIR%\keygen.py" del "%DIST_DIR%\keygen.py"
if exist "%DIST_DIR%\private.pem" del "%DIST_DIR%\private.pem"

echo [INFO] Build Complete! Output is in %DIST_DIR%
pause
