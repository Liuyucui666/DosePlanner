"""
籽源管理器

负责管理籽源的位置、方向、类型，
支持路径规划、编辑和优化。
"""

import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class Seed:
    """籽源数据类"""

    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)  # 位置 (mm)
    orientation: Tuple[float, float, float] = (0.0, 0.0, 1.0)  # 方向向量
    seed_type_id: int = 1  # 籽源类型ID
    activity: float = 3.0  # 活度 (mCi)
    seed_id: Optional[int] = None  # 唯一标识


class SeedManager:
    """籽源管理器"""

    def __init__(self, db_session=None):
        """
        初始化籽源管理器

        Args:
            db_session: 数据库会话
        """
        self.session = db_session
        self._seeds: List[Seed] = []
        self._next_id = 1

    def add_seed(
        self,
        position: Tuple[float, float, float],
        orientation: Tuple[float, float, float] = (0.0, 0.0, 1.0),
        seed_type_id: int = 1,
        activity: float = 3.0,
    ) -> int:
        """
        添加籽源

        Args:
            position: 位置坐标 (x, y, z) mm
            orientation: 方向向量 (dx, dy, dz)
            seed_type_id: 籽源类型ID
            activity: 活度 (mCi)

        Returns:
            seed_id: 籽源ID
        """
        seed = Seed(
            position=position,
            orientation=orientation,
            seed_type_id=seed_type_id,
            activity=activity,
            seed_id=self._next_id,
        )
        self._seeds.append(seed)
        self._next_id += 1
        return seed.seed_id

    def add_seeds_from_path(
        self,
        path_points: List[Tuple[float, float, float]],
        spacing: float = 10.0,
        seed_type_id: int = 1,
        activity: float = 3.0,
        orientation: Optional[Tuple[float, float, float]] = None,
    ) -> List[int]:
        """
        沿路径添加多个籽源

        Args:
            path_points: 路径点列表
            spacing: 籽源间距 (mm)
            seed_type_id: 籽源类型ID
            activity: 活度 (mCi)
            orientation: 方向向量，如果为None则使用路径方向

        Returns:
            seed_ids: 籽源ID列表
        """
        if len(path_points) < 2:
            return []

        seed_ids = []
        remaining = 0.0 

        for i in range(1, len(path_points)):
            p1 = np.array(path_points[i - 1])
            p2 = np.array(path_points[i])
            seg = p2 - p1
            seg_len = np.linalg.norm(seg)
            if seg_len < 1e-6:
                continue

            if orientation is None:
                seg_dir = seg / seg_len
            else:
                seg_dir = np.array(orientation) / np.linalg.norm(orientation)

            start_dist = remaining
            while start_dist < seg_len:
                pos = p1 + seg_dir * start_dist
                seed_id = self.add_seed(
                    position=tuple(pos),
                    orientation=tuple(seg_dir),
                    seed_type_id=seed_type_id,
                    activity=activity,
                )
                seed_ids.append(seed_id)
                start_dist += spacing

            remaining = start_dist - seg_len

        return seed_ids

    def add_seeds_in_grid(
        self,
        center: Tuple[float, float, float],
        rows: int = 3,
        cols: int = 3,
        spacing: float = 10.0,
        seed_type_id: int = 1,
        activity: float = 3.0,
        orientation: Tuple[float, float, float] = (0.0, 0.0, 1.0),
    ) -> List[int]:
        """
        在网格中放置籽源

        Args:
            center: 网格中心
            rows: 行数
            cols: 列数
            spacing: 间距 (mm)
            seed_type_id: 籽源类型ID
            activity: 活度 (mCi)
            orientation: 方向向量

        Returns:
            seed_ids: 籽源ID列表
        """
        seed_ids = []
        cx, cy, cz = center

        start_x = cx - (cols - 1) * spacing / 2
        start_y = cy - (rows - 1) * spacing / 2

        for row in range(rows):
            for col in range(cols):
                position = (
                    start_x + col * spacing,
                    start_y + row * spacing,
                    cz,
                )
                seed_id = self.add_seed(
                    position, orientation, seed_type_id, activity
                )
                seed_ids.append(seed_id)

        return seed_ids

    def update_seed(self, seed_id: int, **kwargs) -> bool:
        """
        更新籽源属性

        Args:
            seed_id: 籽源ID
            **kwargs: 要更新的属性

        Returns:
            是否成功更新
        """
        seed = self.get_seed(seed_id)
        if seed is None:
            return False

        for key, value in kwargs.items():
            if hasattr(seed, key):
                setattr(seed, key, value)

        return True

    def delete_seed(self, seed_id: int) -> bool:
        """
        删除籽源

        Args:
            seed_id: 籽源ID

        Returns:
            是否成功删除
        """
        seed = self.get_seed(seed_id)
        if seed is None:
            return False

        self._seeds.remove(seed)
        return True

    def get_seed(self, seed_id: int) -> Optional[Seed]:
        """
        根据ID获取籽源

        Args:
            seed_id: 籽源ID

        Returns:
            籽源对象，如果不存在则返回None
        """
        for seed in self._seeds:
            if seed.seed_id == seed_id:
                return seed
        return None

    def get_seeds(self) -> List[Seed]:
        """
        获取所有籽源

        Returns:
            籽源列表
        """
        return self._seeds.copy()

    def get_seed_count(self) -> int:
        """
        获取籽源数量

        Returns:
            籽源数量
        """
        return len(self._seeds)

    def clear(self):
        """清空所有籽源"""
        self._seeds.clear()

    def get_seed_positions(self) -> np.ndarray:
        """
        获取所有籽源的位置数组

        Returns:
            位置数组 (N x 3)
        """
        if not self._seeds:
            return np.empty((0, 3))

        return np.array([seed.position for seed in self._seeds])

    def get_seed_orientations(self) -> np.ndarray:
        """
        获取所有籽源的方向数组

        Returns:
            方向数组 (N x 3)
        """
        if not self._seeds:
            return np.empty((0, 3))

        return np.array([seed.orientation for seed in self._seeds])

    def get_seeds_as_dict(self) -> List[Dict[str, Any]]:
        """
        获取所有籽源的字典列表

        Returns:
            籽源字典列表
        """
        return [
            {
                "seed_id": seed.seed_id,
                "position": seed.position,
                "orientation": seed.orientation,
                "seed_type_id": seed.seed_type_id,
                "activity": seed.activity,
            }
            for seed in self._seeds
        ]

    def import_from_dict(self, seeds_data: List[Dict[str, Any]]):
        """
        从字典列表导入籽源

        Args:
            seeds_data: 籽源字典列表
        """
        self.clear()

        for seed_data in seeds_data:
            self.add_seed(
                position=seed_data.get("position", (0, 0, 0)),
                orientation=seed_data.get("orientation", (0, 0, 1)),
                seed_type_id=seed_data.get("seed_type_id", 1),
                activity=seed_data.get("activity", 100.0),
            )

    def get_bounding_box(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        获取籽源的包围盒

        Returns:
            (min_corner, max_corner) 包围盒角点
        """
        if not self._seeds:
            return np.zeros(3), np.zeros(3)

        positions = self.get_seed_positions()
        return np.min(positions, axis=0), np.max(positions, axis=0)

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取籽源统计信息

        Returns:
            统计信息字典
        """
        if not self._seeds:
            return {
                "count": 0,
                "total_activity": 0.0,
                "mean_activity": 0.0,
                "bbox": None,
            }

        positions = self.get_seed_positions()
        activities = [seed.activity for seed in self._seeds]
        min_bbox, max_bbox = self.get_bounding_box()

        return {
            "count": len(self._seeds),
            "total_activity": sum(activities),
            "mean_activity": np.mean(activities),
            "activity_range": (min(activities), max(activities)),
            "bbox": {
                "min": tuple(min_bbox),
                "max": tuple(max_bbox),
                "center": tuple((min_bbox + max_bbox) / 2),
                "size": tuple(max_bbox - min_bbox),
            },
            "seed_types": list(set(seed.seed_type_id for seed in self._seeds)),
        }