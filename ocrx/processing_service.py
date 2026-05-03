# -- coding: utf-8 --
"""
处理服务模块
整合所有处理模块，提供完整的 OCR 处理流程
"""

from pathlib import Path
from typing import List, Dict, Tuple, Optional, Callable
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from .pdf_processor import PDFProcessor
from .image_processor import ImageProcessor
from .ocr_engine import OCREngine
from .result_merger import ResultMerger
from .logger import StructuredLogger

logger = logging.getLogger(__name__)


class ProcessingService:
    """OCR 处理服务"""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model_name: str,
        output_dir: str,
        max_workers: int = 10,
        pdf_scale: float = 3.0,
        logger_inst: Optional[StructuredLogger] = None
    ):
        """
        初始化处理服务

        Args:
            api_key: API 密钥
            base_url: API 基础 URL
            model_name: 模型名称
            output_dir: 输出目录
            max_workers: 最大并发数
            pdf_scale: PDF 缩放比例
            logger_inst: 日志实例
        """
        self.api_key = api_key
        self.base_url = base_url
        self.model_name = model_name
        self.output_dir = output_dir
        self.max_workers = max_workers
        self.pdf_scale = pdf_scale
        self.logger_inst = logger_inst or StructuredLogger()

        # 初始化各个处理器
        self.pdf_processor = PDFProcessor(scale_factor=pdf_scale)
        self.image_processor = ImageProcessor()
        self.result_merger = ResultMerger(output_dir)

        # 初始化 OCR 引擎
        self.ocr_engine = OCREngine(
            api_key=api_key,
            base_url=base_url,
            model_name=model_name,
            max_workers=max_workers,
            logger_inst=self.logger_inst
        )

        # 进度回调
        self._progress_callback: Optional[Callable] = None
        self._status_callback: Optional[Callable] = None

        self.logger_inst.info("处理服务初始化完成", "System")

    def set_progress_callback(self, callback: Callable):
        """设置进度回调"""
        self._progress_callback = callback

    def set_status_callback(self, callback: Callable):
        """设置状态回调"""
        self._status_callback = callback

    def _update_progress(self, current: int, total: int, phase: str, percent: float):
        """更新进度"""
        if self._progress_callback:
            self._progress_callback(current, total, percent, phase)

    def _update_status(self, status: str):
        """更新状态"""
        if self._status_callback:
            self._status_callback(status)

    def _prepare_images(
        self,
        file_paths: List[str],
        page_range_str: Optional[str] = None,
        progress_callback = None
    ) -> Tuple[List[Tuple[str, int, bytes]], Dict[str, Tuple[bool, Optional[str]]]]:
        """
        准备图片（PDF转图片或读取图片文件）

        Args:
            file_paths: 文件路径列表
            page_range_str: 页码范围字符串
            progress_callback: 进度回调函数，参数为 (current, total, phase, percent)

        Returns:
            (所有页面列表, 失败的文件结果字典)
            页面列表: [(file_stem, page_num, img_data), ...]
        """
        all_pages = []
        failed_files = {}
        total_files = len(file_paths)

        for file_idx, file_path in enumerate(file_paths):
            path_obj = Path(file_path)
            if not path_obj.exists():
                failed_files[path_obj.stem] = (False, None)
                continue

            suffix_lower = path_obj.suffix.lower()

            try:
                if suffix_lower == '.pdf':
                    images = self.pdf_processor.pdf_to_images(
                        str(path_obj), page_range_str
                    )
                    for page_num, img_data in images:
                        all_pages.append((path_obj.stem, page_num, img_data))

                elif self.image_processor.is_supported_image(str(path_obj)):
                    img_data = self.image_processor.image_file_to_bytes(str(path_obj))
                    if img_data:
                        all_pages.append((path_obj.stem, 1, img_data))
                    else:
                        failed_files[path_obj.stem] = (False, None)
                else:
                    self.logger_inst.warning(f"不支持的文件类型：{suffix_lower}", "FileProcess")
                    failed_files[path_obj.stem] = (False, None)

            except Exception as e:
                self.logger_inst.error(f"处理文件失败 {path_obj.name}: {e}", "FileProcess")
                failed_files[path_obj.stem] = (False, None)

            # 更新进度（0-20%）
            if progress_callback:
                percent = ((file_idx + 1) / total_files) * 20 if total_files > 0 else 0
                progress_callback(file_idx + 1, total_files, f"预处理 ({file_idx + 1}/{total_files})", percent)

        return all_pages, failed_files

    def _recognize_pages(
        self,
        pages: List[Tuple[str, int, bytes]],
        prompt: str,
        progress_callback = None,
        example_images: List[Tuple[str, bytes]] = None
    ) -> List[Tuple[Tuple[str, int], str]]:
        """
        识别所有页面（OCR），支持少样本提示

        Args:
            pages: 页面列表 [(file_stem, page_num, img_data), ...]
            prompt: 提示词
            progress_callback: 进度回调函数，参数为 (current, total, phase, percent)
            example_images: 少样本示例列表 [(示例文本, 示例图片数据), ...]

        Returns:
            识别结果列表 [((file_stem, page_num), content), ...]
        """
        if not pages:
            return []

        total_pages = len(pages)
        successful_results = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            future_to_index = {}
            for i, (file_stem, page_num, img_data) in enumerate(pages):
                identifier = (file_stem, page_num)
                self.logger_inst.debug(f"提交任务：页面 {file_stem}-{page_num}", "OCR")
                future = executor.submit(
                    self.ocr_engine.process_single_image,
                    prompt,
                    identifier,
                    img_data,
                    5,  # max_retries
                    example_images  # 传入少样本示例
                )
                future_to_index[future] = i

            self.logger_inst.info(f"已提交所有 {len(future_to_index)} 个识别任务", "OCR")
            # 收集结果（带超时控制）
            completed = 0
            from concurrent.futures import TimeoutError
            
            # 循环处理每个future
            for future in as_completed(future_to_index):
                idx = future_to_index[future]
                file_stem, page_num = pages[idx][:2]
                
                try:
                    # 设置单个页面的超时时间为180秒（比API timeout多60秒缓冲）
                    result = future.result(timeout=180)
                    
                    # 检查结果
                    if isinstance(result, tuple) and len(result) == 2:
                        content = result[1]
                        successful_results.append(result)
                        self.logger_inst.debug(f"页面 {file_stem}-{page_num} 识别成功", "OCR")
                    else:
                        # 结果格式不对，添加失败结果
                        error_result = ((file_stem, page_num), "识别失败：结果格式错误")
                        successful_results.append(error_result)
                        self.logger_inst.warning(f"页面 {file_stem}-{page_num} 结果格式错误，已记录失败", "OCR")
                        
                except TimeoutError:
                    error_msg = f"识别超时（超过180秒）"
                    error_result = ((file_stem, page_num), f"识别失败：{error_msg}")
                    successful_results.append(error_result)
                    self.logger_inst.error(f"页面 {file_stem}-{page_num} {error_msg}", "OCR")
                    
                except Exception as e:
                    error_msg = f"识别异常：{str(e)}"
                    error_result = ((file_stem, page_num), f"识别失败：{error_msg}")
                    successful_results.append(error_result)
                    self.logger_inst.error(f"页面 {file_stem}-{page_num} {error_msg}", "OCR")
                
                completed += 1
                self.logger_inst.debug(f"已完成 {completed}/{total_pages} 个页面识别", "OCR")

                # 更新进度（20-90%）
                if progress_callback:
                    ocr_percent = (completed / total_pages * 100) if total_pages > 0 else 0
                    overall_percent = 20 + (ocr_percent * 0.7)
                    progress_callback(completed, total_pages, f"OCR识别 ({completed}/{total_pages})", overall_percent)

        # 统计成功识别的页数
        total_success = len(successful_results)
        self.logger_inst.info(f"识别完成，共 {total_pages} 页，成功识别 {total_success} 页", "OCR")
        for i, (file_stem_page, content) in enumerate(successful_results):
            self.logger_inst.debug(f"成功结果[{i}]: {file_stem_page} -> [{len(content)} chars] content starts with: '{content[:50]}...'", "OCR-Debug")
        return successful_results

    def _merge_results(
        self,
        results: List[Tuple[Tuple[str, int], str]],
        save_to_file: bool = False,
        progress_callback = None
    ) -> Tuple[str, Dict[str, Tuple[bool, Optional[str]]]]:
        """
        合并结果，可选保存到文件

        Args:
            results: 识别结果列表 [((file_stem, page_num), content), ...]
            save_to_file: 是否保存到文件
            progress_callback: 进度回调函数，参数为 (current, total, phase, percent)

        Returns:
            (合并后的总内容, {file_stem: (success, output_path)} 字典)
        """
        # 按文件分组
        file_pages = {}
        for (file_stem, page_num), content in results:
            if file_stem not in file_pages:
                file_pages[file_stem] = []
            file_pages[file_stem].append((page_num, content))

        output_results = {}
        all_contents = []
        total_files = len(file_pages)
        total_pages = sum(len(pages) for pages in file_pages.values())
        
        self.logger_inst.debug(f"_merge_results: 总结果数={len(results)}, 分组后文件数={total_files}, 总页数={total_pages}", "Merge-Debug")
        for file_stem, pages in file_pages.items():
            self.logger_inst.debug(f"  文件 {file_stem}: {len(pages)} 页", "Merge-Debug")
        
        # 判断是否需要分开保存：单个文件大于 10 页 或者 总页数大于 200
        should_split = False
        if total_pages > 200:
            should_split = True
        else:
            for file_stem, pages in file_pages.items():
                if len(pages) > 10:
                    should_split = True
                    break

        if should_split and save_to_file:
            # 每个文件单独合并保存
            for file_idx, (file_stem, pages) in enumerate(file_pages.items()):
                try:
                    # 按页码排序
                    pages.sort(key=lambda x: x[0])
                    # 保持 ((file_stem, page_num), content) 格式
                    sorted_results = [((file_stem, page_num), content) for page_num, content in pages]
                    # 合并结果
                    markdown_content = self.result_merger.merge_contents_to_markdown(sorted_results)
                    # 保存文件
                    output_path = self.result_merger.save_to_file(
                        content=markdown_content,
                        file_stem=file_stem,
                        output_dir=self.output_dir
                    )
                    output_results[file_stem] = (True, output_path)
                    all_contents.append(markdown_content)
                    self.logger_inst.info(f"文件处理完成：{file_stem}", "FileProcess")
                except Exception as e:
                    self.logger_inst.error(f"保存文件失败 {file_stem}: {e}", "FileProcess")
                    output_results[file_stem] = (False, None)
                
                # 更新进度（90-100%）
                if progress_callback:
                    percent = 90 + ((file_idx + 1) / total_files) * 10 if total_files > 0 else 100
                    progress_callback(file_idx + 1, total_files, f"保存结果 ({file_idx + 1}/{total_files})", percent)
        else:
            # 所有文件一起合并
            for file_idx, (file_stem, pages) in enumerate(file_pages.items()):
                try:
                    # 按页码排序
                    pages.sort(key=lambda x: x[0])
                    # 保持 ((file_stem, page_num), content) 格式
                    sorted_results = [((file_stem, page_num), content) for page_num, content in pages]
                    # 合并结果
                    markdown_content = self.result_merger.merge_contents_to_markdown(sorted_results)
                    all_contents.append(markdown_content)
                    
                    if save_to_file:
                        # 所有文件一起合并，但是每个文件也要单独保存
                        output_path = self.result_merger.save_to_file(
                            content=markdown_content,
                            file_stem=file_stem,
                            output_dir=self.output_dir
                        )
                        output_results[file_stem] = (True, output_path)
                    else:
                        output_results[file_stem] = (True, None)
                except Exception as e:
                    self.logger_inst.error(f"合并失败 {file_stem}: {e}", "FileProcess")
                    output_results[file_stem] = (False, None)
                
                # 更新进度（90-100%）
                if progress_callback:
                    action = "保存结果" if save_to_file else "合并结果"
                    percent = 90 + ((file_idx + 1) / total_files) * 10 if total_files > 0 else 100
                    progress_callback(file_idx + 1, total_files, f"{action} ({file_idx + 1}/{total_files})", percent)

        # 合并所有内容
        total_content = "\n\n".join(all_contents)
        return total_content, output_results

    def process_file(
        self,
        file_path: str,
        prompt: str,
        page_range_str: Optional[str] = None
    ) -> Tuple[bool, Optional[str], str]:
        """
        处理单个文件（使用核心方法）

        Args:
            file_path: 文件路径
            prompt: 提示词
            page_range_str: 页码范围

        Returns:
            (是否成功，输出文件路径，源文件名)
        """
        path_obj = Path(file_path)
        
        if not path_obj.exists():
            self.logger_inst.warning(f"文件不存在：{file_path}", "FileProcess")
            return (False, None, path_obj.stem)

        self.logger_inst.info(f"开始处理文件：{path_obj.name}", "FileProcess")
        self._update_status(f"处理文件：{path_obj.name}")

        # 1. 准备图片（进度：0-20%）
        all_pages, failed_files = self._prepare_images(
            [file_path],
            page_range_str,
            progress_callback=self._update_progress
        )

        if not all_pages:
            self.logger_inst.warning(f"文件没有可处理的内容：{path_obj.name}", "FileProcess")
            return (False, None, path_obj.stem)

        # 2. OCR 识别（进度：20-90%）
        self._update_status("正在 OCR 识别...")
        results = self._recognize_pages(
            all_pages,
            prompt,
            progress_callback=self._update_progress
        )

        # 3. 合并并保存（进度：90-100%）
        self._update_status("合并并保存结果...")
        total_content, output_results = self._merge_results(
            results,
            save_to_file=True,
            progress_callback=self._update_progress
        )

        # 返回结果
        if path_obj.stem in output_results:
            success, output_path = output_results[path_obj.stem]
            if success:
                self.logger_inst.info(f"处理完成：{output_path}", "FileProcess")
                self._update_status("处理完成")
                return (True, output_path, path_obj.stem)
        
        return (False, None, path_obj.stem)

    def process_files(
        self,
        file_paths: List[str],
        prompt: str,
        page_range_str: Optional[str] = None,
        example_images: List[Tuple[str, bytes]] = None
    ) -> Dict[str, Tuple[bool, Optional[str]]]:
        """
        批量处理文件（使用核心方法，支持总进度计算），支持少样本提示

        Args:
            file_paths: 文件路径列表
            prompt: 提示词
            page_range_str: 页码范围
            example_images: 少样本示例列表 [(示例文本, 示例图片数据), ...]

        Returns:
            {文件名：(是否成功，输出路径)} 字典
        """
        self.logger_inst.info(f"开始批量处理 {len(file_paths)} 个文件", "BatchProcess")
        self._update_status(f"开始处理 {len(file_paths)} 个文件...")

        # 1. 准备图片（进度：0-20%）
        all_pages, failed_files = self._prepare_images(
            file_paths,
            page_range_str,
            progress_callback=self._update_progress
        )

        if not all_pages:
            self.logger_inst.warning("没有可处理的页面", "BatchProcess")
            return failed_files

        total_pages = len(all_pages)
        self.logger_inst.info(f"共 {len(file_paths)} 个文件，{total_pages} 页待识别", "BatchProcess")

        # 2. OCR 识别（进度：20-90%）
        self._update_status("正在 OCR 识别...")
        results = self._recognize_pages(
            all_pages,
            prompt,
            progress_callback=self._update_progress,
            example_images=example_images
        )

        # 3. 合并并保存（进度：90-100%）
        self._update_status("合并并保存结果...")
        total_content, output_results = self._merge_results(
            results,
            save_to_file=True,
            progress_callback=self._update_progress
        )

        # 合并失败文件和成功文件的结果
        output_results.update(failed_files)

        self.logger_inst.info(f"批量处理完成", "BatchProcess")
        self._update_progress(total_pages, total_pages, "全部完成", 100)
        self._update_status("全部处理完成")

        return output_results

    def process_and_copy(
        self,
        file_paths: List[str],
        prompt: str,
        page_range_str: Optional[str] = None,
        example_images: List[Tuple[str, bytes]] = None
    ) -> Tuple[bool, str]:
        """
        识别并复制到剪贴板（使用核心方法，支持正确的进度计算），支持少样本提示

        Args:
            file_paths: 文件路径列表
            prompt: 提示词
            page_range_str: 页码范围
            example_images: 少样本示例列表 [(示例文本, 示例图片数据), ...]

        Returns:
            (是否成功，结果内容或错误信息)
        """
        self.logger_inst.info(f"开始识别并复制 {len(file_paths)} 个文件", "CopyProcess")
        self._update_status(f"准备识别 {len(file_paths)} 个文件...")

        try:
            # 1. 准备图片（进度：0-20%）
            all_pages, failed_files = self._prepare_images(
                file_paths,
                page_range_str,
                progress_callback=self._update_progress
            )

            if not all_pages:
                return (False, "没有可处理的图像")

            total_pages = len(all_pages)
            self.logger_inst.info(f"共 {total_pages} 页待识别", "CopyProcess")

            # 2. OCR 识别（进度：20-90%）
            self._update_status("正在 OCR 识别...")
            results = self._recognize_pages(
                all_pages,
                prompt,
                progress_callback=self._update_progress,
                example_images=example_images
            )

            # 3. 合并结果（进度：90-100%），不保存文件
            self._update_status("合并结果...")
            total_content, output_results = self._merge_results(
                results,
                save_to_file=False,
                progress_callback=self._update_progress
            )

            self._update_progress(total_pages, total_pages, "处理完成", 100)
            self.logger_inst.info(f"识别完成，共 {len(results)} 页", "CopyProcess")
            return (True, total_content)

        except Exception as e:
            error_msg = f"识别失败：{str(e)}"
            self.logger_inst.error(error_msg, "CopyProcess")
            return (False, error_msg)

    def update_config(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
        output_dir: Optional[str] = None,
        max_workers: Optional[int] = None,
        pdf_scale: Optional[float] = None
    ):
        """更新配置"""
        if api_key:
            self.api_key = api_key
        if base_url:
            self.base_url = base_url
        if model_name:
            self.model_name = model_name
        if output_dir:
            self.output_dir = output_dir
        if max_workers:
            self.max_workers = max_workers
        if pdf_scale:
            self.pdf_scale = pdf_scale

        # 重新初始化处理器
        self.pdf_processor = PDFProcessor(scale_factor=self.pdf_scale)
        self.result_merger = ResultMerger(self.output_dir)
        self.ocr_engine = OCREngine(
            api_key=self.api_key,
            base_url=self.base_url,
            model_name=self.model_name,
            max_workers=self.max_workers,
            logger_inst=self.logger_inst
        )

        self.logger_inst.info("配置已更新", "System")