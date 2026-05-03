# -- coding: utf-8 --
"""
剪贴板管理模块
提供剪贴板历史记录管理和复制功能
"""

import hashlib
from datetime import datetime
from typing import List, Dict, Any, Optional
import time
import logging
import sys
import tkinter as tk

logger = logging.getLogger(__name__)


class ClipboardHistory:
    """剪贴板历史记录管理"""

    def __init__(self, max_history: int = 10):
        """
        初始化剪贴板历史记录

        Args:
            max_history: 最大历史记录数量
        """
        self.history: List[Dict[str, Any]] = []
        self.max_history = max_history

    def add_record(self, content: str, success: bool = True, method: str = "auto", error_msg: str = ""):
        """
        添加复制记录

        Args:
            content: 复制的内容（完整内容）
            success: 是否复制成功
            method: 使用的复制方法
            error_msg: 错误信息
        """
        record = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'content': content,  # 存储完整内容
            'content_preview': content[:100] + "..." if len(content) > 100 else content,
            'content_length': len(content),
            'content_hash': hashlib.md5(content.encode('utf-8')).hexdigest()[:8],
            'success': success,
            'method': method,
            'error_msg': error_msg
        }

        self.history.append(record)
        # 保持历史记录数量限制
        if len(self.history) > self.max_history:
            self.history.pop(0)
            
    def get_content_by_index(self, index: int) -> Optional[str]:
        """
        根据索引获取完整内容

        Args:
            index: 历史记录索引

        Returns:
            完整内容，如果不存在返回 None
        """
        if 0 <= index < len(self.history):
            return self.history[index].get('content')
        return None

    def get_history(self) -> List[Dict[str, Any]]:
        """获取历史记录"""
        return self.history

    def clear_history(self):
        """清空历史记录"""
        self.history.clear()

    def copy_to_clipboard(self, content: str, max_retries: int = 3) -> bool:
        """
        复制内容到剪贴板（使用 tkinter，简单可靠）
        
        注意：剪贴板是系统资源，必须是串行的，不能并发

        Args:
            content: 要复制的内容
            max_retries: 最大重试次数

        Returns:
            是否复制成功
        """
        logger.info(f"开始复制到剪贴板，内容长度：{len(content)}")
        
        for attempt in range(max_retries + 1):
            try:
                # 创建 tkinter 根窗口
                root = tk.Tk()
                root.withdraw()
                
                # 清空并设置剪贴板
                root.clipboard_clear()
                root.clipboard_append(content)
                root.update()
                root.destroy()
                
                logger.info(f"tkinter 复制成功（尝试 {attempt + 1}）")
                self.add_record(content, success=True, method="tkinter")
                return True
                
            except Exception as e:
                logger.error(f"复制尝试 {attempt + 1} 失败: {e}")
                if attempt < max_retries:
                    wait_time = 0.5 * (attempt + 1)  # 递增等待时间
                    logger.info(f"等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"所有复制尝试都失败（已重试{max_retries}次）")
                    self.add_record(content, success=False, method="tkinter", error_msg=str(e))
                    return False
        
        return False

    def get_record_by_hash(self, content_hash: str) -> Optional[Dict[str, Any]]:
        """
        根据哈希值获取记录

        Args:
            content_hash: 内容哈希值

        Returns:
            记录字典，如果不存在返回 None
        """
        for record in self.history:
            if record['content_hash'] == content_hash:
                return record
        return None

    def get_recent_records(self, count: int = 5) -> List[Dict[str, Any]]:
        """
        获取最近的记录

        Args:
            count: 记录数量

        Returns:
            记录列表
        """
        return self.history[-count:] if len(self.history) >= count else self.history
