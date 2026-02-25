# -- coding: utf-8 --
"""
识别并保存功能处理器
"""

from pathlib import Path
from typing import List, Dict, Tuple, Optional
from .base_handler import BaseHandler


class SaveHandler(BaseHandler):
    """识别并保存功能处理器"""

    def process_files(
        self,
        file_paths: List[str],
        prompt: str,
        page_range: str
    ) -> Dict[str, Tuple[bool, Optional[str]]]:
        """
        处理文件（识别并保存）

        Args:
            file_paths: 文件路径列表
            prompt: 提示词
            page_range: 页码范围

        Returns:
            处理结果字典
        """
        try:
            self._update_status("开始识别并保存...")
            
            # 执行处理
            results = self.processing_service.process_files(
                file_paths=file_paths,
                prompt=prompt,
                page_range_str=page_range
            )

            # 处理完成
            success_count = sum(1 for success, _ in results.values() if success)
            total_count = len(results)
            
            # 读取保存的文件内容并显示到结果窗口
            display_content = self._prepare_display_content(results)
            if display_content:
                self._display_result(display_content)
            
            # 显示完成消息
            self.show_message(
                "处理完成",
                f"识别并保存完成！\n成功：{success_count}/{total_count} 个文件\n\n"
                f"结果已保存到指定目录，并显示在'识别结果'页面（限{self.DISPLAY_MAX_LENGTH}字）。",
                "info"
            )
            
            self.logger.info(f"识别并保存完成：{success_count}/{total_count} 成功", "Task")
            
            return results

        except Exception as e:
            self.logger.error(f"处理失败：{e}", "Task")
            self.show_message("处理失败", str(e), "error")
            return {}

    def _prepare_display_content(
        self,
        results: Dict[str, Tuple[bool, Optional[str]]]
    ) -> str:
        """
        准备显示内容（限制字数）

        Args:
            results: 处理结果字典

        Returns:
            显示内容
        """
        all_content = []
        total_length = 0
        
        for file_stem, (success, output_path) in results.items():
            if success and output_path:
                try:
                    with open(output_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                        # 检查是否超过限制
                        if total_length + len(content) > self.DISPLAY_MAX_LENGTH:
                            remaining = self.DISPLAY_MAX_LENGTH - total_length
                            if remaining > 0:
                                all_content.append(f"=== {file_stem} ===\n")
                                all_content.append(content[:remaining])
                                all_content.append(
                                    f"\n... (内容已截断，完整内容请查看文件: {output_path})"
                                )
                            break
                        else:
                            all_content.append(f"=== {file_stem} ===\n")
                            all_content.append(content)
                            all_content.append("\n\n")
                            total_length += len(content) + len(file_stem) + 10
                            
                except Exception as e:
                    self.logger.warning(f"读取文件失败 {output_path}: {e}", "SaveProcess")
        
        return "".join(all_content) if all_content else ""
