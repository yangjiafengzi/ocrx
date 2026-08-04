# -- coding: utf-8 --
"""
OCR 识别引擎
负责调用 API 进行文字识别
"""

import base64
import time
from typing import Callable, List, Optional, Tuple

from .ocr_client import OCRClient
from .logger import StructuredLogger
from .retry_utils import ContentRefusedError, OperationCancelledError, retry_operation


class OCREngine:
    """OCR 识别引擎"""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model_name: str,
        max_workers: int = 10,
        logger_inst: Optional[StructuredLogger] = None
    ):
        """
        初始化 OCR 引擎

        Args:
            api_key: API 密钥
            base_url: API 基础 URL
            model_name: 模型名称
            max_workers: 最大并发数
            logger_inst: 日志实例
        """
        self.api_key = api_key
        self.base_url = base_url
        self.model_name = model_name
        self.max_workers = max_workers
        self.logger_inst = logger_inst or StructuredLogger()

        # 创建 OCR 客户端
        self.client = OCRClient(
            api_key=api_key,
            base_url=base_url,
            logger=self.logger_inst
        )

    def image_to_base64(self, image_data: bytes) -> str:
        """
        将图片数据转换为 base64 编码

        Args:
            image_data: 图片字节数据

        Returns:
            base64 编码字符串
        """
        return base64.b64encode(image_data).decode('utf-8')

    def process_single_image(
        self,
        prompt: str,
        identifier: Tuple[str, int],
        image_data: bytes,
        max_retries: int = 3,
        example_images: Optional[List[Tuple[str, bytes]]] = None,
        cancel_check: Optional[Callable[[], bool]] = None,
        deadline_seconds: int = 120
    ) -> Tuple[Tuple[str, int], str]:
        """
        处理单张图片

        重试策略：网络错误由 OCRClient 内部退避重试，本方法只对“业务校验失败”
        （空内容、None、以“识别失败”开头）重试，避免嵌套放大请求量。

        Args:
            prompt: 提示词
            identifier: (文件名，页码) 元组
            image_data: 图片字节数据
            max_retries: 业务校验失败的最大重试次数
            example_images: 少样本示例列表 [(示例文本, 示例图片数据), ...]
            cancel_check: 取消检查函数，返回 True 时立即取消
            deadline_seconds: 单页总处理时限（含重试），超时立即放弃

        Returns:
            (identifier, 识别结果) 元组
        """
        if cancel_check and cancel_check():
            self.logger_inst.warning(f"页面 {identifier} 已取消", "OCR")
            return (identifier, "识别失败：任务已取消")

        deadline = time.monotonic() + deadline_seconds

        def _check_deadline():
            if time.monotonic() > deadline:
                raise TimeoutError("单页处理超时")

        def do_recognition():
            if cancel_check and cancel_check():
                raise OperationCancelledError("任务已取消")
            _check_deadline()

            image_base64 = self.image_to_base64(image_data)

            messages = [
                {"role": "system", "content": prompt},
            ]

            if example_images:
                for example_text, example_image_data in example_images:
                    example_base64 = self.image_to_base64(example_image_data)
                    messages.append({
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/png;base64,{example_base64}"}
                            },
                            {"type": "text", "text": "请识别这张图片中的内容"}
                        ]
                    })
                    messages.append({
                        "role": "assistant",
                        "content": example_text
                    })

            messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{image_base64}"}
                    },
                    {"type": "text", "text": "请识别这张图片中的内容"}
                ]
            })

            response = self.client.chat_completions_create(
                model=self.model_name,
                messages=messages,
                timeout=60,
                cancel_check=cancel_check
            )

            choice = response.choices[0]
            message = choice.message
            _finish = getattr(choice, "finish_reason", None)
            _refusal = getattr(message, "refusal", None)
            finish_reason = _finish.lower() if isinstance(_finish, str) else ""
            refusal = _refusal if isinstance(_refusal, str) else ""
            result = message.content
            content_text = str(result or "").lower()

            # 安全策略拒绝：重试没有意义，直接标记失败
            refusal_phrases = (
                "拒绝回答", "无法回答", "不能回答", "不能提供", "不便回答",
                "i'm sorry", "cannot assist", "can't assist",
                "content policy", "内容政策",
            )
            if (
                "filter" in finish_reason
                or refusal
                or any(phrase in content_text for phrase in refusal_phrases)
            ):
                raise ContentRefusedError("模型返回被安全策略拒绝")

            # 验证结果有效性，无效时抛出异常触发重试
            if result is None:
                raise ValueError("API返回None")

            result_str = str(result).strip()
            if len(result_str) == 0:
                raise ValueError("API返回空内容")

            if result_str.startswith("识别失败"):
                raise ValueError(f"API返回失败内容：{result_str[:100]}")

            return result

        def on_retry(attempt, delay, exception):
            self.logger_inst.warning(
                f"页面 {identifier} 识别失败，第 {attempt} 次重试，等待 {delay:.1f} 秒...",
                "OCR"
            )
            _check_deadline()

        try:
            result = retry_operation(
                do_recognition,
                max_retries=max_retries,
                base_delay=1.0,  # 基础延迟1秒
                max_delay=10.0,  # 最大延迟10秒
                exceptions=(ValueError,),  # 只重试业务校验失败，网络错误由客户端负责
                on_retry=on_retry,
                cancel_check=cancel_check
            )

            self.logger_inst.debug(f"页面 {identifier} 识别成功", "OCR")
            return (identifier, result)

        except OperationCancelledError as e:
            self.logger_inst.warning(f"页面 {identifier} 任务已取消", "OCR")
            return (identifier, f"识别失败：{str(e)}")

        except ContentRefusedError as e:
            self.logger_inst.warning(
                f"页面 {identifier} 内容被安全策略拒绝", "OCR"
            )
            return (
                identifier,
                "识别失败：内容被模型安全策略拒绝（可能包含敏感内容），请更换图片或调整提示词",
            )

        except TimeoutError as e:
            self.logger_inst.warning(f"页面 {identifier} {str(e)}", "OCR")
            return (identifier, "识别失败：单页处理超时，请检查网络或模型状态")

        except Exception as e:
            error_msg = f"识别失败（已重试{max_retries}次）：{str(e)}"
            self.logger_inst.error(f"页面 {identifier} 识别异常：{error_msg}", "OCR")
            return (identifier, error_msg)

    def update_config(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
        max_workers: Optional[int] = None
    ):
        """
        更新配置

        Args:
            api_key: API 密钥
            base_url: API 基础 URL
            model_name: 模型名称
            max_workers: 最大并发数
        """
        if api_key is not None:
            self.api_key = api_key
            self.client.update_config(api_key=api_key)

        if base_url is not None:
            self.base_url = base_url
            self.client.update_config(base_url=base_url)

        if model_name is not None:
            self.model_name = model_name

        if max_workers is not None:
            self.max_workers = max_workers
