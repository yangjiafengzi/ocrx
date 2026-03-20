@echo off
chcp 65001 >nul
cls
echo ==========================================
echo OCRX 2.1.0 Build Script
echo ==========================================
echo.

REM 检查是否在项目根目录
if not exist "main.py" (
    echo [错误] 请在项目根目录运行此脚本！
    pause
    exit /b 1
)

REM 步骤1: 清理旧文件
echo [1/4] 清理旧文件...
if exist "dist" rmdir /s /q "dist"
if exist "build" rmdir /s /q "build"
if exist "*.spec" del /q "*.spec"
if exist "installer" rmdir /s /q "installer"
echo     清理完成

REM 步骤2: PyInstaller 打包
echo.
echo [2/4] PyInstaller 打包中...
echo     这可能需要 5-10 分钟，请耐心等待...
pyinstaller ^
    --name="OCRX-2.1.0" ^
    --windowed ^
    --onefile ^
    --icon=assets\icon.ico ^
    --add-data="ocrx;ocrx" ^
    --add-data="assets;assets" ^
    --hidden-import=tkinter ^
    --hidden-import=PIL ^
    --hidden-import=PIL._imaging ^
    --hidden-import=PIL._imagingtk ^
    --hidden-import=PIL._tkinter_finder ^
    --hidden-import=fitz ^
    --hidden-import=PyMuPDF ^
    --collect-all=fitz ^
    --collect-all=PyMuPDF ^
    --clean ^
    --noconfirm ^
    main.py

if errorlevel 1 (
    echo.
    echo [错误] PyInstaller 打包失败！
    pause
    exit /b 1
)
echo     打包完成

REM 步骤3: 准备安装程序文件
echo.
echo [3/4] 准备安装程序文件...
mkdir installer 2>nul
copy "dist\OCRX-2.1.0.exe" "installer\OCRX-2.1.0.exe" >nul
copy "assets\README.txt" "installer\README.txt" >nul
echo     准备完成

REM 步骤4: Inno Setup 制作安装包
echo.
echo [4/4] 制作安装程序...
echo     检查 Inno Setup...

set "INNO_PATH=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if not exist "%INNO_PATH%" (
    set "INNO_PATH=C:\Program Files\Inno Setup 6\ISCC.exe"
)

if exist "%INNO_PATH%" (
    "%INNO_PATH%" installer.iss
    if errorlevel 1 (
        echo [警告] Inno Setup 编译失败，但单文件 exe 已生成
    ) else (
        echo     安装程序制作完成
    )
) else (
    echo [警告] 未找到 Inno Setup，跳过安装程序制作
    echo     单文件 exe 已生成: dist\OCRX-2.1.0.exe
)

echo.
echo ==========================================
echo 打包完成！
echo ==========================================
echo.
echo 输出文件:
echo   - 单文件版本: dist\OCRX-2.1.0.exe
echo   - 安装程序:   installer\OCRX-2.1.0-Setup.exe (如果 Inno Setup 安装)
echo.
pause