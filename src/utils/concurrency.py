"""
并发处理工具模块
提供线程池和进程池并发执行功能
"""

import os
from typing import List, Dict, Any, Callable, Optional, TypeVar, Generic
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from functools import wraps
import pandas as pd
from loguru import logger

T = TypeVar("T")
R = TypeVar("R")


class ConcurrentProcessor:
    """并发处理器，支持线程池和进程池"""

    def __init__(self, max_workers: Optional[int] = None, use_threads: bool = True):
        """
        初始化并发处理器

        Args:
            max_workers: 最大工作线程/进程数，默认为CPU核心数的2倍
            use_threads: 是否使用线程池（True）或进程池（False）
        """
        if max_workers is None:
            max_workers = min(32, (os.cpu_count() or 1) * 2)
        self.max_workers = max_workers
        self.use_threads = use_threads

    def process_batch(
        self,
        items: List[T],
        processor: Callable[[T], R],
        desc: str = "处理中",
        show_progress: bool = True,
    ) -> Dict[T, R]:
        """
        批量并发处理

        Args:
            items: 待处理的项目列表
            processor: 处理函数
            desc: 进度描述
            show_progress: 是否显示进度

        Returns:
            项目到结果的映射字典
        """
        results = {}
        executor_class = ThreadPoolExecutor if self.use_threads else ProcessPoolExecutor

        with executor_class(max_workers=self.max_workers) as executor:
            future_to_item = {executor.submit(processor, item): item for item in items}

            completed = 0
            total = len(items)

            for future in as_completed(future_to_item):
                item = future_to_item[future]
                completed += 1

                try:
                    result = future.result()
                    results[item] = result

                    if show_progress and completed % 10 == 0:
                        logger.info(f"{desc}: {completed}/{total}")

                except Exception as e:
                    logger.error(f"处理 {item} 时出错: {e}")
                    results[item] = None

        return results

    def process_batch_with_index(
        self,
        items: List[T],
        processor: Callable[[int, T], R],
        desc: str = "处理中",
        show_progress: bool = True,
    ) -> List[R]:
        """
        带索引的批量并发处理

        Args:
            items: 待处理的项目列表
            processor: 处理函数，接受索引和项目
            desc: 进度描述
            show_progress: 是否显示进度

        Returns:
            按索引顺序排列的结果列表
        """
        results = [None] * len(items)
        executor_class = ThreadPoolExecutor if self.use_threads else ProcessPoolExecutor

        with executor_class(max_workers=self.max_workers) as executor:
            future_to_index = {
                executor.submit(processor, idx, item): idx
                for idx, item in enumerate(items)
            }

            completed = 0
            total = len(items)

            for future in as_completed(future_to_index):
                idx = future_to_index[future]
                completed += 1

                try:
                    result = future.result()
                    results[idx] = result

                    if show_progress and completed % 10 == 0:
                        logger.info(f"{desc}: {completed}/{total}")

                except Exception as e:
                    logger.error(f"处理索引 {idx} 时出错: {e}")
                    results[idx] = None

        return results


def parallel_map(
    func: Callable[[T], R],
    items: List[T],
    max_workers: Optional[int] = None,
    use_threads: bool = True,
    desc: str = "并行处理",
) -> List[R]:
    """
    并行映射函数

    Args:
        func: 处理函数
        items: 待处理项目列表
        max_workers: 最大工作线程/进程数
        use_threads: 是否使用线程池
        desc: 进度描述

    Returns:
        结果列表
    """
    processor = ConcurrentProcessor(max_workers=max_workers, use_threads=use_threads)

    results_dict = processor.process_batch(items, func, desc=desc, show_progress=False)

    return [results_dict.get(item) for item in items]


def batch_fetch_stock_data(
    stock_codes: List[str], fetcher: Callable[[str], pd.DataFrame], max_workers: int = 8
) -> Dict[str, pd.DataFrame]:
    """
    批量获取股票数据（并发版本）

    Args:
        stock_codes: 股票代码列表
        fetcher: 数据获取函数
        max_workers: 最大并发数

    Returns:
        股票代码到数据的映射
    """
    processor = ConcurrentProcessor(max_workers=max_workers, use_threads=True)
    return processor.process_batch(
        items=stock_codes, processor=fetcher, desc="获取股票数据", show_progress=True
    )


__all__ = [
    "ConcurrentProcessor",
    "parallel_map",
    "batch_fetch_stock_data",
]
