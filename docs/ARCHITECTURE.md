# OCRX 2.0 架构设计文档

## 1. 架构概述

### 1.1 设计目标

- **模块化**：各功能模块独立，便于维护和扩展
- **可测试性**：核心逻辑与界面分离，便于单元测试
- **可配置性**：支持用户自定义配置
- **可靠性**：关键操作带重试机制

### 1.2 架构模式

采用**分层架构** + **处理器模式**：

```
┌─────────────────────────────────────────┐
│              表示层 (GUI)                │
│  ┌─────────────┐  ┌─────────────────┐  │
│  │ MainWindow  │  │    Handlers     │  │
│  └─────────────┘  └─────────────────┘  │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│            业务逻辑层                   │
│  ┌─────────────────────────────────┐   │
│  │     ProcessingService           │   │
│  │  ┌──────────┐  ┌──────────┐    │   │
│  │  │_prepare_ │  │_recognize│    │   │
│  │  │_images() │  │_pages()  │    │   │
│  │  └──────────┘  └──────────┘    │   │
│  └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│            数据访问层                   │
│  ┌──────────┐ ┌──────────┐ ┌────────┐ │
│  │PDF       │ │Image     │ │OCR     │ │
│  │Processor │ │Processor │ │Engine  │ │
│  └──────────┘ └──────────┘ └────────┘ │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│            基础设施层                   │
│  ┌────────┐ ┌────────┐ ┌────────────┐ │
│  │Config  │ │Logger  │ │Clipboard   │ │
│  └────────┘ └────────┘ └────────────┘ │
└─────────────────────────────────────────┘
```

## 2. 核心组件

### 2.1 ProcessingService（处理服务）

**职责**：协调整个处理流程

**核心方法**：
- `_prepare_images()`：准备图片（PDF/图片转换）
- `_recognize_pages()`：OCR 识别所有页面
- `_merge_results()`：合并结果（可选保存）
- `process_file()`：处理单个文件
- `process_files()`：批量处理文件
- `process_and_copy()`：识别并复制

**进度计算**：
```
0-20%  ：预处理（PDF/图片转换）
20-90% ：OCR 识别（按完成页数/总页数）
90-100%：合并结果和保存
```

### 2.2 OCREngine（OCR 引擎）

**职责**：调用 API 进行文字识别

**核心方法**：
- `process_single_image()`：识别单张图片（带重试）
- `process_images_batch()`：批量识别

**重试机制**：
- 最大重试：3 次
- 基础延迟：2 秒
- 最大延迟：30 秒
- API 超时：120 秒

### 2.3 Handlers（处理器）

**职责**：封装特定功能，与 GUI 解耦

**处理器列表**：
- `SaveHandler`：识别并保存
- `CopyHandler`：识别并复制
- `ClipboardHandler`：剪贴板历史
- `ResultHandler`：结果展示
- `PromptHandler`：提示词预设管理
- `ProgressHandler`：进度条显示

## 3. 数据流

### 3.1 识别并保存流程

```
用户点击"识别并保存"
    ↓
SaveHandler.process_files()
    ↓
ProcessingService.process_files()
    ↓
1. _prepare_images()      [0-20%]
   - PDF 转图片
   - 图片加载
    ↓
2. _recognize_pages()     [20-90%]
   - 并发 OCR 识别
   - 每页超时 180 秒
    ↓
3. _merge_results()       [90-100%]
   - 按文件分组
   - 合并结果
   - 保存到文件
    ↓
显示完成消息
```

### 3.2 识别并复制流程

```
用户点击"识别并复制"
    ↓
CopyHandler.process_files()
    ↓
ProcessingService.process_and_copy()
    ↓
1. _prepare_images()      [0-20%]
    ↓
2. _recognize_pages()     [20-90%]
    ↓
3. _merge_results()       [90-100%]
   - 合并结果
   - 不保存文件
    ↓
ClipboardHistory.copy_to_clipboard()
    ↓
显示完成消息
```

## 4. 并发设计

### 4.1 线程池

使用 `ThreadPoolExecutor` 进行并发处理：

```python
with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
    # 提交所有任务
    futures = {executor.submit(task, arg): i for i, arg in enumerate(args)}
    
    # 收集结果（带超时）
    for future in as_completed(futures):
        try:
            result = future.result(timeout=180)
        except TimeoutError:
            # 处理超时
```

### 4.2 线程安全

- **剪贴板操作**：串行执行（系统资源）
- **日志记录**：线程安全（使用队列）
- **GUI 更新**：通过 `root.after()` 在主线程执行

## 5. 错误处理

### 5.1 重试策略

**等差数列延迟**：
- 第 1 次重试：等待 1 秒
- 第 2 次重试：等待 2 秒
- 第 3 次重试：等待 3 秒

### 5.2 错误类型

| 错误类型 | 处理方式 | 重试 |
|---------|---------|------|
| API 调用失败 | 记录日志，重试 | 是 |
| 识别超时 | 标记为失败，继续 | 否 |
| 合并失败 | 重试 | 是 |
| 复制失败 | 提示用户 | 否 |

## 6. 配置管理

### 6.1 配置项

```python
DEFAULT_CONFIG = {
    "BASE_URL": "",
    "API_KEY": "",
    "MODEL_NAME": "gpt-4o",
    "OUTPUT_DIR": str(Path.home() / "Documents" / "OCRX_Output"),
    "PDF_SCALE_FACTOR": "3.0",
    "MAX_WORKERS": "10",
    "prompt_templates": {...}
}
```

### 6.2 配置文件位置

- **Windows**：`C:\Users\<用户名>\.ocrx_config.json`
- **日志文件**：`C:\Users\<用户名>\.ocrx_gui.log`

## 7. 扩展点

### 7.1 添加新处理器

```python
# handlers/new_handler.py
from .base_handler import BaseHandler

class NewHandler(BaseHandler):
    def process(self, ...):
        # 实现功能
        pass
```

### 7.2 自定义 OCR 引擎

```python
# ocr_engine.py
class CustomOCREngine(OCREngine):
    def process_single_image(self, ...):
        # 自定义识别逻辑
        pass
```

## 8. 性能优化

### 8.1 并发优化

- 使用线程池管理并发
- 设置合理的最大并发数（默认 10）
- 单页面超时控制（180 秒）

### 8.2 内存优化

- 图片处理后立即释放
- 使用生成器处理大文件
- 剪贴板内容限制显示长度

## 9. 安全考虑

### 9.1 API 密钥

- 存储在用户目录下的配置文件中
- 不输出到日志
- 支持环境变量覆盖

### 9.2 文件安全

- 输出目录自动创建
- 文件名安全检查
- 临时文件及时清理

## 10. 测试策略

### 10.1 单元测试

- 测试各个处理器
- 测试核心服务方法
- 测试工具函数

### 10.2 集成测试

- 测试完整处理流程
- 测试 GUI 交互
- 测试错误恢复

---

*文档版本：v2.0*  
*最后更新：2026-02-26*
