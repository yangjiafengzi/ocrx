# -- coding: utf-8 --
"""
图片处理模块
负责读取和处理图片文件
"""

from pathlib import Path
from typing import List, Tuple, Optional
import logging
from PIL import Image
import io

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

    def image_file_to_bytes(self, image_path: str, convert_to_png: bool = True) -> Optional[bytes]:
        """
        读取图片文件为字节数据，自动转换不兼容格式为PNG

        Args:
            image_path: 图片文件路径
            convert_to_png: 是否转换不兼容格式为PNG

        Returns:
            图片字节数据，失败返回 None
        """
        image_path = Path(image_path)
        
        if not image_path.exists():
            logger.warning(f"图片文件不存在：{image_path}")
            return None

        suffix = image_path.suffix.lower()
        
        # JPEG和PNG直接读取
        if suffix in ['.jpg', '.jpeg', '.png']:
            try:
                # 先验证图片有效性
                with Image.open(image_path) as img:
                    img.verify()
                    
                # 读取字节
                with open(image_path, 'rb') as f:
                    img_data = f.read()
                
                if len(img_data) == 0:
                    logger.warning(f"图片文件为空：{image_path.name}")
                    return None
                    
                logger.debug(f"已读取图片文件：{image_path.name}, 大小：{len(img_data)} bytes")
                return img_data
            except Exception as e:
                logger.error(f"读取或验证图片失败：{e}")
                return None
        
        # 其他格式需要转换为PNG
        if convert_to_png and suffix in self.CONVERTIBLE_FORMATS:
            try:
                logger.debug(f"转换图片格式 {suffix} 为PNG：{image_path.name}")
                
                # 打开图片并转换为RGB
                with Image.open(image_path) as img:
                    # 如果是RGBA模式，转换为RGB（避免PNG透明通道问题）
                    if img.mode in ('RGBA', 'P'):
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                        img = background
                    elif img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    # 转换为PNG字节
                    img_byte_arr = io.BytesIO()
                    img.save(img_byte_arr, format='PNG', optimize=True)
                    img_byte_arr = img_byte_arr.getvalue()
                    
                    logger.debug(f"图片转换完成，原大小：{image_path.stat().st_size} bytes, 转换后：{len(img_byte_arr)} bytes")
                    return img_byte_arr
                    
            except Exception as e:
                logger.error(f"转换图片格式失败：{e}")
                # 尝试直接读取
                try:
                    with open(image_path, 'rb') as f:
                        return f.read()
                except:
                    return None
        
        # 不支持的格式，尝试直接读取
        try:
            with open(image_path, 'rb') as f:
                img_data = f.read()
            logger.debug(f"尝试直接读取图片文件：{image_path.name}, 大小：{len(img_data)} bytes")
            return img_data
        except Exception as e:
            logger.error(f"读取图片文件失败：{e}")
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
