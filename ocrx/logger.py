# -- coding: utf-8 --
"""
日志系统模块
提供结构化的日志记录功能
"""

import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Callable, List, Dict, Any


class StructuredLogger:
    """结构化日志系统"""

    def __init__(self, log_file_path: str = None, gui_callback: Optional[Callable] = None):
        """
        初始化日志系统

        Args:
            log_file_path: 日志文件路径
            gui_callback: GUI 回调函数，用于实时更新日志显示
        """
        self.log_file_path = Path(log_file_path) if log_file_path else Path.home() / ".ocrx_gui.log"
        self.logs: List[Dict[str, Any]] = []
        self.gui_callback = gui_callback

        # 设置日志级别
        self.levels = {
            'DEBUG': 0,
            'INFO': 1,
            'WARNING': 2,
            'ERROR': 3,
            'CRITICAL': 4
        }
        self.current_level = 'DEBUG'

        # 初始化文件日志
        self._setup_file_logger()
        print(f"日志系统初始化完成，日志文件：{self.log_file_path}")

    def _setup_file_logger(self):
        """设置文件日志记录器"""
        self.logger = logging.getLogger('OCRXGUI')
        self.logger.setLevel(logging.DEBUG)

        # 清除现有的处理器
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)

        # 创建文件处理器
        try:
            file_handler = logging.FileHandler(self.log_file_path, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)

            # 创建格式器
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(formatter)

            # 添加处理器
            self.logger.addHandler(file_handler)
            print("文件日志记录器设置成功")
        except Exception as e:
            print(f"文件日志记录器设置失败：{e}")

    def log(self, level: str, message: str, component: str = "General") -> Dict[str, Any]:
        """
        记录结构化日志

        Args:
            level: 日志级别
            message: 日志消息
            component: 组件名称

        Returns:
            日志条目
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = {
            'timestamp': timestamp,
            'level': level,
            'component': component,
            'message': message
        }

        # 添加到内存日志
        self.logs.append(log_entry)

        # 写入文件日志
        try:
            if level == 'ERROR':
                self.logger.error(f"[{component}] {message}")
            elif level == 'WARNING':
                self.logger.warning(f"[{component}] {message}")
            elif level == 'INFO':
                self.logger.info(f"[{component}] {message}")
            elif level == 'DEBUG':
                self.logger.debug(f"[{component}] {message}")
        except Exception as e:
            print(f"写入日志文件失败：{e}")

        # 控制台输出
        print(f"[{timestamp}][{level}] {component} - {message}")

        # 调用 GUI 回调函数实时更新日志显示
        if self.gui_callback:
            try:
                self.gui_callback(log_entry)
            except Exception as e:
                print(f"GUI 回调失败：{e}")

        return log_entry

    def debug(self, message: str, component: str = "General") -> Optional[Dict[str, Any]]:
        """记录 DEBUG 级别日志"""
        if self.levels[self.current_level] <= self.levels['DEBUG']:
            return self.log('DEBUG', message, component)
        return None

    def info(self, message: str, component: str = "General") -> Optional[Dict[str, Any]]:
        """记录 INFO 级别日志"""
        if self.levels[self.current_level] <= self.levels['INFO']:
            return self.log('INFO', message, component)
        return None

    def warning(self, message: str, component: str = "General") -> Optional[Dict[str, Any]]:
        """记录 WARNING 级别日志"""
        if self.levels[self.current_level] <= self.levels['WARNING']:
            return self.log('WARNING', message, component)
        return None

    def error(self, message: str, component: str = "General") -> Dict[str, Any]:
        """记录 ERROR 级别日志"""
        return self.log('ERROR', message, component)

    def critical(self, message: str, component: str = "General") -> Dict[str, Any]:
        """记录 CRITICAL 级别日志"""
        return self.log('CRITICAL', message, component)

    def get_logs(self, level: str = None) -> List[Dict[str, Any]]:
        """
        获取日志

        Args:
            level: 日志级别，如果为 None 则返回所有日志

        Returns:
            日志列表
        """
        if level:
            return [log for log in self.logs if log['level'] == level]
        return self.logs

    def export_logs(self, file_path: str = None) -> Optional[str]:
        """
        导出日志到文件

        Args:
            file_path: 导出文件路径

        Returns:
            导出文件路径，如果失败返回 None
        """
        if not file_path:
            file_path = Path.home() / f"ocrx_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                for log in self.logs:
                    f.write(f"{log['timestamp']} - [{log['level']}] {log['component']} - {log['message']}\n")
            return str(file_path)
        except Exception as e:
            self.error(f"导出日志失败：{e}", "Logger")
            return None

    def clear_logs(self):
        """清空日志"""
        self.logs.clear()
