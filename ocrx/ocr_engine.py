# -- coding: utf-8 --
"""
OCR 识别引擎
负责调用 API 进行文字识别
"""

import base64
from typing import Tuple, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
from pathlib import Path

from .ocr_client import OCRClient
from .logger import StructuredLogger

logger = logging.getLogger(__name__)


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
        max_retries: int = 5,
        example_images: List[Tuple[str, bytes]] = None
    ) -> Tuple[Tuple[str, int], str]:
        """
        处理单张图片（带重试机制，支持少样本提示）

        Args:
            prompt: 提示词
            identifier: (文件名，页码) 元组
            image_data: 图片字节数据
            max_retries: 最大重试次数
            example_images: 少样本示例列表 [(示例文本, 示例图片数据), ...]

        Returns:
            (identifier, 识别结果) 元组
        """
        from .retry_utils import retry_operation
        
        def do_recognition():
            # 构建消息内容
            content = []
            
            # 如果有示例，先添加示例图片和文本
            if example_images:
                for i, (example_text, example_image_data) in enumerate(example_images):
                    example_base64 = self.image_to_base64(example_image_data)
                    
                    # 添加示例图片
                    content.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{example_base64}"
                        }
                    })
                    
                    # 添加示例文本说明
                    content.append({
                        "type": "text", 
                        "text": f"示例{i+1}：这是一张示例图片，它的正确识别结果是：{example_text}"
                    })
            
            # 添加目标图片
            image_base64 = self.image_to_base64(image_data)
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{image_base64}"
                }
            })
            
            # 添加提示词
            content.append({"type": "text", "text": prompt})
            
            response = self.client.chat_completions_create(
                model=self.model_name,
                messages=[
                    {
                        "role": "user",
                        "content": content
                    }
                ],
                timeout=120  # 超时时间120秒（2分钟），适合复杂图形识别
            )
            
            result = response.choices[0].message.content
            
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
        
        try:
            result = retry_operation(
                do_recognition,
                max_retries=max_retries,
                base_delay=2.0,  # 基础延迟2秒
                max_delay=30.0,  # 最大延迟30秒
                exceptions=(Exception,),
                on_retry=on_retry
            )
            
            self.logger_inst.debug(f"页面 {identifier} 识别成功", "OCR")
            return (identifier, result)

        except Exception as e:
            error_msg = f"识别失败（已重试{max_retries}次）：{str(e)}"
            self.logger_inst.error(f"页面 {identifier} 识别异常：{error_msg}", "OCR")
            return (identifier, error_msg)

    def process_images_batch(
        self,
        prompt: str,
        images: List[Tuple[int, bytes]],
        file_stem: str = "unknown",
        progress_callback = None
    ) -> List[Tuple[Tuple[str, int], str]]:
        """
        批量处理图片

        Args:
            prompt: 提示词
            images: [(页码，图片数据), ...] 列表
            file_stem: 文件名（不含扩展名）
            progress_callback: 进度回调函数，参数为 (completed, total)

        Returns:
            [((文件名，页码), 识别结果), ...] 列表
        """
        results = []
        total_pages = len(images)

        self.logger_inst.info(f"开始识别 {total_pages} 页", "OCR")

        # 使用线程池并发处理
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {}
            
            # 提交所有任务
            for page_num, img_data in images:
                identifier = (file_stem, page_num)
                future = executor.submit(
                    self.process_single_image,
                    prompt,
                    identifier,
                    img_data
                )
                futures[future] = page_num

            # 收集结果
            completed = 0
            for future in as_completed(futures):
                page_num = futures[future]
                try:
                    result = future.result()
                    results.append(result)
                    completed += 1
                    
                    # 调用进度回调
                    if progress_callback:
                        progress_callback(completed, total_pages)
                    
                    if completed % 5 == 0 or completed == total_pages:
                        self.logger_inst.info(
                            f"进度：{completed}/{total_pages} 页",
                            "OCR"
                        )
                        
                except Exception as e:
                    self.logger_inst.error(
                        f"第 {page_num} 页处理异常：{e}",
                        "OCR"
                    )
                    results.append(((file_stem, page_num), f"识别失败：{str(e)}"))

        self.logger_inst.info(f"完成 {len(results)} 页识别", "OCR")
        return results

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
        if api_key:
            self.api_key = api_key
            self.client.update_config(api_key=api_key)
        
        if base_url:
            self.base_url = base_url
            self.client.update_config(base_url=base_url)
        
        if model_name:
            self.model_name = model_name
        
        if max_workers:
            self.max_workers = max_workers
