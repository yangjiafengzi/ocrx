# -- coding: utf-8 --
"""
OCR 客户端模块
提供 OCR API 调用功能，支持重试机制
"""

import time
from typing import Any, Callable, Optional
from openai import OpenAI

from .logger import StructuredLogger
from .retry_utils import OperationCancelledError


class OCRClient:
    """增强的 OCR 客户端，支持重试机制"""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        max_retries: int = 2,
        retry_delay: int = 1,
        logger: Optional[StructuredLogger] = None
    ):
        """
        初始化 OCR 客户端

        Args:
            api_key: API 密钥
            base_url: API 基础 URL
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）
            logger: 日志记录器
        """
        self.api_key = api_key
        self.base_url = base_url
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.logger = logger or StructuredLogger()

        # OpenAI 客户端延迟创建：允许应用在尚未配置 API Key 时正常启动
        self._client = None

    def _ensure_client(self) -> OpenAI:
        """按需创建 OpenAI 客户端。"""
        if self._client is None:
            if not self.api_key:
                raise ValueError("API Key 未配置，请先在设置中填写 API Key")
            self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        return self._client

    def chat_completions_create(
        self,
        model: str,
        messages: list,
        timeout: int = 300,
        cancel_check: Optional[Callable[[], bool]] = None
    ) -> Any:
        """
        带重试机制的 API 调用

        Args:
            model: 模型名称
            messages: 消息列表
            timeout: 超时时间（秒）
            cancel_check: 取消检查函数，返回 True 时立即抛出取消异常

        Returns:
            API 响应

        Raises:
            Exception: API 调用失败时抛出异常
        """
        if cancel_check and cancel_check():
            raise OperationCancelledError("任务已取消")

        last_exception = None
        current_delay = self.retry_delay
        client = self._ensure_client()

        for attempt in range(self.max_retries + 1):
            if cancel_check and cancel_check():
                raise OperationCancelledError("任务已取消")

            try:
                self.logger.debug(f"API 调用尝试 {attempt + 1}/{self.max_retries + 1}")

                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    timeout=timeout
                )

                self.logger.debug("API 调用成功")
                return response

            except Exception as e:
                last_exception = e
                self.logger.warning(f"API 调用失败 (尝试 {attempt + 1}): {str(e)}")

                if attempt < self.max_retries:
                    self.logger.info(f"等待 {current_delay} 秒后重试...")
                    time.sleep(current_delay)
                    current_delay *= 2  # 指数退避（仅本次调用内生效）
                else:
                    self.logger.error(f"API 调用最终失败：{str(e)}")
                    raise last_exception

        raise last_exception

    def update_config(self, api_key: str = None, base_url: str = None):
        """
        更新客户端配置

        Args:
            api_key: 新的 API 密钥
            base_url: 新的 API 基础 URL
        """
        if api_key is not None:
            self.api_key = api_key
        if base_url is not None:
            self.base_url = base_url
        # 配置变化后重建客户端
        self._client = None
