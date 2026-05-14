"""
测试数据生成器

提供用于测试的模拟数据。
"""

import numpy as np
from typing import Tuple, Dict, Any


def create_test_dose_grid(
    grid_size: int = 32,
    center: Tuple[float, float, float] = None,
    peak_dose: float = 100.0,
) -> np.ndarray:
    """
    创建测试用剂量网格（高斯分布）

    Args:
        grid_size: 网格大小
        center: 中心位置
        peak_dose: 峰值剂量

    Returns:
        3D剂量网格
    """
    if center is None:
        center = (grid_size // 2, grid_size // 2, grid_size // 2)

    x, y, z = np.meshgrid(
        np.arange(grid_size),
        np.arange(grid_size),
        np.arange(grid_size),
        indexing="ij",
    )

    # 高斯分布
    sigma = grid_size / 8
    dose = peak_dose * np.exp(
        -((x - center[0]) ** 2 + (y - center[1]) ** 2 + (z - center[2]) ** 2)
        / (2 * sigma ** 2)
    )

    return dose.astype(np.float32)


def create_test_ct_image(
    shape: Tuple[int, int, int] = (64, 64, 64),
    spacing: Tuple[float, float, float] = (1.0, 1.0, 1.0),
) -> Dict[str, Any]:
    """
    创建测试用CT图像

    Args:
        shape: 图像尺寸 (z, y, x)
        spacing: 体素间距

    Returns:
        图像数据字典
    """
    z, y, x = shape

    # 创建简单的椭球体
    xx, yy, zz = np.meshgrid(
        np.linspace(-1, 1, x),
        np.linspace(-1, 1, y),
        np.linspace(-1, 1, z),
        indexing="ij",
    )

    # 椭球掩膜
    ellipsoid = (xx ** 2 + yy ** 2 * 1.5 + zz ** 2 * 2) <= 1.0

    # CT值：背景为空气，椭球为软组织
    ct_array = np.zeros(shape, dtype=np.int16)
    ct_array[ellipsoid] = 40  # 软组织CT值
    ct_array[~ellipsoid] = -1000  # 空气CT值

    # 添加一些噪声
    noise = np.random.normal(0, 10, shape).astype(np.int16)
    ct_array += noise

    return {
        "array": ct_array,
        "spacing": spacing,
        "origin": (0.0, 0.0, 0.0),
        "direction": np.eye(3),
        "size": (x, y, z),
    }


def create_test_seeds(
    count: int = 5,
    center: Tuple[float, float, float] = (32, 32, 32),
    spacing: float = 10.0,
) -> list:
    """
    创建测试用籽源数据

    Args:
        count: 籽源数量
        center: 中心位置
        spacing: 间距

    Returns:
        籽源字典列表
    """
    seeds = []
    for i in range(count):
        position = (
            center[0] + i * spacing,
            center[1],
            center[2],
        )
        seeds.append({
            "position": position,
            "orientation": (0.0, 0.0, 1.0),
            "seed_type_id": 1,
            "activity": 100.0,
        })

    return seeds


def create_test_mc_data(
    grid_size_r: int = 16,
    grid_size_z: int = 20,
    resolution_mm: float = 1.0,
) -> Dict[str, Any]:
    """
    创建测试用蒙特卡洛数据（R-Z柱坐标格式）

    Args:
        grid_size_r: R方向网格点数
        grid_size_z: Z方向网格点数
        resolution_mm: 空间分辨率

    Returns:
        蒙特卡洛数据字典（R-Z格式）
    """
    r_max = 15.0
    z_min = -10.0
    z_max = 10.0

    r_values = np.linspace(0, r_max, grid_size_r)
    z_values = np.linspace(z_min, z_max, grid_size_z)

    RR, ZZ = np.meshgrid(r_values, z_values, indexing="ij")
    dose_table = np.exp(-(RR ** 2) / (2 * 3.0 ** 2)) * np.exp(-(ZZ ** 2) / (2 * 5.0 ** 2))
    dose_table = dose_table.astype(np.float32)

    return {
        "dose_table": dose_table,
        "r_max": r_max,
        "z_min": z_min,
        "z_max": z_max,
        "grid_size_r": grid_size_r,
        "grid_size_z": grid_size_z,
        "resolution_mm": resolution_mm,
        "dose_per_decay": 1.0,
    }