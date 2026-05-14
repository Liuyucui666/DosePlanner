"""
剂量-颜色映射
"""

import numpy as np
from typing import Tuple, List, Optional
from enum import Enum


class DoseMapper:
    """剂量-颜色映射器"""

    def __init__(self, colormap: str = "viridis"):
        """
        初始化剂量映射器

        Args:
            colormap: 颜色映射名称
        """
        self.colormap = colormap
        self._dose_range = (0.0, 100.0)

    def set_dose_range(self, min_dose: float, max_dose: float):
        """
        设置剂量范围

        Args:
            min_dose: 最小剂量
            max_dose: 最大剂量
        """
        self._dose_range = (min_dose, max_dose)

    def dose_to_color(self, dose_value: float) -> Tuple[float, float, float]:
        """
        将剂量值映射为颜色

        Args:
            dose_value: 剂量值

        Returns:
            颜色 (r, g, b)，值范围0-1
        """
        # 归一化
        dose_min, dose_max = self._dose_range
        if dose_max - dose_min < 1e-10:
            normalized = 0.0
        else:
            normalized = (dose_value - dose_min) / (dose_max - dose_min)
            normalized = np.clip(normalized, 0.0, 1.0)

        return self._apply_colormap(normalized)

    def dose_grid_to_colors(self, dose_grid: np.ndarray) -> np.ndarray:
        """
        将剂量网格转换为颜色数组

        Args:
            dose_grid: 剂量网格 (3D数组)

        Returns:
            颜色数组 (..., 3)
        """
        # 归一化
        dose_min, dose_max = self._dose_range
        if dose_max - dose_min < 1e-10:
            normalized = np.zeros_like(dose_grid)
        else:
            normalized = (dose_grid - dose_min) / (dose_max - dose_min)
            normalized = np.clip(normalized, 0.0, 1.0)

        # 应用颜色映射
        colors = self._apply_colormap_grid(normalized)
        return colors

    def _apply_colormap(self, value: float) -> Tuple[float, float, float]:
        """应用颜色映射"""
        if self.colormap == "viridis":
            return self._viridis(value)
        elif self.colormap == "plasma":
            return self._plasma(value)
        elif self.colormap == "hot":
            return self._hot(value)
        elif self.colormap == "cool":
            return self._cool(value)
        else:
            return self._jet(value)

    def _apply_colormap_grid(self, values: np.ndarray) -> np.ndarray:
        """对网格应用颜色映射"""
        # 简单实现：使用逐点映射
        shape = values.shape
        flat_values = values.flatten()
        flat_colors = np.array([self._apply_colormap(v) for v in flat_values])
        return flat_colors.reshape(*shape, 3)

    @staticmethod
    def _viridis(t: float) -> Tuple[float, float, float]:
        """Viridis颜色映射"""
        # 简化的Viridis实现
        if t < 0.25:
            return (0.267, 0.004, 0.329)
        elif t < 0.5:
            return (0.282, 0.281, 0.543)
        elif t < 0.75:
            return (0.127, 0.567, 0.550)
        else:
            return (0.369, 0.789, 0.383)

    @staticmethod
    def _plasma(t: float) -> Tuple[float, float, float]:
        """Plasma颜色映射"""
        if t < 0.25:
            return (0.050, 0.030, 0.528)
        elif t < 0.5:
            return (0.417, 0.000, 0.572)
        elif t < 0.75:
            return (0.792, 0.299, 0.356)
        else:
            return (0.940, 0.738, 0.169)

    @staticmethod
    def _hot(t: float) -> Tuple[float, float, float]:
        """Hot颜色映射"""
        return (min(t * 2, 1.0), min(t * 4 - 2, 1.0), min(t * 6 - 4, 1.0))

    @staticmethod
    def _cool(t: float) -> Tuple[float, float, float]:
        """Cool颜色映射"""
        return (t, 1.0 - t, 1.0)

    @staticmethod
    def _jet(t: float) -> Tuple[float, float, float]:
        """Jet颜色映射"""
        if t < 0.125:
            return (0.0, 0.0, 0.5 + t * 4.0)
        elif t < 0.375:
            return (0.0, (t - 0.125) * 4.0, 1.0)
        elif t < 0.625:
            return ((t - 0.375) * 4.0, 1.0, 1.0 - (t - 0.375) * 4.0)
        elif t < 0.875:
            return (1.0, 1.0 - (t - 0.625) * 4.0, 0.0)
        else:
            return (1.0 - (t - 0.875) * 4.0, 0.0, 0.0)

    @staticmethod
    def get_available_colormaps() -> List[str]:
        """获取可用的颜色映射列表"""
        return ["viridis", "plasma", "hot", "cool", "jet", "rainbow", "inferno", "magma"]