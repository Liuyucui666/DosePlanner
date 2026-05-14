"""
医学可视化专用色图
"""

import numpy as np
from typing import Dict, List, Tuple, Optional


class DoseColorMaps:
    """医学剂量专用色图"""

    @staticmethod
    def get_dose_colormap(name: str = "dose_clinical") -> Dict[str, List[float]]:
        """
        获取剂量色图

        Args:
            name: 色图名称

        Returns:
            色图定义（控制点列表）
        """
        colormaps = {
            "dose_clinical": DoseColorMaps._dose_clinical(),
            "dose_hot_iron": DoseColorMaps._dose_hot_iron(),
            "dose_rainbow": DoseColorMaps._dose_rainbow(),
            "dose_thermal": DoseColorMaps._dose_thermal(),
            "ct_bone": DoseColorMaps._ct_bone(),
            "ct_lung": DoseColorMaps._ct_lung(),
        }

        return colormaps.get(name, colormaps["dose_clinical"])

    @staticmethod
    def get_available_colormaps() -> List[str]:
        """获取可用色图列表"""
        return [
            "dose_clinical",
            "dose_hot_iron",
            "dose_rainbow",
            "dose_thermal",
            "ct_bone",
            "ct_lung",
        ]

    @staticmethod
    def _dose_clinical() -> Dict[str, List[float]]:
        """临床剂量色图（蓝-绿-黄-红）"""
        return {
            "positions": [0.0, 0.25, 0.5, 0.75, 1.0],
            "red": [0.0, 0.0, 0.0, 1.0, 1.0],
            "green": [0.0, 0.5, 1.0, 1.0, 0.0],
            "blue": [0.5, 1.0, 0.0, 0.0, 0.0],
        }

    @staticmethod
    def _dose_hot_iron() -> Dict[str, List[float]]:
        """热铁色图（黑-红-橙-黄-白）"""
        return {
            "positions": [0.0, 0.25, 0.5, 0.75, 1.0],
            "red": [0.0, 0.5, 1.0, 1.0, 1.0],
            "green": [0.0, 0.0, 0.5, 0.8, 1.0],
            "blue": [0.0, 0.0, 0.0, 0.2, 1.0],
        }

    @staticmethod
    def _dose_rainbow() -> Dict[str, List[float]]:
        """彩虹色图"""
        return {
            "positions": [0.0, 0.17, 0.33, 0.5, 0.67, 0.83, 1.0],
            "red": [0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 1.0],
            "green": [0.0, 0.0, 1.0, 1.0, 1.0, 0.0, 0.0],
            "blue": [0.0, 1.0, 1.0, 0.0, 0.0, 0.0, 1.0],
        }

    @staticmethod
    def _dose_thermal() -> Dict[str, List[float]]:
        """热感色图"""
        return {
            "positions": [0.0, 0.25, 0.5, 0.75, 1.0],
            "red": [0.0, 0.3, 0.8, 1.0, 1.0],
            "green": [0.0, 0.0, 0.3, 0.7, 1.0],
            "blue": [0.0, 0.0, 0.0, 0.0, 1.0],
        }

    @staticmethod
    def _ct_bone() -> Dict[str, List[float]]:
        """CT骨窗色图"""
        return {
            "positions": [0.0, 0.5, 0.75, 1.0],
            "red": [0.0, 0.5, 0.8, 1.0],
            "green": [0.0, 0.5, 0.8, 1.0],
            "blue": [0.0, 0.5, 0.8, 1.0],
        }

    @staticmethod
    def _ct_lung() -> Dict[str, List[float]]:
        """CT肺窗色图"""
        return {
            "positions": [0.0, 0.5, 1.0],
            "red": [0.0, 0.5, 1.0],
            "green": [0.0, 0.5, 1.0],
            "blue": [0.0, 0.5, 1.0],
        }

    @staticmethod
    def interpolate_color(
        colormap: Dict[str, List[float]],
        value: float,
    ) -> Tuple[float, float, float]:
        """
        在色图中插值颜色

        Args:
            colormap: 色图定义
            value: 归一化的值 (0-1)

        Returns:
            颜色 (r, g, b)
        """
        positions = colormap["positions"]

        # 边界处理
        if value <= positions[0]:
            return (
                colormap["red"][0],
                colormap["green"][0],
                colormap["blue"][0],
            )
        if value >= positions[-1]:
            return (
                colormap["red"][-1],
                colormap["green"][-1],
                colormap["blue"][-1],
            )

        # 查找插值区间
        for i in range(len(positions) - 1):
            if positions[i] <= value <= positions[i + 1]:
                # 线性插值
                t = (value - positions[i]) / (positions[i + 1] - positions[i])
                r = colormap["red"][i] + t * (colormap["red"][i + 1] - colormap["red"][i])
                g = colormap["green"][i] + t * (colormap["green"][i + 1] - colormap["green"][i])
                b = colormap["blue"][i] + t * (colormap["blue"][i + 1] - colormap["blue"][i])
                return (r, g, b)

        return (0, 0, 0)

    @staticmethod
    def get_vtk_color_transfer_function(name: str = "dose_clinical"):
        """
        获取VTK颜色传输函数

        Args:
            name: 色图名称

        Returns:
            VTK颜色传输函数
        """
        try:
            import vtk

            colormap = DoseColorMaps.get_dose_colormap(name)

            ctf = vtk.vtkColorTransferFunction()
            positions = colormap["positions"]

            for i, pos in enumerate(positions):
                ctf.AddRGBPoint(
                    pos,
                    colormap["red"][i],
                    colormap["green"][i],
                    colormap["blue"][i],
                )

            return ctf
        except ImportError:
            return None

    @staticmethod
    def create_opacity_function(
        dose_range: Tuple[float, float],
        peak_position: float = 0.5,
    ) -> Dict[str, List[float]]:
        """
        创建不透明度函数

        Args:
            dose_range: 剂量范围 (min, max)
            peak_position: 峰值位置 (0-1)

        Returns:
            不透明度函数定义
        """
        return {
            "positions": [0.0, peak_position * 0.5, peak_position, 1.0],
            "opacities": [0.0, 0.3, 0.8, 0.2],
        }