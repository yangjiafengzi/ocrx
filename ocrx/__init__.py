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
from .pdf_processor import PDFProcessor
from .image_processor import ImageProcessor
from .ocr_engine import OCREngine
from .result_merger import ResultMerger
from .processing_service import ProcessingService

__all__ = [
    "ClipboardHistory",
    "StructuredLogger",
    "OCRClient",
    "ConfigManager",
    "PDFProcessor",
    "ImageProcessor",
    "OCREngine",
    "ResultMerger",
    "ProcessingService",
]
