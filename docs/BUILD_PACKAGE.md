# OCRX 2.0 打包发布指南

## 概述

本指南将教你如何将 OCRX 2.0 打包成 Windows 安装程序（.exe 安装包）。

## 打包流程

```
Python 源代码
    ↓
PyInstaller 打包 → 单个 exe 文件 + 依赖文件
    ↓
Inno Setup 封装 → Windows 安装程序（Setup.exe）
```

## 准备工作

### 1. 安装必要软件

**需要安装的软件：**

1. **Python 3.8+**（已安装）
2. **PyInstaller**（Python 打包工具）
3. **Inno Setup**（Windows 安装程序制作工具）

### 2. 安装 PyInstaller

打开命令提示符（CMD）或 PowerShell：

```bash
# 安装 PyInstaller
pip install pyinstaller

# 验证安装
pyinstaller --version
```

### 3. 下载并安装 Inno Setup

1. 访问官网：https://jrsoftware.org/isinfo.php
2. 下载最新版本的 Inno Setup
3. 运行安装程序，按提示安装
4. 记住安装路径（通常是 `C:\Program Files (x86)\Inno Setup 6`）

## 第一步：使用 PyInstaller 打包

### 1. 创建打包脚本

我已经为你创建了打包脚本 `build_exe.bat`：

```batch
@echo off
chcp 65001
cls
echo ==========================================
echo OCRX 2.0 打包工具
echo ==========================================
echo.

REM 检查是否在项目根目录
if not exist "main.py" (
    echo 错误：请在项目根目录运行此脚本！
    pause
    exit /b 1
)

echo 步骤 1/3: 清理旧文件...
if exist "dist" rmdir /s /q "dist"
if exist "build" rmdir /s /q "build"
if exist "*.spec" del /q "*.spec"

echo.
echo 步骤 2/3: 打包应用程序...
pyinstaller ^
    --name="OCRX" ^
    --windowed ^
    --onefile ^
    --icon=assets\icon.ico ^
    --add-data="ocrx;ocrx" ^
    --hidden-import=tkinter ^
    --hidden-import=PIL ^
    --hidden-import=fitz ^
    --clean ^
    main.py

if errorlevel 1 (
    echo.
    echo 错误：打包失败！
    pause
    exit /b 1
)

echo.
echo 步骤 3/3: 复制额外文件...
if not exist "dist\assets" mkdir "dist\assets"
xcopy /s /i /y "assets\*" "dist\assets\" 2>nul

echo.
echo ==========================================
echo 打包完成！
echo 输出目录: dist\
echo ==========================================
pause
```

### 2. 准备图标文件

创建 `assets` 文件夹并添加图标：

```bash
# 创建 assets 文件夹
mkdir assets

# 将你的图标文件命名为 icon.ico 放入 assets 文件夹
# 如果没有图标，可以使用默认的
```

### 3. 运行打包脚本

双击运行 `build_exe.bat`，或者命令行执行：

```bash
build_exe.bat
```

等待打包完成，输出在 `dist\OCRX.exe`

### 4. 测试打包结果

```bash
# 运行打包后的程序
dist\OCRX.exe
```

## 第二步：使用 Inno Setup 创建安装程序

### 1. 创建安装脚本

我已经为你创建了 Inno Setup 脚本 `installer.iss`：

```pascal
; OCRX 2.0 安装脚本
; 使用 Inno Setup 编译

#define MyAppName "OCRX"
#define MyAppVersion "2.0.0"
#define MyAppPublisher "OCRX Team"
#define MyAppURL "https://github.com/yourusername/ocrx"
#define MyAppExeName "OCRX.exe"

[Setup]
; 应用程序信息
AppId={{YOUR-GUID-HERE}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}

; 默认安装目录
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}

; 输出文件名
OutputDir=installer
OutputBaseFilename=OCRX_2.0.0_Setup

; 压缩设置
Compression=lzma2
SolidCompression=yes

; 图标和样式
SetupIconFile=assets\icon.ico
WizardStyle=modern

; 权限设置
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

; 版本信息
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName} - 智能文字识别系统
VersionInfoTextVersion={#MyAppVersion}

[Languages]
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode

[Files]
; 主程序文件
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

; 依赖文件和目录
Source: "dist\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; 文档
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "CHANGELOG.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; 开始菜单图标
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{group}\README"; Filename: "{app}\README.md"

; 桌面图标
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

; 快速启动图标
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Run]
; 安装完成后可选运行
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; 卸载时删除的文件和目录
Type: filesandordirs; Name: "{app}"

[Code]
// 安装前检查
function InitializeSetup(): Boolean;
begin
  Result := true;
end;

// 安装完成后显示信息
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    // 可以在这里添加安装后的操作
  end;
end;
```

### 2. 修改脚本中的 GUID

打开 `installer.iss`，找到这一行：

```pascal
AppId={{YOUR-GUID-HERE}}
```

替换为新的 GUID（可以使用在线 GUID 生成器）：

```pascal
AppId={{12345678-1234-1234-1234-123456789012}}
```

### 3. 编译安装程序

**方法一：使用 Inno Setup 编译器**

1. 打开 Inno Setup Compiler
2. 选择 `File` → `Open`，打开 `installer.iss`
3. 点击工具栏的绿色运行按钮（或按 F9）
4. 等待编译完成

**方法二：使用命令行编译**

```bash
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
```

### 4. 输出文件

编译完成后，安装程序在 `installer\OCRX_2.0.0_Setup.exe`

## 第三步：测试安装程序

### 1. 测试安装

1. 双击运行 `OCRX_2.0.0_Setup.exe`
2. 按提示完成安装
3. 检查开始菜单和桌面图标
4. 运行程序，测试功能

### 2. 测试卸载

1. 打开控制面板 → 程序和功能
2. 找到 OCRX，点击卸载
3. 确认卸载干净

## 第四步：发布分发

### 1. 准备发布文件

创建发布文件夹：

```
release/
├── OCRX_2.0.0_Setup.exe    # 安装程序
├── README.txt               # 快速说明
└── LICENSE.txt              # 许可证
```

### 2. README.txt 内容

```
OCRX 2.0 - 智能文字识别系统
==============================

安装方法：
1. 双击运行 OCRX_2.0.0_Setup.exe
2. 按提示完成安装
3. 从开始菜单或桌面启动程序

系统要求：
- Windows 10/11
- 无需安装 Python

使用说明：
1. 配置 API 信息（Base URL、API Key、Model Name）
2. 选择要识别的文件
3. 点击"识别并保存"或"识别并复制"

卸载方法：
- 控制面板 → 程序和功能 → OCRX → 卸载
- 或开始菜单 → OCRX → 卸载

更多信息请查看安装目录下的 README.md
```

### 3. 分发方式

- **GitHub Releases**：上传到 GitHub Release 页面
- **网盘分享**：百度网盘、阿里云盘等
- **网站下载**：上传到自己的网站

## 自动打包脚本（一键打包）

我为你创建了一键打包脚本 `build_all.bat`：

```batch
@echo off
chcp 65001
cls
echo ==========================================
echo OCRX 2.0 一键打包工具
echo ==========================================
echo.

REM 检查必要文件
if not exist "main.py" (
    echo 错误：请在项目根目录运行此脚本！
    pause
    exit /b 1
)

REM 步骤 1: 清理
echo [1/4] 清理旧文件...
if exist "dist" rmdir /s /q "dist"
if exist "build" rmdir /s /q "build"
if exist "installer" rmdir /s /q "installer"
if exist "*.spec" del /q "*.spec"

REM 步骤 2: PyInstaller 打包
echo.
echo [2/4] PyInstaller 打包...
pyinstaller --name="OCRX" --windowed --onefile --icon=assets\icon.ico --add-data="ocrx;ocrx" --hidden-import=tkinter --hidden-import=PIL --hidden-import=fitz --clean main.py

if errorlevel 1 (
    echo 错误：PyInstaller 打包失败！
    pause
    exit /b 1
)

REM 步骤 3: 复制资源文件
echo.
echo [3/4] 复制资源文件...
if not exist "dist\assets" mkdir "dist\assets"
xcopy /s /i /y "assets\*" "dist\assets\" 2>nul

REM 步骤 4: Inno Setup 打包
echo.
echo [4/4] Inno Setup 打包...
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
) else (
    echo 警告：未找到 Inno Setup，请手动编译 installer.iss
    echo 安装程序未生成，但单文件版本已生成在 dist\ 目录
)

echo.
echo ==========================================
echo 打包完成！
echo ==========================================
if exist "installer\OCRX_2.0.0_Setup.exe" (
    echo 安装程序: installer\OCRX_2.0.0_Setup.exe
) else (
    echo 单文件版本: dist\OCRX.exe
)
echo ==========================================
pause
```

## 常见问题

### Q: 打包后的程序很大？

A: 这是正常的，因为包含了 Python 解释器和所有依赖。可以使用 UPX 压缩：

```bash
pip install upx-binary
pyinstaller --upx-dir="path\to\upx" ...
```

### Q: 杀毒软件报毒？

A: PyInstaller 打包的程序有时会被误报。可以：
1. 将程序添加到杀毒软件白名单
2. 使用代码签名证书签名
3. 向杀毒软件厂商提交误报

### Q: 程序无法运行？

A: 检查是否缺少依赖：
1. 使用 `--onedir` 代替 `--onefile` 测试
2. 检查日志文件
3. 确保所有资源文件都正确打包

### Q: 如何更新版本？

A: 
1. 修改 `installer.iss` 中的版本号
2. 修改 `ocrx\__init__.py` 中的版本号
3. 重新运行打包脚本
4. 更新 CHANGELOG.md

## 维护更新流程

### 日常维护

1. **修改代码**：编辑源代码
2. **测试**：运行 `python main.py` 测试
3. **打包**：运行 `build_all.bat`
4. **发布**：上传新版本

### 版本更新

1. 更新版本号（`installer.iss` 和 `__init__.py`）
2. 更新 `CHANGELOG.md`
3. 重新打包
4. 发布新版本

## 联系支持

如有问题，请查看文档或提交 Issue。

---

*文档版本：v1.0*  
*最后更新：2026-02-26*
