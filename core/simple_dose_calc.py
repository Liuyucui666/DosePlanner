# src/dose_planner/core/simple_dose_calc.py
import numpy as np

class SimpleDoseCalculator:
    """基于线性衰减的简单剂量计算器（用于测试）"""
    def calculate_total_dose(self, seeds, grid_resolution=1.0, margin=30.0):
        """
        seeds: 字典列表，每个字典包含 'position' (x,y,z) 和 'activity'
        返回: total_dose (3D ndarray), origin (tuple), spacing (tuple)
        """
        positions = np.array([s['position'] for s in seeds])
        min_pos = positions.min(axis=0) - margin
        max_pos = positions.max(axis=0) + margin
        origin = tuple(min_pos)

        # 构建网格
        ranges = [np.arange(min_pos[i], max_pos[i] + grid_resolution, grid_resolution)
                  for i in range(3)]
        xx, yy, zz = np.meshgrid(*ranges, indexing='ij')
        total_dose = np.zeros_like(xx, dtype=np.float64)

        for seed in seeds:
            pos = np.array(seed['position'])
            activity = seed.get('activity', 100.0)
            dist = np.sqrt((xx - pos[0])**2 + (yy - pos[1])**2 + (zz - pos[2])**2)
            # 线性衰减：活性度在中心为 activity，30mm 处降为 0
            dose_contrib = np.maximum(0, activity * (1 - dist / margin))
            total_dose += dose_contrib

        spacing = (grid_resolution, grid_resolution, grid_resolution)
        return total_dose.astype(np.float32), origin, spacing