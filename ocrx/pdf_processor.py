# -*- coding: utf-8 -*-
"""
PDF处理模块
负责PDF文件的转换和处理
"""

from pathlib import Path
from typing import List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class PDFProcessor:
    """PDF处理器"""

    def __init__(self, scale_factor: float = 3.0):
        """
        初始化PDF处理器

        Args:
            scale_factor: PDF渲染缩放比例，越大越清晰但处理越慢
        """
        self.scale_factor = scale_factor
        self._fitz = None
        self._init_fitz()

    def _init_fitz(self):
        """延迟初始化 fitz 模块"""
        if self._fitz is None:
            try:
                import fitz
                self._fitz = fitz
            except ImportError:
                logger.error("无法导入 fitz 模块，请确保 PyMuPDF 已正确安装")
                raise

    def pdf_to_images(
        self,
        pdf_path: str,
        page_range: Optional[str] = None
    ) -> List[Tuple[int, bytes]]:
        """
        将PDF转换为图片

        Args:
            pdf_path: PDF文件路径
            page_range: 页码范围字符串，如 "1,3,5-10"，None表示全部

        Returns:
            [(页码, 图片数据), ...] 列表
        """
        self._init_fitz()
        fitz = self._fitz

        pdf_file = Path(pdf_path)
        if not pdf_file.exists():
            raise FileNotFoundError(f"PDF文件不存在: {pdf_path}")

        images = []

        try:
            doc = fitz.open(str(pdf_file))
            total_pages = len(doc)

            if total_pages == 0:
                logger.warning(f"PDF文件为空: {pdf_file.name}")
                return images

            # 解析页码范围
            pages_to_process = self._parse_page_range(page_range, total_pages)

            for page_num in pages_to_process:
                if page_num < 1 or page_num > total_pages:
                    logger.warning(f"页码 {page_num} 超出范围 (1-{total_pages})")
                    continue

                try:
                    page = doc[page_num - 1]  # fitz使用0-based索引
                    mat = fitz.Matrix(self.scale_factor, self.scale_factor)
                    pix = page.get_pixmap(matrix=mat)
                    img_data = pix.tobytes("png")
                    images.append((page_num, img_data))
                    logger.debug(f"PDF第 {page_num} 页转换完成")

                except Exception as e:
                    logger.error(f"PDF第 {page_num} 页转换失败: {e}")
                    continue

            doc.close()
            logger.info(f"PDF转换完成: {pdf_file.name}, 共 {len(images)} 页")

        except Exception as e:
            logger.error(f"PDF处理失败 {pdf_file.name}: {e}")
            raise

        return images

    def _parse_page_range(self, page_range: Optional[str], total_pages: int) -> List[int]:
        """
        解析页码范围字符串

        Args:
            page_range: 页码范围字符串，如 "1,3,5-10"
            total_pages: 总页数

        Returns:
            页码列表
        """
        if not page_range or page_range.strip() == "":
            return list(range(1, total_pages + 1))

        pages = set()
        parts = page_range.split(",")

        for part in parts:
            part = part.strip()
            if not part:
                continue

            if "-" in part:
                # 处理范围，如 "5-10"
                try:
                    start, end = part.split("-")
                    start = int(start.strip())
                    end = int(end.strip())
                    pages.update(range(start, end + 1))
                except ValueError:
                    logger.warning(f"无效的页码范围: {part}")
                    continue
            else:
                # 处理单页
                try:
                    page = int(part)
                    pages.add(page)
                except ValueError:
                    logger.warning(f"无效的页码: {part}")
                    continue

        return sorted(list(pages))

    def get_pdf_info(self, pdf_path: str) -> dict:
        """
        获取PDF文件信息

        Args:
            pdf_path: PDF文件路径

        Returns:
            PDF信息字典
        """
        self._init_fitz()
        fitz = self._fitz

        pdf_file = Path(pdf_path)
        if not pdf_file.exists():
            raise FileNotFoundError(f"PDF文件不存在: {pdf_path}")

        try:
            doc = fitz.open(str(pdf_file))
            info = {
                "page_count": len(doc),
                "metadata": doc.metadata,
                "file_size": pdf_file.stat().st_size,
            }
            doc.close()
            return info

        except Exception as e:
            logger.error(f"获取PDF信息失败 {pdf_file.name}: {e}")
            raise
