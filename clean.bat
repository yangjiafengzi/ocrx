@echo off
echo ==========================================
echo OCRX 2.0 - Clean Temporary Files
echo ==========================================
echo.

echo [1/4] Removing build directories...
if exist "build" (
    rmdir /s /q "build"
    echo   - build/ removed
)
if exist "dist" (
    rmdir /s /q "dist"
    echo   - dist/ removed
)
if exist "installer" (
    rmdir /s /q "installer"
    echo   - installer/ removed
)

echo.
echo [2/4] Removing Python cache...
for /d /r . %%d in (__pycache__) do (
    if exist "%%d" (
        rmdir /s /q "%%d" 2>nul
    )
)
echo   - __pycache__/ removed

echo.
echo [3/4] Removing temporary files...
del /s /q *.pyc 2>nul
del /s /q *.spec 2>nul
del /s /q *.log 2>nul
del /s /q test_*.py 2>nul
echo   - *.pyc removed
echo   - *.spec removed
echo   - *.log removed
echo   - test_*.py removed

echo.
echo [4/4] Removing old markdown files...
del /q "重构*.md" 2>nul
del /q "更新说明*.md" 2>nul
del /q "问题诊断*.md" 2>nul
del /q "验证报告*.md" 2>nul
del /q "开发指南*.md" 2>nul
echo   - Old markdown files removed

echo.
echo ==========================================
echo Clean complete!
echo ==========================================
pause
