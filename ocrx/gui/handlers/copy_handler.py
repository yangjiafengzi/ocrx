# -- coding: utf-8 --
"""
识别并复制功能处理器
"""

from pathlib import Path
from typing import List, Tuple, Optional, Dict
from .base_handler import BaseHandler
from ...pdf_processor import PDFProcessor


class CopyHandler(BaseHandler):
    """识别并复制功能处理器"""

    def check_page_limit(
        self,
        file_paths: List[str],
        page_range: str
    ) -> Tuple[bool, int, str]:
        """
        检查页数限制

        Args:
            file_paths: 文件路径列表
            page_range: 页码范围

        Returns:
            (是否通过, 总页数, 提示信息)
        """
        total_pages = 0
        
        for file_path in file_paths:
            path_obj = Path(file_path)
            if path_obj.suffix.lower() == '.pdf':
                try:
                    pdf_processor = PDFProcessor()
                    page_count = pdf_processor.get_pdf_page_count(file_path)
                    total_pages += page_count
                except Exception as e:
                    self.logger.warning(f"无法获取PDF页数 {file_path}: {e}", "Validation")
                    total_pages += 1
            else:
                total_pages += 1
        
        # 如果指定了页码范围，计算实际页数
        if page_range:
            try:
                range_pages = self._estimate_page_range_count(page_range)
                if range_pages > 0:
                    total_pages = min(total_pages, range_pages)
            except:
                pass
        
        # 检查是否超过限制
        if total_pages > self.COPY_MAX_PAGES:
            msg = (
                f"识别并复制模式仅支持 {self.COPY_MAX_PAGES} 页以下的文档。\n"
                f"当前文档共 {total_pages} 页。\n\n"
                f"建议：\n"
                f"1. 使用'识别并保存'模式处理大文档\n"
                f"2. 或使用页面范围指定前 {self.COPY_MAX_PAGES} 页"
            )
            return False, total_pages, msg
        
        return True, total_pages, ""

    def _estimate_page_range_count(self, page_range_str: str) -> int:
        """
        估算页码范围指定的页数

        Args:
            page_range_str: 页码范围字符串

        Returns:
            估算的页数
        """
        if not page_range_str:
            return 0
        
        total = 0
        parts = page_range_str.split(',')
        
        for part in parts:
            part = part.strip()
            if not part:
                continue
            
            if '-' in part:
                try:
                    start, end = part.split('-', 1)
                    start = int(start.strip())
                    end = int(end.strip())
                    total += max(0, end - start + 1)
                except:
                    total += 1
            else:
                total += 1
        
        return total

    def process_files(
        self,
        file_paths: List[str],
        prompt: str,
        page_range: str
    ) -> Tuple[bool, str]:
        """
        处理文件（识别并复制）

        Args:
            file_paths: 文件路径列表
            prompt: 提示词
            page_range: 页码范围

        Returns:
            (是否成功, 结果内容或错误信息)
        """
        try:
            self._update_status("开始识别并复制...")
            
            # 执行处理
            success, result = self.processing_service.process_and_copy(
                file_paths=file_paths,
                prompt=prompt,
                page_range_str=page_range
            )

            if success:
                # 限制显示字数（复制不受限制）
                display_result = self._prepare_display_content(result)
                
                # 显示结果到常驻页面
                self._display_result(display_result)
                
                # 复制到剪贴板（必须在主线程中执行）
                self._update_status("复制到剪贴板...")
                
                def do_copy():
                    copy_success = self.clipboard_history.copy_to_clipboard(result)
                    if copy_success:
                        msg = (
                            f"识别并复制完成！\n"
                            f"结果已复制到剪贴板，并显示在'识别结果'页面（限{self.DISPLAY_MAX_LENGTH}字）。"
                        )
                        if len(result) > self.DISPLAY_MAX_LENGTH:
                            msg += f"\n\n注意：完整内容（{len(result)}字）已复制到剪贴板。"
                        self.show_message("处理完成", msg, "info")
                        self.logger.info("识别并复制完成，已复制到剪贴板", "Task")
                    else:
                        self.show_message(
                            "复制失败",
                            "自动复制到剪贴板失败！\n结果已显示在'识别结果'页面，请手动复制。",
                            "warning"
                        )
                        self.logger.warning("剪贴板复制失败", "Task")
                
                self.root.after(0, do_copy)
            else:
                self.show_message("处理失败", result, "error")
                self.logger.error(f"识别失败：{result}", "Task")
            
            return success, result

        except Exception as e:
            self.logger.error(f"处理失败：{e}", "Task")
            self.show_message("处理失败", str(e), "error")
            return False, str(e)

    def _prepare_display_content(self, result: str) -> str:
        """
        准备显示内容（限制字数）

        Args:
            result: 完整结果

        Returns:
            限制字数后的内容
        """
        if len(result) > self.DISPLAY_MAX_LENGTH:
            return (
                result[:self.DISPLAY_MAX_LENGTH] + 
                f"\n\n... (内容已截断，共 {len(result)} 字，完整内容已复制到剪贴板)"
            )
        return result
