# -- coding: utf-8 --
"""
PDF 处理模块
负责将 PDF 文件转换为图片
"""

import fitz  # PyMuPDF
from pathlib import Path
from typing import List, Tuple
import logging

logger = logging.getLogger(__name__)


class PDFProcessor:
    """PDF 处理器"""

    def __init__(self, scale_factor: float = 3.0):
        """
        初始化 PDF 处理器

        Args:
            scale_factor: PDF 渲染缩放比例，默认 3.0
        """
        self.scale_factor = scale_factor

    def parse_page_range(self, page_range_str: str, total_pages: int) -> List[int]:
        """
        解析页码范围字符串

        Args:
            page_range_str: 页码范围字符串，如 "1,3,5-10"
            total_pages: 总页数

        Returns:
            需要处理的页码列表（从 1 开始）
        """
        if not page_range_str or page_range_str.strip() == "":
            return list(range(1, total_pages + 1))

        pages_to_process = []
        parts = page_range_str.split(',')

        for part in parts:
            part = part.strip()
            if not part:
                continue

            if '-' in part:
                # 范围，如 "5-10"
                try:
                    start, end = part.split('-', 1)
                    start = int(start.strip())
                    end = int(end.strip())
                    # 确保范围在有效范围内
                    start = max(1, min(start, total_pages))
                    end = max(1, min(end, total_pages))
                    if start <= end:
                        pages_to_process.extend(range(start, end + 1))
                except ValueError:
                    logger.warning(f"无效的页码范围：{part}")
            else:
                # 单个页码
                try:
                    page_num = int(part)
                    if 1 <= page_num <= total_pages:
                        pages_to_process.append(page_num)
                except ValueError:
                    logger.warning(f"无效的页码：{part}")

        # 去重并排序
        pages_to_process = sorted(list(set(pages_to_process)))

        if not pages_to_process:
            return list(range(1, total_pages + 1))

        return pages_to_process

    def pdf_to_images(self, pdf_path: str, page_range_str: str = None) -> List[Tuple[int, bytes]]:
        """
        将 PDF 转换为图片列表

        Args:
            pdf_path: PDF 文件路径
            page_range_str: 页码范围字符串

        Returns:
            [(页码，图片数据), ...] 列表
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF 文件不存在：{pdf_path}")

        images = []

        try:
            doc = fitz.open(pdf_path)
            total_pages = len(doc)

            # 解析页码范围
            pages_to_process = self.parse_page_range(page_range_str, total_pages)

            logger.info(f"PDF 共 {total_pages} 页，将处理 {len(pages_to_process)} 页")

            for page_num in pages_to_process:
                # fitz 的页码从 0 开始
                page = doc[page_num - 1]

                # 创建缩放矩阵
                zoom = self.scale_factor
                mat = fitz.Matrix(zoom, zoom)

                # 渲染页面为图片
                pix = page.get_pixmap(matrix=mat)

                # 转换为 PNG 格式
                img_data = pix.tobytes("png")

                images.append((page_num, img_data))
                logger.debug(f"已转换第 {page_num} 页")

            doc.close()
            logger.info(f"成功转换 {len(images)} 页")

        except Exception as e:
            logger.error(f"PDF 转换失败：{e}")
            raise

        return images

    def get_pdf_page_count(self, pdf_path: str) -> int:
        """
        获取 PDF 页数

        Args:
            pdf_path: PDF 文件路径

        Returns:
            页数
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF 文件不存在：{pdf_path}")

        try:
            doc = fitz.open(pdf_path)
            page_count = len(doc)
            doc.close()
            return page_count
        except Exception as e:
            logger.error(f"获取 PDF 页数失败：{e}")
            raise
