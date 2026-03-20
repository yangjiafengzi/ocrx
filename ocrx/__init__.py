# -- coding: utf-8 --
"""
OCRX - 智能文字识别系统
"""

__version__ = "2.1.0"
__author__ = "OCRX Team"

from .clipboard import ClipboardHistory
from .logger import StructuredLogger
from .ocr_client import OCRClient
from .config import ConfigManager
from .image_processor import ImageProcessor
from .ocr_engine import OCREngine
from .result_merger import ResultMerger
from .processing_service import ProcessingService

# PDFProcessor 延迟导入，避免 PyMuPDF 导入问题
PDFProcessor = None

def get_pdf_processor():
    """延迟获取 PDFProcessor，处理 PyMuPDF 导入问题"""
    global PDFProcessor
    if PDFProcessor is None:
        try:
            from .pdf_processor import PDFProcessor as PP
            PDFProcessor = PP
        except ImportError as e:
            import logging
            logging.getLogger(__name__).error(f"无法导入 PDFProcessor: {e}")
            raise
    return PDFProcessor

__all__ = [
    "ClipboardHistory",
    "StructuredLogger",
    "OCRClient",
    "ConfigManager",
    "ImageProcessor",
    "OCREngine",
    "ResultMerger",
    "ProcessingService",
    "get_pdf_processor",
]
