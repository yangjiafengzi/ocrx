# OCRX 2.0 开发文档

## 开发环境设置

### 1. 环境要求

- Python 3.8+
- Windows 10/11
- Git

### 2. 安装开发依赖

```bash
# 克隆项目
git clone <repository-url>
cd ocrx2.0

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 安装开发依赖
pip install pytest black flake8 mypy
```

### 3. 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_ocr_engine.py

# 带覆盖率报告
pytest --cov=ocrx tests/
```

## 代码规范

### 1. 代码风格

- 使用 **Black** 格式化代码
- 使用 **Flake8** 检查代码质量
- 使用 **MyPy** 进行类型检查

```bash
# 格式化代码
black ocrx/

# 检查代码
flake8 ocrx/

# 类型检查
mypy ocrx/
```

### 2. 文档字符串规范

使用 Google 风格的文档字符串：

```python
def process_file(
    self,
    file_path: str,
    prompt: str,
    page_range_str: Optional[str] = None
) -> Tuple[bool, Optional[str], str]:
    """
    处理单个文件

    Args:
        file_path: 文件路径
        prompt: 提示词
        page_range_str: 页码范围

    Returns:
        (是否成功，输出文件路径，源文件名)

    Raises:
        FileNotFoundError: 文件不存在
        ValueError: 参数错误
    """
```

### 3. 类型注解

所有函数参数和返回值都应添加类型注解：

```python
from typing import List, Dict, Tuple, Optional

def merge_contents(
    results: List[Tuple[Tuple[str, int], str]]
) -> str:
    ...
```

## 模块开发指南

### 1. 添加新处理器

#### 步骤 1：创建处理器文件

```python
# ocrx/gui/handlers/my_handler.py
from .base_handler import BaseHandler

class MyHandler(BaseHandler):
    """我的处理器"""

    def __init__(self, main_window):
        super().__init__(main_window)
        # 初始化代码

    def process(self, data: str) -> bool:
        """
        处理数据

        Args:
            data: 输入数据

        Returns:
            是否成功
        """
        try:
            # 处理逻辑
            self._update_status("处理中...")
            
            # 调用服务
            result = self.processing_service.do_something(data)
            
            # 显示结果
            self._display_result(result)
            
            return True
        except Exception as e:
            self.logger.error(f"处理失败：{e}")
            return False
```

#### 步骤 2：导出处理器

```python
# ocrx/gui/handlers/__init__.py
from .my_handler import MyHandler

__all__ = [
    # ... 其他处理器
    "MyHandler",
]
```

#### 步骤 3：在主窗口中使用

```python
# ocrx/gui/main_window.py
from .handlers import MyHandler

class MainWindow:
    def _init_handlers(self):
        # ... 其他处理器
        self.my_handler = MyHandler(self)

    def create_widgets(self):
        # 创建按钮
        ttk.Button(
            button_frame,
            text="我的功能",
            command=self.my_handler.process
        ).pack(side=tk.LEFT, padx=5)
```

### 2. 修改 OCR 引擎

#### 添加自定义识别逻辑

```python
# ocrx/ocr_engine.py

class OCREngine:
    def process_single_image(
        self,
        prompt: str,
        identifier: Tuple[str, int],
        image_data: bytes,
        max_retries: int = 3
    ) -> Tuple[Tuple[str, int], str]:
        """
        处理单张图片
        """
        # 自定义预处理
        processed_image = self._preprocess(image_data)
        
        # 调用 API
        result = self._call_api(prompt, processed_image)
        
        # 自定义后处理
        cleaned_result = self._postprocess(result)
        
        return (identifier, cleaned_result)

    def _preprocess(self, image_data: bytes) -> bytes:
        """图像预处理"""
        # 实现预处理逻辑
        pass

    def _postprocess(self, result: str) -> str:
        """结果后处理"""
        # 实现后处理逻辑
        pass
```

### 3. 添加重试机制

#### 使用 retry_utils

```python
from ocrx.retry_utils import retry_operation, retry_with_backoff

# 方式 1：使用装饰器
@retry_with_backoff(max_retries=3, base_delay=1.0)
def my_function():
    # 可能失败的代码
    pass

# 方式 2：使用函数
result = retry_operation(
    operation=my_function,
    max_retries=3,
    base_delay=1.0,
    max_delay=30.0,
    on_retry=lambda attempt, delay, e: print(f"重试 {attempt}")
)
```

### 4. 添加日志记录

```python
from ocrx.logger import StructuredLogger

class MyClass:
    def __init__(self):
        self.logger = StructuredLogger()

    def do_something(self):
        # 不同级别的日志
        self.logger.debug("调试信息", "Component")
        self.logger.info("普通信息", "Component")
        self.logger.warning("警告信息", "Component")
        self.logger.error("错误信息", "Component")
```

## 测试指南

### 1. 单元测试

```python
# tests/test_ocr_engine.py
import pytest
from ocrx.ocr_engine import OCREngine

class TestOCREngine:
    def setup_method(self):
        self.engine = OCREngine(
            api_key="test-key",
            base_url="https://test.com",
            model_name="test-model"
        )

    def test_process_single_image_success(self):
        # 测试成功场景
        result = self.engine.process_single_image(
            prompt="test",
            identifier=("file", 1),
            image_data=b"test-data"
        )
        assert result[0] == ("file", 1)
        assert isinstance(result[1], str)

    def test_process_single_image_failure(self):
        # 测试失败场景
        with pytest.raises(Exception):
            self.engine.process_single_image(
                prompt="",
                identifier=("file", 1),
                image_data=b""
            )
```

### 2. 集成测试

```python
# tests/test_processing_service.py
import pytest
from ocrx.processing_service import ProcessingService

class TestProcessingService:
    def test_process_file(self, tmp_path):
        service = ProcessingService(
            api_key="test-key",
            base_url="https://test.com",
            model_name="test-model",
            output_dir=str(tmp_path)
        )
        
        success, output_path, file_stem = service.process_file(
            file_path="test.pdf",
            prompt="test prompt"
        )
        
        assert isinstance(success, bool)
```

### 3. GUI 测试

```python
# tests/test_gui.py
import tkinter as tk
from ocrx.gui.main_window import MainWindow

class TestMainWindow:
    def setup_method(self):
        self.root = tk.Tk()
        self.main_window = MainWindow(self.root)

    def teardown_method(self):
        self.root.destroy()

    def test_window_title(self):
        assert self.root.title() == "OCRX-智能文字识别"
```

## 调试技巧

### 1. 日志调试

```python
# 设置日志级别
import logging
logging.basicConfig(level=logging.DEBUG)

# 在关键位置添加日志
logger.debug(f"变量值: {variable}")
```

### 2. 断点调试

使用 IDE 的调试功能：
1. 在代码中设置断点
2. 启动调试模式
3. 逐步执行，检查变量

### 3. 性能分析

```python
import cProfile
import pstats

# 性能分析
profiler = cProfile.Profile()
profiler.enable()

# 要分析的代码
process_files()

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(20)  # 打印前 20 个
```

## 发布流程

### 1. 版本号管理

使用语义化版本号：`主版本.次版本.修订号`

- 主版本：重大更新，不兼容
- 次版本：新功能，兼容
- 修订号：Bug 修复

### 2. 发布前检查

```bash
# 1. 运行测试
pytest

# 2. 检查代码风格
black --check ocrx/
flake8 ocrx/

# 3. 类型检查
mypy ocrx/

# 4. 更新版本号
# 修改 __init__.py 中的 __version__

# 5. 更新文档
# 更新 README.md、CHANGELOG.md
```

### 3. 打包发布

```bash
# 安装打包工具
pip install setuptools wheel

# 打包
python setup.py sdist bdist_wheel

# 上传到 PyPI（如果需要）
pip install twine
twine upload dist/*
```

## 贡献指南

### 1. 提交 Issue

- 描述问题
- 提供复现步骤
- 提供环境信息
- 提供错误日志

### 2. 提交 PR

1. Fork 项目
2. 创建分支：`git checkout -b feature/my-feature`
3. 提交更改：`git commit -m "Add feature"`
4. 推送分支：`git push origin feature/my-feature`
5. 创建 Pull Request

### 3. 代码审查

- 所有 PR 需要经过审查
- 确保测试通过
- 确保代码风格正确
- 确保文档更新

## API 参考

### ProcessingService

```python
class ProcessingService:
    def process_file(file_path, prompt, page_range_str) -> Tuple[bool, Optional[str], str]
    def process_files(file_paths, prompt, page_range_str) -> Dict[str, Tuple[bool, Optional[str]]]
    def process_and_copy(file_paths, prompt, page_range_str) -> Tuple[bool, str]
```

### OCREngine

```python
class OCREngine:
    def process_single_image(prompt, identifier, image_data, max_retries=3) -> Tuple[Tuple[str, int], str]
    def process_images_batch(prompt, images, file_stem, progress_callback) -> List[Tuple[Tuple[str, int], str]]
```

### BaseHandler

```python
class BaseHandler:
    def _update_status(status: str)
    def _update_progress(current: int, total: int, phase: str)
    def _display_result(content: str)
    def show_message(title: str, message: str, msg_type: str)
```

---

*文档版本：v2.0*  
*最后更新：2026-02-26*
