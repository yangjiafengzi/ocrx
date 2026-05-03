# -- coding: utf-8 --
"""
OCR 客户端模块
提供 OCR API 调用功能，支持重试机制
"""

import time
from typing import Optional, Any
from openai import OpenAI

from .logger import StructuredLogger


class OCRClient:
    """增强的 OCR 客户端，支持重试机制"""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        max_retries: int = 3,
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
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.logger = logger or StructuredLogger()

    def chat_completions_create(
        self,
        model: str,
        messages: list,
        timeout: int = 300
    ) -> Any:
        """
        带重试机制的 API 调用

        Args:
            model: 模型名称
            messages: 消息列表
            timeout: 超时时间（秒）

        Returns:
            API 响应

        Raises:
            Exception: API 调用失败时抛出异常
        """
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                self.logger.debug(f"API 调用尝试 {attempt + 1}/{self.max_retries + 1}")
                
                response = self.client.chat.completions.create(
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
                    self.logger.info(f"等待 {self.retry_delay} 秒后重试...")
                    time.sleep(self.retry_delay)
                    self.retry_delay *= 2  # 指数退避
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
        if api_key:
            self.client.api_key = api_key
        if base_url:
            self.client.base_url = base_url
