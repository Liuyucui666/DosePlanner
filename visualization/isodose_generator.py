"""
等剂量线生成器
"""

import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from scipy import ndimage


class IsodoseGenerator:
    """等剂量线生成器"""

    def __init__(self):
        self._surfaces = {}

    def generate_isodose_surfaces(
        self,
        dose_grid: np.ndarray,
        levels: List[float],
        smooth_iterations: int = 0,
    ) -> Dict[float, Dict[str, np.ndarray]]:
        """
        生成等剂量面

        Args:
            dose_grid: 剂量网格 (3D数组)
            levels: 等剂量水平列表（绝对值）
            smooth_iterations: 平滑迭代次数

        Returns:
            等剂量面字典 {level: {vertices, faces, normals}}
        """
        from skimage import measure

        # 可选：高斯平滑
        if smooth_iterations > 0:
            dose_grid = ndimage.gaussian_filter(
                dose_grid, sigma=smooth_iterations
            )

        surfaces = {}
        for level in levels:
            try:
                # 使用Marching Cubes算法
                verts, faces, normals, values = measure.marching_cubes(
                    dose_grid,
                    level=level,
                    spacing=(1.0, 1.0, 1.0),
                    gradient_direction='ascent',
                )

                surfaces[level] = {
                    "vertices": verts,
                    "faces": faces,
                    "normals": normals,
                    "values": values,
                }
            except Exception as e:
                # 如果该等值面不存在，跳过
                pass

        self._surfaces = surfaces
        return surfaces

    def generate_isodose_contours(
        self,
        dose_slice: np.ndarray,
        levels: List[float],
    ) -> Dict[float, List[np.ndarray]]:
        """
        生成2D等剂量线

        Args:
            dose_slice: 2D剂量切片
            levels: 等剂量水平列表

        Returns:
            等剂量线字典 {level: [contour1, contour2, ...]}
        """
        from skimage import measure

        contours = {}
        for level in levels:
            try:
                contour_lines = measure.find_contours(dose_slice, level)
                if contour_lines:
                    contours[level] = contour_lines
            except Exception:
                pass

        return contours

    def calculate_isodose_metrics(
        self,
        dose_grid: np.ndarray,
        target_mask: np.ndarray,
        prescription_dose: float,
    ) -> Dict[str, Any]:
        """
        计算等剂量相关指标

        Args:
            dose_grid: 剂量网格
            target_mask: 靶区掩膜
            prescription_dose: 处方剂量

        Returns:
            指标字典
        """
        if target_mask.sum() == 0:
            return {}

        target_doses = dose_grid[target_mask]

        # V100: 接受处方剂量的靶区体积百分比
        v100 = (target_doses >= prescription_dose).sum() / target_mask.sum() * 100

        # V150: 接受150%处方剂量的靶区体积百分比
        v150 = (target_doses >= prescription_dose * 1.5).sum() / target_mask.sum() * 100

        # D90: 90%靶区体积接受的剂量
        sorted_doses = np.sort(target_doses)
        d90_index = int(len(sorted_doses) * 0.9)
        d90 = sorted_doses[d90_index] if d90_index < len(sorted_doses) else 0

        # D95: 95%靶区体积接受的剂量
        d95_index = int(len(sorted_doses) * 0.95)
        d95 = sorted_doses[d95_index] if d95_index < len(sorted_doses) else 0

        # 适形指数(CI)
        prescription_volume = (dose_grid >= prescription_dose).sum()
        target_volume = target_mask.sum()
        ci = (prescription_volume & target_volume) / prescription_volume if prescription_volume > 0 else 0

        return {
            "v100": float(v100),
            "v150": float(v150),
            "d90": float(d90),
            "d95": float(d95),
            "conformity_index": float(ci),
            "prescription_dose": float(prescription_dose),
            "target_volume": int(target_volume),
            "target_mean_dose": float(target_doses.mean()),
            "target_max_dose": float(target_doses.max()),
            "target_min_dose": float(target_doses.min()),
        }

    def get_surface_vertices(self, level: float) -> Optional[np.ndarray]:
        """
        获取指定水平的等剂量面顶点

        Args:
            level: 等剂量水平

        Returns:
            顶点数组
        """
        surface = self._surfaces.get(level)
        return surface["vertices"] if surface else None

    def get_surface_faces(self, level: float) -> Optional[np.ndarray]:
        """
        获取指定水平的等剂量面三角面片

        Args:
            level: 等剂量水平

        Returns:
            面片数组
        """
        surface = self._surfaces.get(level)
        return surface["faces"] if surface else None

    def clear(self):
        """清空所有等剂量面数据"""
        self._surfaces.clear()