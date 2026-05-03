# -- coding: utf-8 --
"""
示例库管理模块
用于存储和管理少样本提示的示例（图片+文本）
"""

import json
import hashlib
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class Example:
    """示例数据类"""
    id: str                          # 示例唯一ID
    image_path: str                  # 示例图片路径
    text: str                        # 示例对应的正确文本
    description: str = ""            # 可选的描述/标签
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Example':
        """从字典创建"""
        return cls(**data)


class ExampleLibrary:
    """示例库管理类"""
    
    def __init__(self, library_path: str = None):
        """
        初始化示例库
        
        Args:
            library_path: 示例库存储路径，默认在用户目录下
        """
        if library_path is None:
            # 默认存储在用户目录下
            self.library_path = Path.home() / ".ocrx" / "example_library"
        else:
            self.library_path = Path(library_path)
            
        self.library_path.mkdir(parents=True, exist_ok=True)
        
        # 数据文件路径
        self.data_file = self.library_path / "examples.json"
        
        # 图片存储目录
        self.images_dir = self.library_path / "images"
        self.images_dir.mkdir(exist_ok=True)
        
        # 加载示例列表
        self.examples: List[Example] = []
        self._load_examples()
        
        logger.info(f"示例库初始化完成，路径：{self.library_path}")
    
    def _load_examples(self):
        """从文件加载示例列表"""
        if not self.data_file.exists():
            self.examples = []
            return
            
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.examples = [Example.from_dict(item) for item in data]
            logger.info(f"加载了 {len(self.examples)} 个示例")
        except Exception as e:
            logger.error(f"加载示例失败：{e}")
            self.examples = []
    
    def _save_examples(self):
        """保存示例列表到文件"""
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                data = [ex.to_dict() for ex in self.examples]
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.debug("示例列表已保存")
        except Exception as e:
            logger.error(f"保存示例失败：{e}")
    
    def _generate_id(self, image_path: str) -> str:
        """生成示例ID"""
        # 使用图片内容哈希作为ID的一部分
        try:
            with open(image_path, 'rb') as f:
                content = f.read()
                hash_obj = hashlib.md5(content)
                return hash_obj.hexdigest()[:16]
        except:
            # 如果失败，使用时间戳+随机数
            import time
            return f"ex_{int(time.time() * 1000)}"
    
    def add_example(self, image_path: str, text: str, description: str = "") -> Optional[Example]:
        """
        添加新示例
        
        Args:
            image_path: 示例图片路径
            text: 示例对应的正确文本
            description: 可选的描述
            
        Returns:
            添加的示例对象，失败返回None
        """
        try:
            # 复制图片到库目录
            src_path = Path(image_path)
            if not src_path.exists():
                logger.error(f"图片不存在：{image_path}")
                return None
                
            # 生成ID
            ex_id = self._generate_id(image_path)
            
            # 复制图片到库目录
            dst_filename = f"{ex_id}.png"
            dst_path = self.images_dir / dst_filename
            
            # 使用PIL转换并保存为PNG
            from PIL import Image
            with Image.open(src_path) as img:
                # 转换为RGB（如果是RGBA）
                if img.mode in ('RGBA', 'P'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                img.save(dst_path, 'PNG', optimize=True)
            
            # 创建示例对象
            example = Example(
                id=ex_id,
                image_path=str(dst_path),
                text=text,
                description=description
            )
            
            # 添加到列表
            self.examples.append(example)
            self._save_examples()
            
            logger.info(f"添加示例成功：{ex_id}")
            return example
            
        except Exception as e:
            logger.error(f"添加示例失败：{e}")
            return None
    
    def remove_example(self, ex_id: str) -> bool:
        """
        删除示例
        
        Args:
            ex_id: 示例ID
            
        Returns:
            是否删除成功
        """
        try:
            # 查找示例
            example = next((ex for ex in self.examples if ex.id == ex_id), None)
            if not example:
                logger.warning(f"示例不存在：{ex_id}")
                return False
            
            # 删除图片文件
            try:
                img_path = Path(example.image_path)
                if img_path.exists():
                    img_path.unlink()
            except Exception as e:
                logger.warning(f"删除图片文件失败：{e}")
            
            # 从列表移除
            self.examples.remove(example)
            self._save_examples()
            
            logger.info(f"删除示例成功：{ex_id}")
            return True
            
        except Exception as e:
            logger.error(f"删除示例失败：{e}")
            return False
    
    def get_example(self, ex_id: str) -> Optional[Example]:
        """获取单个示例"""
        return next((ex for ex in self.examples if ex.id == ex_id), None)
    
    def get_all_examples(self) -> List[Example]:
        """获取所有示例"""
        return self.examples.copy()
    
    def get_examples_by_description(self, keyword: str) -> List[Example]:
        """根据描述关键词搜索示例"""
        keyword = keyword.lower()
        return [ex for ex in self.examples if keyword in ex.description.lower()]
    
    def clear_all(self) -> bool:
        """
        清空所有示例
        
        Returns:
            是否清空成功
        """
        try:
            # 删除所有图片文件
            for example in self.examples:
                try:
                    img_path = Path(example.image_path)
                    if img_path.exists():
                        img_path.unlink()
                except:
                    pass
            
            # 清空列表
            self.examples = []
            self._save_examples()
            
            logger.info("清空所有示例")
            return True
            
        except Exception as e:
            logger.error(f"清空示例失败：{e}")
            return False
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            "total_examples": len(self.examples),
            "library_path": str(self.library_path),
            "images_dir": str(self.images_dir),
            "data_file": str(self.data_file)
        }