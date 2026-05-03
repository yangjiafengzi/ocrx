# OCRX 2.0 版本管理指南

## 项目结构规范

```
ocrx2.0/
├── main.py                      # 程序入口
├── requirements.txt             # 依赖列表
├── README.md                    # 项目说明
├── CHANGELOG.md                 # 更新日志
├── VERSION_MANAGEMENT.md        # 本文件
├── .gitignore                   # Git 忽略规则
├── installer.iss                # Inno Setup 安装脚本
├── build_all.bat                # 打包脚本
├── build.ps1                    # PowerShell 打包脚本
├── assets/                      # 资源文件
│   ├── icon.ico                 # 程序图标
│   └── README.txt               # 资源说明
├── docs/                        # 文档
│   ├── ARCHITECTURE.md          # 架构设计
│   ├── USER_GUIDE.md            # 用户指南
│   ├── DEVELOPMENT.md           # 开发文档
│   └── BUILD_PACKAGE.md         # 打包指南
├── ocrx/                        # 主代码包
│   ├── __init__.py              # 版本号
│   ├── config.py
│   ├── logger.py
│   ├── clipboard.py
│   ├── processing_service.py
│   ├── ocr_engine.py
│   ├── result_merger.py
│   ├── retry_utils.py
│   ├── pdf_processor.py
│   ├── image_processor.py
│   └── gui/                     # GUI 模块
│       ├── __init__.py
│       ├── main_window.py
│       └── handlers/            # 处理器
│           ├── __init__.py
│           ├── base_handler.py
│           ├── save_handler.py
│           ├── copy_handler.py
│           ├── clipboard_handler.py
│           ├── result_handler.py
│           ├── prompt_handler.py
│           └── progress_handler.py
└── tests/                       # 测试
    ├── __init__.py
    └── test_*.py
```

## 版本号规范

使用语义化版本号：**主版本.次版本.修订号**

- **主版本**：重大更新，可能不兼容（如 2.0.0 → 3.0.0）
- **次版本**：新功能，向后兼容（如 2.0.0 → 2.1.0）
- **修订号**：Bug 修复（如 2.0.0 → 2.0.1）

## 需要更新的文件

发布新版本时，需要更新以下文件：

1. **`ocrx/__init__.py`** - 版本号
   ```python
   __version__ = "2.0.1"
   ```

2. **`installer.iss`** - 安装程序版本
   ```pascal
   #define MyAppVersion "2.0.1"
   OutputBaseFilename=OCRX_2.0.1_Setup
   ```

3. **`CHANGELOG.md`** - 更新日志
   ```markdown
   ## [2.0.1] - 2026-02-26
   ### Fixed
   - 修复了 xxx 问题
   ```

4. **`README.md`** - 如有必要

## 发布流程

### 1. 开发阶段

```bash
# 创建功能分支
git checkout -b feature/new-feature

# 开发功能
# ...

# 提交更改
git add .
git commit -m "Add new feature"

# 合并到主分支
git checkout main
git merge feature/new-feature
```

### 2. 测试阶段

```bash
# 运行测试
python -m pytest tests/

# 手动测试
python main.py
```

### 3. 版本更新

```bash
# 1. 更新版本号（编辑文件）
# - ocrx/__init__.py
# - installer.iss
# - CHANGELOG.md

# 2. 提交版本更新
git add .
git commit -m "Bump version to 2.0.1"

# 3. 打标签
git tag -a v2.0.1 -m "Version 2.0.1"

# 4. 推送
git push origin main --tags
```

### 4. 打包发布

```bash
# 运行打包脚本
.\build_all.bat

# 或使用 PowerShell
powershell -File build.ps1
```

输出文件：
- `installer/OCRX_2.0.1_Setup.exe`

### 5. 发布到 GitHub

1. 创建 Release
2. 上传 `OCRX_2.0.1_Setup.exe`
3. 填写更新说明

## 文件管理规范

### 应该提交到版本控制的文件

✅ **源代码**：
- `main.py`
- `ocrx/` 目录下的所有 `.py` 文件
- `tests/` 目录下的测试文件

✅ **配置文件**：
- `requirements.txt`
- `installer.iss`
- `.gitignore`

✅ **文档**：
- `README.md`
- `CHANGELOG.md`
- `docs/` 目录下的所有文件

✅ **资源**：
- `assets/` 目录下的图标等资源

✅ **打包脚本**：
- `build_all.bat`
- `build.ps1`

### 不应该提交的文件

❌ **生成的文件**：
- `build/` 目录
- `dist/` 目录
- `installer/` 目录（除了 .iss 脚本）
- `*.spec` 文件
- `__pycache__/` 目录
- `*.pyc` 文件

❌ **临时文件**：
- `test_*.py`（临时测试文件）
- `*.log` 日志文件
- `.ocrx_config.json` 用户配置

❌ **环境相关**：
- `venv/` 虚拟环境
- `.idea/` IDE 配置
- `.vscode/` IDE 配置

## 清理脚本

创建 `clean.bat` 用于清理临时文件：

```batch
@echo off
echo Cleaning temporary files...

REM 删除生成的目录
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "installer" rmdir /s /q "installer"

REM 删除 Python 缓存
for /d /r . %%d in (__pycache__) do @if exist "%%d" rmdir /s /q "%%d"

REM 删除临时文件
del /s /q *.pyc 2>nul
del /s /q *.spec 2>nul
del /s /q *.log 2>nul

echo Clean complete!
pause
```

## 备份策略

### 定期备份

1. **代码备份**：
   - 使用 Git 定期提交
   - 推送到远程仓库（GitHub/GitLab）

2. **发布包备份**：
   - 保留每个版本的安装程序
   - 命名格式：`OCRX_2.0.1_Setup.exe`
   - 存储位置：`releases/` 目录或网盘

### 恢复方法

```bash
# 从 Git 恢复特定版本
git checkout v2.0.0

# 或从标签创建分支
git checkout -b restore-v2.0.0 v2.0.0
```

## 协作开发

### 分支策略

```
main        - 稳定版本
  ↓
develop     - 开发分支
  ↓
feature/*   - 功能分支
  ↓
hotfix/*    - 紧急修复
```

### 提交规范

提交信息格式：`<类型>: <描述>`

类型：
- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更新
- `style`: 代码格式
- `refactor`: 重构
- `test`: 测试
- `chore`: 构建/工具

示例：
```bash
git commit -m "feat: add progress bar display"
git commit -m "fix: resolve clipboard copy issue"
git commit -m "docs: update README"
```

## 常见问题

### Q: 如何回滚到旧版本？

```bash
# 查看历史
git log --oneline

# 回滚到特定提交
git reset --hard <commit-id>

# 或创建回滚分支
git checkout -b rollback <commit-id>
```

### Q: 如何比较版本差异？

```bash
# 比较两个提交
git diff v2.0.0 v2.0.1

# 查看文件历史
git log -p ocrx/main_window.py
```

### Q: 如何管理大文件？

使用 Git LFS（Large File Storage）：
```bash
# 安装 Git LFS
git lfs install

# 追踪大文件
git lfs track "*.exe"
git lfs track "*.ico"
```

---

*文档版本：v1.0*  
*最后更新：2026-02-26*
