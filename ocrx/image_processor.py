# -- coding: utf-8 --
"""
图片处理模块
负责读取和处理图片文件
"""

import io
import logging
from pathlib import Path
from typing import List, Optional, Tuple

from PIL import Image

logger = logging.getLogger(__name__)


class ImageProcessor:
    """图片处理器"""

    # 支持的主流图片格式
    SUPPORTED_FORMATS = [
        '.jpg', '.jpeg',   # JPEG
        '.png',           # PNG
        '.bmp',           # Bitmap
        '.gif',           # GIF
        '.tiff', '.tif',   # TIFF
        '.webp',          # WebP
        '.heic', '.heif',  # HEIC/HEIF (iPhone 照片)
        '.raw', '.cr2', '.nef', '.arw', '.dng'  # 相机 RAW 格式
    ]

    # 可以转换为 PNG 的格式（需要 Pillow 处理）
    CONVERTIBLE_FORMATS = [
        '.gif', '.tiff', '.tif', '.webp',
        '.heic', '.heif', '.raw', '.cr2',
        '.nef', '.arw', '.dng', '.bmp'
    ]

    # 发送给识别 API 的最大边长；过大只会增加 token/费用，对精度帮助有限
    DEFAULT_MAX_DIMENSION = 2048

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

    @staticmethod
    def _to_rgb(img: Image.Image) -> Image.Image:
        """统一转为 RGB，透明通道用白色背景合成。"""
        if img.mode in ('RGBA', 'LA', 'PA'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[-1])
            return background
        if img.mode == 'P':
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img)
            return background
        if img.mode != 'RGB':
            return img.convert('RGB')
        return img

    @staticmethod
    def _downscale(img: Image.Image, max_dimension: int) -> Image.Image:
        """按比例缩小到最大边长以内。"""
        if max_dimension and max(img.size) > max_dimension:
            ratio = max_dimension / max(img.size)
            new_size = (
                max(1, int(img.width * ratio)),
                max(1, int(img.height * ratio)),
            )
            return img.resize(new_size, Image.LANCZOS)
        return img

    def image_file_to_bytes(
        self,
        image_path: str,
        convert_to_png: bool = True,
        max_dimension: int = DEFAULT_MAX_DIMENSION
    ) -> Optional[bytes]:
        """
        读取图片文件为统一的 PNG 字节数据。

        统一转换为 PNG 并压缩到 max_dimension 以内，保证发送给 API 时
        MIME 类型始终正确；无法解码的格式（如缺少插件的 HEIC/RAW）返回 None，
        不再把原始字节当图片发送。

        Args:
            image_path: 图片文件路径
            convert_to_png: 是否统一转换为 PNG（为 False 时原样返回字节）
            max_dimension: 最大边长，超过则等比缩小

        Returns:
            图片字节数据，失败返回 None
        """
        image_path = Path(image_path)

        if not image_path.exists():
            logger.warning(f"图片文件不存在：{image_path}")
            return None

        if not convert_to_png:
            # 兼容旧行为：原样读取字节
            try:
                with open(image_path, 'rb') as f:
                    data = f.read()
                return data or None
            except Exception as e:
                logger.error(f"读取图片文件失败：{e}")
                return None

        try:
            with Image.open(image_path) as img:
                img.load()
                img = self._to_rgb(img)
                img = self._downscale(img, max_dimension)

                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format='PNG', optimize=True)
                data = img_byte_arr.getvalue()

                if not data:
                    logger.warning(f"图片文件为空：{image_path.name}")
                    return None

                logger.debug(
                    f"图片转换完成：{image_path.name}, "
                    f"原大小：{image_path.stat().st_size} bytes, "
                    f"转换后：{len(data)} bytes, 尺寸：{img.size}"
                )
                return data
        except Exception as e:
            logger.error(f"图片读取或转换失败：{e}")
            return None

    def validate_image(self, image_path: str) -> Tuple[bool, str]:
        """
        验证图片文件是否有效

        Args:
            image_path: 图片文件路径

        Returns:
            (是否有效, 错误信息)
        """
        image_path = Path(image_path)

        if not image_path.exists():
            return False, "文件不存在"

        if not self.is_supported_image(image_path):
            return False, f"不支持的图片格式：{image_path.suffix}"

        try:
            with Image.open(image_path) as img:
                img.verify()  # 验证图片完整性
                return True, "图片有效"
        except Exception as e:
            return False, f"图片损坏：{str(e)}"

    def get_supported_formats(self) -> List[str]:
        """获取支持的图片格式列表"""
        return [fmt.upper()[1:] for fmt in self.SUPPORTED_FORMATS]

    def get_supported_formats_description(self) -> str:
        """获取支持格式的描述文本"""
        formats = sorted(list(set([fmt.lower() for fmt in self.SUPPORTED_FORMATS])))
        return "支持的图片格式：" + ", ".join(formats)

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
