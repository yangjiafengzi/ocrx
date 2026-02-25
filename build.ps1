# OCRX 2.0 Build Script for PowerShell

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "OCRX 2.0 Build Tool" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Check if in project root
if (-not (Test-Path "main.py")) {
    Write-Host "Error: Please run this script in project root directory!" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Step 1: Clean
Write-Host "[1/4] Cleaning old files..." -ForegroundColor Yellow
if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
if (Test-Path "installer") { Remove-Item -Recurse -Force "installer" }
Get-ChildItem -Filter "*.spec" | Remove-Item -Force

# Step 2: PyInstaller
Write-Host ""
Write-Host "[2/4] Building with PyInstaller..." -ForegroundColor Yellow
pyinstaller --name="OCRX" --windowed --onefile --icon=assets\icon.ico --add-data="ocrx;ocrx" --hidden-import=tkinter --hidden-import=PIL --hidden-import=fitz --clean main.py

if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: PyInstaller build failed!" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Step 3: Copy assets
Write-Host ""
Write-Host "[3/4] Copying assets..." -ForegroundColor Yellow
if (-not (Test-Path "dist\assets")) { New-Item -ItemType Directory -Path "dist\assets" }
Copy-Item -Path "assets\*" -Destination "dist\assets\" -Recurse -Force -ErrorAction SilentlyContinue

# Step 4: Inno Setup
Write-Host ""
Write-Host "[4/4] Building installer with Inno Setup..." -ForegroundColor Yellow
$innoPath = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if (Test-Path $innoPath) {
    & $innoPath installer.iss
} else {
    Write-Host "Warning: Inno Setup not found, please compile installer.iss manually" -ForegroundColor Yellow
    Write-Host "Installer not generated, but single file version is in dist\ directory" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "Build Complete!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
if (Test-Path "installer\OCRX_2.0.0_Setup.exe") {
    Write-Host "Installer: installer\OCRX_2.0.0_Setup.exe" -ForegroundColor Green
} else {
    Write-Host "Single file: dist\OCRX.exe" -ForegroundColor Green
}
Write-Host "==========================================" -ForegroundColor Green
Read-Host "Press Enter to exit"
