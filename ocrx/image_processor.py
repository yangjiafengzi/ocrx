# -- coding: utf-8 --
"""
图片处理模块
负责读取和处理图片文件
"""

from pathlib import Path
from typing import List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class ImageProcessor:
    """图片处理器"""

    SUPPORTED_FORMATS = ['.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff']

    def __init__(self):
        """初始化图片处理器"""
        pass

    def is_supported_image(self, file_path: str) -> bool:
        """
        检查文件是否为支持的图片格式

        Args:
            file_path: 文件路径

        Returns:
            是否为支持的图片格式
        """
        suffix = Path(file_path).suffix.lower()
        return suffix in self.SUPPORTED_FORMATS

    def image_file_to_bytes(self, image_path: str) -> Optional[bytes]:
        """
        读取图片文件为字节数据

        Args:
            image_path: 图片文件路径

        Returns:
            图片字节数据，失败返回 None
        """
        image_path = Path(image_path)
        
        if not image_path.exists():
            logger.warning(f"图片文件不存在：{image_path}")
            return None

        try:
            with open(image_path, 'rb') as f:
                img_data = f.read()
            
            logger.debug(f"已读取图片文件：{image_path.name}, 大小：{len(img_data)} bytes")
            return img_data

        except Exception as e:
            logger.error(f"读取图片文件失败：{e}")
            return None

    def load_image(self, image_path: str) -> Optional[Tuple[int, bytes]]:
        """
        加载单个图片文件

        Args:
            image_path: 图片文件路径

        Returns:
            [(1, 图片数据)] 或 None
        """
        img_data = self.image_file_to_bytes(image_path)
        if img_data:
            return [(1, img_data)]
        return None

    def load_images(self, image_paths: List[str]) -> List[Tuple[str, int, bytes]]:
        """
        批量加载图片文件

        Args:
            image_paths: 图片文件路径列表

        Returns:
            [(文件名，页码，图片数据), ...] 列表
        """
        images = []

        for image_path in image_paths:
            img_data = self.image_file_to_bytes(image_path)
            if img_data:
                file_name = Path(image_path).stem
                images.append((file_name, 1, img_data))
                logger.info(f"已加载图片：{image_path}")
            else:
                logger.warning(f"跳过无效图片：{image_path}")

        return images
