# -- coding: utf-8 --
"""
重试工具模块
提供通用的重试机制和取消信号
"""

import functools
import time
from typing import Any, Callable, Optional, Tuple


class OperationCancelledError(Exception):
    """任务被用户取消时抛出的异常。"""


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
