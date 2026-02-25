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

echo Step 1/3: Cleaning old files...
if exist "dist" rmdir /s /q "dist"
if exist "build" rmdir /s /q "build"
if exist "*.spec" del /q "*.spec"

echo.
echo Step 2/3: Building application...
pyinstaller --name="OCRX" --windowed --onefile --icon=assets\icon.ico --add-data="ocrx;ocrx" --hidden-import=tkinter --hidden-import=PIL --hidden-import=fitz --clean main.py

if errorlevel 1 (
    echo.
    echo Error: Build failed!
    pause
    exit /b 1
)

echo.
echo Step 3/3: Copying assets...
if not exist "dist\assets" mkdir "dist\assets"
xcopy /s /i /y "assets\*" "dist\assets\" 2>nul

echo.
echo ==========================================
echo Build Complete!
echo Output: dist\OCRX.exe
echo ==========================================
pause
