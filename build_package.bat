@echo off
chcp 65001 >nul
cls
echo ==========================================
echo OCRX 2.1.0 Build Script
echo ==========================================
echo.

REM Check if in project root
if not exist "main.py" (
    echo [Error] Please run this script in project root directory!
    pause
    exit /b 1
)

REM Step 1: Clean
echo [1/4] Cleaning old files...
if exist "dist" rmdir /s /q "dist"
if exist "build" rmdir /s /q "build"
if exist "*.spec" del /q "*.spec"
if exist "installer" rmdir /s /q "installer"
echo     Done

REM Step 2: PyInstaller
echo.
echo [2/4] Building with PyInstaller...
echo     This may take 5-10 minutes, please wait...
pyinstaller --name="OCRX-2.1.0" --windowed --onefile --icon=assets\icon.ico --add-data="ocrx;ocrx" --add-data="assets;assets" --additional-hooks-dir=. --hidden-import=tkinter --hidden-import=PIL --hidden-import=PIL._imaging --hidden-import=PIL._imagingtk --hidden-import=PIL._tkinter_finder --hidden-import=fitz --hidden-import=fitz.fitz --hidden-import=PyMuPDF --collect-all=fitz --collect-all=PyMuPDF --copy-metadata=PyMuPDF --clean --noconfirm main.py

if errorlevel 1 (
    echo.
    echo [Error] PyInstaller build failed!
    pause
    exit /b 1
)
echo     Done

REM Step 3: Prepare installer files
echo.
echo [3/4] Preparing installer files...
mkdir installer 2>nul
copy "dist\OCRX-2.1.0.exe" "installer\OCRX-2.1.0.exe" >nul
copy "assets\README.txt" "installer\README.txt" >nul
echo     Done

REM Step 4: Inno Setup
echo.
echo [4/4] Building installer...
echo     Checking Inno Setup...

set "INNO_PATH=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if not exist "%INNO_PATH%" (
    set "INNO_PATH=C:\Program Files\Inno Setup 6\ISCC.exe"
)

if exist "%INNO_PATH%" (
    "%INNO_PATH%" installer.iss
    if errorlevel 1 (
        echo [Warning] Inno Setup compile failed, but single exe is ready
    ) else (
        echo     Installer build complete
    )
) else (
    echo [Warning] Inno Setup not found, skipping installer
    echo     Single exe ready: dist\OCRX-2.1.0.exe
)

echo.
echo ==========================================
echo Build Complete!
echo ==========================================
echo.
echo Output files:
echo   - Single exe: dist\OCRX-2.1.0.exe
echo   - Installer:  installer\OCRX_2.1.0_Setup.exe (if Inno Setup installed)
echo.
pause
