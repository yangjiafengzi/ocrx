# OCRX 2.2 - 智能文字识别系统

## 项目简介

OCRX 2.2 是一款基于 AI 的 OCR（光学字符识别）文字识别工具，支持 PDF 和图片格式的批量处理，具有直观的图形界面和强大的并发处理能力。

**最新版本：v2.2.0** - 全新 CustomTkinter 向导式界面与分层 GUI 架构；示例库/剪贴板/运行日志面板随窗口伸缩并带常显滚动条；端到端测试覆盖保存/复制/取消流程。

## 主要特性

- **AI 驱动**：基于主流视觉大模型，识别精度高
- **少样本提示（Few-shot）**：上传示例图片和正确文本，提升识别准确率
- **批量处理**：支持多文件、多页面并发处理
- **双模式支持**：
  - 识别并保存：将结果保存为 Markdown 文件
  - 识别并复制：将结果复制到剪贴板
- **进度显示**：实时显示处理进度和状态
- **提示词预设**：支持自定义提示词模板
- **剪贴板历史**：自动记录复制历史
- **页面范围**：支持指定 PDF 页码范围
- **增强重试**：5次自动重试，提高成功率
- **向导式工作流**：配置 → 文件 → 提示词 → 执行，减少主界面控件干扰
- **自适应辅助面板**：少样本示例 / 剪贴板 / 运行日志与主区域共享高度，小窗口下不再被压扁，并带常显滚动条

## 系统要求

- **操作系统**：Windows 10/11
- **Python**：3.8 或更高版本
- **依赖库**：
  - tkinter + customtkinter（界面）
  - openai（或其他 API 客户端）
  - PyMuPDF（PDF 处理）
  - Pillow（图片处理）

## 安装方法

1. **克隆或下载项目**
   ```bash
   git clone <repository-url>
   cd ocrx
   ```

2. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

3. **运行程序**
   ```bash
   python main.py
   ```

## 使用说明

### 界面结构

主窗口分为两块：

1. **四步向导**（上方）：配置 → 文件 → 提示词 → 执行  
   通过顶部步骤按钮切换，当前输入会在同一次会话中保留。
2. **辅助面板**（下方）：`少样本示例` / `剪贴板` / `运行日志`  
   与向导区共享窗口高度；小窗口下仍保留可用高度，并提供常显滚动条。

### 向导步骤

**1. 配置**
- Base URL：API 服务地址
- API Key：您的 API 密钥
- Model Name：模型名称（如 gpt-4o）
- 输出目录、并发数、PDF 缩放比例

**2. 文件**
- 添加多个 PDF / 图片文件
- 页码范围（仅 PDF）：如 `1,3,5-10`，留空表示全部页面

**3. 提示词**
- 选择或编辑提示词预设
- 可保存、另存为、重命名、删除、重置预设
- 勾选少样本示例（建议 1-3 个）

**4. 执行**
- **识别并保存**：结果写为 Markdown 文件
- **识别并复制**：结果写入剪贴板（最多约 10 页，超出请用保存模式或缩小页码范围）
- 查看进度、状态与结果预览；可**停止**取消任务
- **复制全部**：结果预览被截断时复制完整内容

### 少样本提示（Few-shot）

1. 在下方 `少样本示例` 面板添加示例图片与正确文本
2. 切换到向导 **提示词** 步，勾选要用的示例
3. 在 **执行** 步开始识别，AI 会参考示例书写风格

### 辅助面板

- **少样本示例**：添加 / 删除 / 刷新示例库
- **剪贴板**：复制历史（复制选中项、清空、刷新）
- **运行日志**：实时日志，可清空

## 项目结构

```
ocrx/
├── main.py                      # 程序入口
├── requirements.txt             # 依赖列表
├── README.md                    # 项目说明
├── CHANGELOG.md                 # 更新日志
├── build_package.bat            # 打包脚本
├── installer.iss                # 安装程序配置
├── ocrx/                        # 主包
│   ├── __init__.py
│   ├── config.py               # 配置管理
│   ├── logger.py               # 日志系统
│   ├── clipboard.py            # 剪贴板管理
│   ├── processing_service.py   # 处理服务
│   ├── pdf_processor.py        # PDF 处理
│   ├── image_processor.py      # 图片处理
│   ├── ocr_engine.py           # OCR 引擎
│   ├── result_merger.py        # 结果合并
│   ├── retry_utils.py          # 重试工具
│   ├── example_library.py      # 示例库管理（v2.1.0新增）
│   └── gui/                    # GUI 模块
│       ├── __init__.py
│       ├── main_window.py      # 主窗口（向导外壳 + 任务编排）
│       ├── app_context.py      # 共享服务与会话状态
│       ├── example_manager_ui.py  # 示例管理界面（v2.1.0新增）
│       ├── views/              # 向导步骤与辅助视图
│       │   ├── config_step.py / files_step.py / prompt_step.py / run_step.py
│       │   └── examples_view.py / clipboard_view.py / logs_view.py
│       └── controllers/        # 工作流控制器
│           ├── save_controller.py / copy_controller.py
│           └── prompt_controller.py / progress_controller.py
```

## 架构设计

### 分层架构

1. **表示层（GUI）**：
   - `main_window.py`：向导外壳（导航、生命周期、任务编排）
   - `views/`：向导步骤与辅助视图（只渲染和回传用户意图）
   - `controllers/`：工作流控制器（save/copy/prompt/progress）

2. **业务逻辑层**：
   - `processing_service.py`：处理服务
   - `ocr_engine.py`：OCR 引擎

3. **数据访问层**：
   - `pdf_processor.py`：PDF 处理
   - `image_processor.py`：图片处理

4. **基础设施层**：
   - `config.py`：配置管理
   - `logger.py`：日志系统
   - `clipboard.py`：剪贴板管理

### 核心流程

```
用户操作 → Views → Controllers → ProcessingService → OCREngine → API
                ↓
            进度回调 ← 结果合并 ← 保存/复制
```

## 配置说明

### 配置文件

配置文件位于用户目录下的 `.ocrx_gui_config.json`：

```json
{
  "BASE_URL": "https://api.example.com",
  "API_KEY": "your-api-key",
  "MODEL_NAME": "gpt-4o",
  "OUTPUT_DIR": "C:/Users/xxx/Documents/OCRX_Output",
  "PDF_SCALE_FACTOR": "3.0",
  "MAX_WORKERS": "10",
  "prompt_templates": {
    "手写笔记": "...",
    "印刷材料": "..."
  }
}
```

### 默认提示词

**手写笔记**：
```
你是一位专业的手写笔记识别专家...
```

**印刷材料**：
```
你是一名专业的OCR（光学字符识别）专家...
```

## 开发文档

### 添加新视图 / 控制器

1. 视图放 `ocrx/gui/views/`：只负责渲染与回调，不直接调用 OCR API
2. 工作流逻辑放 `ocrx/gui/controllers/`：通过 `AppContext` 使用服务
3. 在 `main_window.py` 中装配视图与控制器

> 旧的 `handlers/`（BaseHandler）目录已删除；本文档之外的完整架构与开发
> 约定以 `AGENTS.md` 为准。

### 修改 OCR 引擎

编辑 `ocr_engine.py` 中的 `process_single_image` 方法：

```python
def process_single_image(self, prompt, identifier, image_data):
    # 自定义识别逻辑
    pass
```

### 添加重试机制

使用 `retry_utils.py` 中的工具：

```python
from ocrx.retry_utils import retry_operation

result = retry_operation(
    operation=my_function,
    max_retries=3,
    base_delay=1.0
)
```

## 常见问题

**Q: 识别失败怎么办？**
A: 检查 API 配置是否正确，网络连接是否正常。

**Q: 复制到剪贴板失败？**
A: 确保没有其他程序占用剪贴板，尝试重启程序。

**Q: PDF 转换失败？**
A: 检查 PDF 文件是否损坏，尝试指定页面范围。

**Q: 进度条卡住？**
A: 可能是 API 响应慢，等待或点击"停止"后重试。

## 更新日志

### v2.2.0
- **向导式主界面**：配置 → 文件 → 提示词 → 执行
- **分层 GUI 架构**：`AppContext` + `views/` + `controllers/`（移除旧 handlers）
- **自适应辅助面板**：少样本示例 / 剪贴板 / 运行日志随窗口伸缩，带常显滚动条
- **完整 GUI 端到端测试**：保存 / 复制 / 取消 / 预检失败
- **性能与稳定性**：进度回调节流、剪贴板不阻塞 UI、保存失败不再误报成功

### v2.1.0
- **新增少样本提示功能（Few-shot Prompting）**：上传示例图片和正确文本，显著提升手写笔记等特殊场景的识别准确率
- **新增示例库管理界面**：独立的示例管理界面，支持添加、删除、选择示例
- **增强重试机制**：重试次数从3次增加到5次
- **优化参数解包安全性**：提高代码向后兼容性
- **修复多项bug**：示例ID截断、参数传递、并发处理等问题

### v2.0
- 重构架构，采用处理器模式
- 添加进度条显示
- 添加提示词预设管理
- 添加重试机制
- 优化并发处理

## 许可证

MIT License

## 联系方式

如有问题或建议，请提交 Issue 或联系开发者。
