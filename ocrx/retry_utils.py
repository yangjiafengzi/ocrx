# -- coding: utf-8 --
"""
重试工具模块
提供通用的重试机制和验证功能
"""

import time
import functools
from typing import Callable, Any, Tuple, Optional
from difflib import SequenceMatcher


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exceptions: Tuple[type, ...] = (Exception,),
    on_retry: Optional[Callable] = None
):
    """
    重试装饰器，使用等差数列延迟机制

    Args:
        max_retries: 最大重试次数
        base_delay: 基础延迟时间（秒）
        max_delay: 最大延迟时间（秒）
        exceptions: 需要捕获的异常类型
        on_retry: 重试时的回调函数，参数为 (attempt, delay, exception)

    Returns:
        装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt >= max_retries:
                        # 超过最大重试次数，抛出异常
                        raise last_exception
                    
                    # 计算延迟时间（等差数列：第n次等待n个单位时间）
                    delay = min(base_delay * (attempt + 1), max_delay)
                    
                    if on_retry:
                        on_retry(attempt + 1, delay, e)
                    
                    time.sleep(delay)
            
            # 不应该到达这里
            raise last_exception if last_exception else RuntimeError("未知错误")
        
        return wrapper
    return decorator


def retry_operation(
    operation: Callable,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exceptions: Tuple[type, ...] = (Exception,),
    on_retry: Optional[Callable] = None
) -> Any:
    """
    对单个操作进行重试

    Args:
        operation: 要执行的操作函数
        max_retries: 最大重试次数
        base_delay: 基础延迟时间（秒）
        max_delay: 最大延迟时间（秒）
        exceptions: 需要捕获的异常类型
        on_retry: 重试时的回调函数

    Returns:
        操作结果
    """
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            return operation()
        except exceptions as e:
            last_exception = e
            
            if attempt >= max_retries:
                raise last_exception
            
            delay = min(base_delay * (attempt + 1), max_delay)
            
            if on_retry:
                on_retry(attempt + 1, delay, e)
            
            time.sleep(delay)
    
    raise last_exception if last_exception else RuntimeError("未知错误")


def verify_clipboard_content(
    expected_content: str,
    sample_length: int = 10,
    min_similarity: float = 0.7
) -> bool:
    """
    验证剪贴板内容是否与预期内容匹配

    Args:
        expected_content: 预期的内容
        sample_length: 采样长度（从头尾各取多少字符）
        min_similarity: 最小相似度（0-1）

    Returns:
        是否验证通过
    """
    try:
        import pyperclip
        clipboard_content = pyperclip.paste()
        
        if not clipboard_content or not expected_content:
            return False
        
        # 如果内容很短，直接比较全部
        if len(expected_content) <= sample_length * 2:
            similarity = SequenceMatcher(None, expected_content, clipboard_content).ratio()
            return similarity >= min_similarity
        
        # 比较头部
        head_expected = expected_content[:sample_length]
        head_clipboard = clipboard_content[:sample_length]
        head_similarity = SequenceMatcher(None, head_expected, head_clipboard).ratio()
        
        # 比较尾部
        tail_expected = expected_content[-sample_length:]
        tail_clipboard = clipboard_content[-sample_length:] if len(clipboard_content) >= sample_length else clipboard_content
        tail_similarity = SequenceMatcher(None, tail_expected, tail_clipboard).ratio()
        
        # 计算总相似度
        total_similarity = (head_similarity + tail_similarity) / 2
        
        return total_similarity >= min_similarity
        
    except Exception:
        return False


def copy_to_clipboard_with_verification(
    content: str,
    max_retries: int = 3,
    base_delay: float = 0.5,
    sample_length: int = 10,
    min_similarity: float = 0.7
) -> Tuple[bool, str]:
    """
    复制到剪贴板并验证

    Args:
        content: 要复制的内容
        max_retries: 最大重试次数
        base_delay: 基础延迟时间（秒）
        sample_length: 验证采样长度
        min_similarity: 最小相似度

    Returns:
        (是否成功, 错误信息)
    """
    import pyperclip
    
    def do_copy():
        pyperclip.copy(content)
        if not verify_clipboard_content(content, sample_length, min_similarity):
            raise RuntimeError("剪贴板验证失败")
    
    try:
        retry_operation(
            do_copy,
            max_retries=max_retries,
            base_delay=base_delay,
            exceptions=(Exception,)
        )
        return True, ""
    except Exception as e:
        return False, str(e)
