# OCRX 2.1 - 智能文字识别系统

## 项目简介

OCRX 2.1 是一款基于 AI 的 OCR（光学字符识别）文字识别工具，支持 PDF 和图片格式的批量处理，具有直观的图形界面和强大的并发处理能力。

**最新版本：v2.1.0** - 新增少样本提示功能，显著提升手写笔记等特殊场景的识别准确率！

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

## 系统要求

- **操作系统**：Windows 10/11
- **Python**：3.8 或更高版本
- **依赖库**：
  - tkinter（Python 标准库）
  - openai（或其他 API 客户端）
  - PyMuPDF（PDF 处理）
  - Pillow（图片处理）

## 安装方法

1. **克隆或下载项目**
   ```bash
   git clone <repository-url>
   cd ocrx2.0
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

### 基本配置

1. **API 配置**：
   - Base URL：API 服务地址
   - API Key：您的 API 密钥
   - Model Name：模型名称（如 gpt-4o）

2. **文件选择**：
   - 点击"选择文件"选择要识别的 PDF 或图片
   - 支持多文件选择

3. **输出目录**：
   - 设置识别结果的保存位置

4. **提示词预设**：
   - 选择适合的提示词模板
   - 支持自定义和保存新预设

### 处理模式

**识别并保存**：
- 识别结果保存为 Markdown 文件
- 适合批量处理大文档
- 自动按文件名组织结果

**识别并复制**：
- 识别结果复制到剪贴板
- 适合快速复制小量内容
- 支持剪贴板历史记录

### 高级功能

**少样本提示（Few-shot Prompting）** [v2.1.0新增]：
1. 切换到"少样本示例库"标签页
2. 点击"添加示例"，选择示例图片并输入正确识别结果
3. 勾选要使用的示例（建议1-3个）
4. 回到"主要配置"，选择目标图片进行识别
5. AI 会参考示例图片的书写风格，给出更准确的识别结果

**页面范围（PDF）**：
- 指定页码范围，如 `1,3,5-10`
- 留空表示处理全部页面

**提示词管理**：
- 保存更改：更新当前预设
- 另存为：创建新预设
- 重命名：修改预设名称
- 删除：删除预设
- 重置所有：恢复默认预设

## 项目结构

```
ocrx2.0/
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
│       ├── main_window.py      # 主窗口
│       ├── example_manager_ui.py  # 示例管理界面（v2.1.0新增）
│       └── handlers/           # 处理器
│           ├── __init__.py
│           ├── base_handler.py
│           ├── save_handler.py
│           ├── copy_handler.py
│           ├── clipboard_handler.py
│           ├── result_handler.py
│           ├── prompt_handler.py
│           └── progress_handler.py
```

## 架构设计

### 分层架构

1. **表示层（GUI）**：
   - `main_window.py`：主窗口界面
   - `handlers/`：功能处理器

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
用户操作 → GUI → Handler → ProcessingService → OCREngine → API
                ↓
            进度回调 ← 结果合并 ← 保存/复制
```

## 配置说明

### 配置文件

配置文件位于用户目录下的 `.ocrx_config.json`：

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

### 添加新处理器

1. 在 `handlers/` 目录下创建新文件
2. 继承 `BaseHandler`
3. 实现必要的方法
4. 在 `main_window.py` 中初始化和使用

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
