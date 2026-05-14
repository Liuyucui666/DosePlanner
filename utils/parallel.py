"""
并行计算工具
"""

import os
from typing import Callable, List, Any, Optional, Dict
from functools import wraps
from pathlib import Path

import numpy as np
from joblib import Parallel, delayed, Memory, dump, load


def parallel_map(
    func: Callable,
    items: List[Any],
    n_jobs: int = -1,
    backend: str = "loky",
    verbose: int = 0,
    **kwargs,
) -> List[Any]:
    """
    并行映射函数

    Args:
        func: 要执行的函数
        items: 输入项列表
        n_jobs: 并行任务数（-1表示使用所有CPU核心）
        backend: 并行后端 ('loky', 'threading', 'multiprocessing')
        verbose: 详细程度

    Returns:
        结果列表
    """
    if n_jobs == -1:
        n_jobs = os.cpu_count()

    if n_jobs == 1 or len(items) == 1:
        # 串行执行
        return [func(item, **kwargs) for item in items]

    # 并行执行
    results = Parallel(n_jobs=n_jobs, backend=backend, verbose=verbose)(
        delayed(func)(item, **kwargs) for item in items
    )

    return results


def parallel_chunked(
    func: Callable,
    items: List[Any],
    chunk_size: int = 10,
    n_jobs: int = -1,
    **kwargs,
) -> List[Any]:
    """
    分块并行处理

    Args:
        func: 要执行的函数
        items: 输入项列表
        chunk_size: 块大小
        n_jobs: 并行任务数

    Returns:
        结果列表
    """
    # 分块
    chunks = [
        items[i : i + chunk_size] for i in range(0, len(items), chunk_size)
    ]

    # 并行处理每个块
    chunk_results = parallel_map(
        _process_chunk_wrapper,
        [(func, chunk, kwargs) for chunk in chunks],
        n_jobs=n_jobs,
    )

    # 合并结果
    results = []
    for chunk_result in chunk_results:
        results.extend(chunk_result)

    return results


def _process_chunk_wrapper(args: tuple) -> List[Any]:
    """处理单个块的包装函数"""
    func, chunk, kwargs = args
    return [func(item, **kwargs) for item in chunk]


def cached_computation(
    cache_dir: Optional[str] = None,
    verbose: bool = False,
):
    """
    缓存装饰器

    用于缓存计算密集型函数的结果

    Args:
        cache_dir: 缓存目录
        verbose: 是否显示详细信息

    Returns:
        装饰器函数
    """
    if cache_dir is None:
        cache_dir = "./cache"

    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)

    memory = Memory(location=str(cache_dir), verbose=verbose)

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return memory.cache(func)(*args, **kwargs)

        return wrapper

    return decorator


class CachedFunction:
    """缓存函数类"""

    def __init__(self, cache_dir: str = "./cache"):
        """
        初始化缓存函数

        Args:
            cache_dir: 缓存目录
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.memory = Memory(location=str(self.cache_dir), verbose=0)

    def cache(self, func: Callable) -> Callable:
        """
        缓存函数

        Args:
            func: 要缓存的函数

        Returns:
            缓存后的函数
        """
        return self.memory.cache(func)

    def clear(self):
        """清除所有缓存"""
        self.memory.clear()

    def clear_function(self, func: Callable):
        """清除特定函数的缓存"""
        try:
            self.memory.clear(warn=False)
        except Exception:
            pass

    def get_cache_size(self) -> int:
        """获取缓存大小（字节）"""
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(self.cache_dir):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                total_size += os.path.getsize(filepath)
        return total_size


def parallel_dose_calculation(
    seed_dose_func: Callable,
    seeds: List[Dict[str, Any]],
    n_jobs: int = -1,
    verbose: bool = False,
) -> np.ndarray:
    """
    并行剂量计算

    Args:
        seed_dose_func: 单个籽源的剂量计算函数
        seeds: 籽源列表
        n_jobs: 并行任务数
        verbose: 是否显示进度

    Returns:
        所有籽源的剂量网格之和
    """
    # 并行计算每个籽源的剂量分布
    dose_grids = parallel_map(
        seed_dose_func,
        seeds,
        n_jobs=n_jobs,
        verbose=1 if verbose else 0,
    )

    # 叠加所有剂量分布
    total_dose = np.sum(dose_grids, axis=0)

    return total_dose


def batch_process(
    items: List[Any],
    func: Callable,
    batch_size: int = 100,
    n_jobs: int = -1,
    verbose: bool = False,
) -> List[Any]:
    """
    批量处理

    Args:
        items: 待处理项列表
        func: 处理函数
        batch_size: 批次大小
        n_jobs: 并行任务数
        verbose: 是否显示进度

    Returns:
        处理结果列表
    """
    results = []

    for i in range(0, len(items), batch_size):
        batch = items[i : i + batch_size]

        if verbose:
            print(f"Processing batch {i // batch_size + 1}/{(len(items) + batch_size - 1) // batch_size}")

        batch_results = parallel_map(func, batch, n_jobs=n_jobs)
        results.extend(batch_results)

    return results