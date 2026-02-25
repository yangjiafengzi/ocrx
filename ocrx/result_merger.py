# -- coding: utf-8 --
"""
结果合并模块
负责将 OCR 识别结果合并为 Markdown 文档
"""

from typing import List, Tuple, Dict
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class ResultMerger:
    """结果合并器"""

    def __init__(self, output_dir: str = None):
        """
        初始化结果合并器

        Args:
            output_dir: 输出目录
        """
        self.output_dir = Path(output_dir) if output_dir else Path.home() / "Documents"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def merge_contents_to_markdown(
        self,
        results: List[Tuple[Tuple[str, int], str]],
        max_retries: int = 3
    ) -> str:
        """
        将识别结果合并为 Markdown 文档（带重试机制）

        Args:
            results: [((文件名，页码), 识别内容), ...] 列表
            max_retries: 最大重试次数

        Returns:
            合并后的 Markdown 文本
        """
        from .retry_utils import retry_operation
        
        def do_merge():
            # 按文件名和页码排序
            sorted_results = sorted(results, key=lambda x: (x[0][0], x[0][1]))

            valid_contents = []
            failure_notes = []

            for identifier, content in sorted_results:
                file_stem, page_num = identifier
                
                if content is None:
                    continue

                content_str = str(content).strip()

                if content_str and not content_str.startswith("识别失败"):
                    # 直接添加内容，不添加页码标记
                    valid_contents.append(content_str)
                        
                elif content_str.startswith("识别失败"):
                    # 记录识别失败的页面（不包含页码标记）
                    failure_note = f"<!-- 某页识别失败：{content_str} -->"
                    failure_notes.append(failure_note)
                    logger.warning(f"页面识别失败：{identifier} - Merge")

            # 合并所有内容
            if valid_contents:
                combined_content = '\n\n'.join(valid_contents)
                
                # 添加失败注释
                if failure_notes:
                    combined_content += "\n\n---\n\n## 识别说明\n\n"
                    combined_content += '\n'.join(failure_notes)
                
                return combined_content
            else:
                return "*未识别到有效内容*"
        
        def on_retry(attempt, delay, exception):
            logger.warning(f"合并失败，第 {attempt} 次重试，等待 {delay:.1f} 秒...")
        
        try:
            return retry_operation(
                do_merge,
                max_retries=max_retries,
                base_delay=1.0,  # 基础延迟1秒
                max_delay=10.0,  # 最大延迟10秒
                exceptions=(Exception,),
                on_retry=on_retry
            )
        except Exception as e:
            logger.error(f"合并失败（已重试{max_retries}次）：{e}")
            raise  # 重新抛出异常，让上层处理

    def save_to_file(
        self,
        content: str,
        file_stem: str,
        output_dir: str = None
    ) -> str:
        """
        保存内容到文件

        Args:
            content: 要保存的内容
            file_stem: 文件名（不含扩展名）
            output_dir: 输出目录

        Returns:
            保存的文件路径
        """
        if output_dir:
            self.output_dir = Path(output_dir)
        
        self.output_dir.mkdir(parents=True, exist_ok=True)

        output_path = self.output_dir / f"{file_stem}_ocr.md"

        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"已保存到：{output_path}", "Save")
            return str(output_path)

        except Exception as e:
            logger.error(f"保存文件失败：{e}", "Save")
            raise

    def save_multiple_files(
        self,
        results_by_file: Dict[str, List[Tuple[Tuple[str, int], str]]],
        output_dir: str = None
    ) -> Dict[str, str]:
        """
        保存多个文件的结果

        Args:
            results_by_file: {文件名：识别结果列表}
            output_dir: 输出目录

        Returns:
            {文件名：保存路径} 字典
        """
        saved_paths = {}

        for file_stem, results in results_by_file.items():
            try:
                # 合并结果
                markdown_content = self.merge_contents_to_markdown(results)
                
                # 保存到文件
                output_path = self.save_to_file(markdown_content, file_stem, output_dir)
                saved_paths[file_stem] = output_path
                
            except Exception as e:
                logger.error(f"保存文件 {file_stem} 失败：{e}", "Save")
                saved_paths[file_stem] = None

        return saved_paths

    def set_output_dir(self, output_dir: str):
        """
        设置输出目录

        Args:
            output_dir: 输出目录路径
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"输出目录设置为：{output_dir}", "Config")
