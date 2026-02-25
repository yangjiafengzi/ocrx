@echo off
chcp 65001 >nul
cls
echo ==========================================
echo OCRX 2.0 Build Tool
echo ==========================================
echo.

REM Check if in project root
if not exist "main.py" (
    echo Error: Please run this script in project root directory!
    pause
    exit /b 1
)

REM Step 1: Clean
echo [1/4] Cleaning old files...
if exist "dist" rmdir /s /q "dist"
if exist "build" rmdir /s /q "build"
if exist "installer" rmdir /s /q "installer"
if exist "*.spec" del /q "*.spec"

REM Step 2: PyInstaller
echo.
echo [2/4] Building with PyInstaller...
pyinstaller --name="OCRX" --windowed --onefile --icon=assets\icon.ico --add-data="ocrx;ocrx" --hidden-import=tkinter --hidden-import=PIL --hidden-import=fitz --clean main.py

if errorlevel 1 (
    echo Error: PyInstaller build failed!
    pause
    exit /b 1
)

REM Step 3: Copy assets
echo.
echo [3/4] Copying assets...
if not exist "dist\assets" mkdir "dist\assets"
xcopy /s /i /y "assets\*" "dist\assets\" 2>nul

REM Step 4: Inno Setup
echo.
echo [4/4] Building installer with Inno Setup...
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
) else (
    echo Warning: Inno Setup not found, please compile installer.iss manually
    echo Installer not generated, but single file version is in dist\ directory
)

echo.
echo ==========================================
echo Build Complete!
echo ==========================================
if exist "installer\OCRX_2.0.0_Setup.exe" (
    echo Installer: installer\OCRX_2.0.0_Setup.exe
) else (
    echo Single file: dist\OCRX.exe
)
echo ==========================================
pause
