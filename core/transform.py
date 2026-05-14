"""
三维几何变换工具

提供3D旋转、平移、缩放变换和坐标系转换功能。
"""

import numpy as np
from typing import Tuple, Optional


class Transform3D:
    """3D几何变换工具"""

    @staticmethod
    def get_rotation_matrix(
        orientation: Tuple[float, float, float],
        reference: Tuple[float, float, float] = (0.0, 0.0, 1.0),
    ) -> np.ndarray:
        """
        根据方向向量计算旋转矩阵

        将参考方向旋转到目标方向

        Args:
            orientation: 目标方向向量 (dx, dy, dz)
            reference: 参考方向向量，默认为Z轴正方向

        Returns:
            旋转矩阵 (3x3)
        """
        # 归一化输入向量
        v1 = np.array(reference, dtype=np.float64)
        v1 = v1 / np.linalg.norm(v1)

        v2 = np.array(orientation, dtype=np.float64)
        norm = np.linalg.norm(v2)
        if norm < 1e-10:
            return np.eye(3)
        v2 = v2 / norm

        # 计算旋转轴和角度
        cross = np.cross(v1, v2)
        dot = np.clip(np.dot(v1, v2), -1.0, 1.0)

        # 如果方向相同，返回单位矩阵
        if abs(dot - 1.0) < 1e-10:
            return np.eye(3)

        # 如果方向相反，旋转180度
        if abs(dot + 1.0) < 1e-10:
            # 选择垂直于v1的任意轴
            if abs(v1[0]) < abs(v1[1]):
                axis = np.array([1.0, 0.0, 0.0])
            else:
                axis = np.array([0.0, 1.0, 0.0])
            axis = axis - np.dot(axis, v1) * v1
            axis = axis / np.linalg.norm(axis)
            angle = np.pi
        else:
            axis = cross / np.linalg.norm(cross)
            angle = np.arccos(dot)

        # 使用Rodrigues旋转公式
        K = np.array([
            [0, -axis[2], axis[1]],
            [axis[2], 0, -axis[0]],
            [-axis[1], axis[0], 0]
        ])

        rotation_matrix = (
            np.eye(3)
            + np.sin(angle) * K
            + (1 - np.cos(angle)) * np.dot(K, K)
        )

        return rotation_matrix

    @staticmethod
    def rotate_volume(
        volume: np.ndarray,
        rotation_matrix: np.ndarray,
    ) -> np.ndarray:
        """
        对3D体积应用旋转变换

        使用三线性插值实现体积旋转

        Args:
            volume: 3D NumPy数组
            rotation_matrix: 3x3旋转矩阵

        Returns:
            旋转后的体积
        """
        from scipy.ndimage import affine_transform

        # 计算旋转中心（体积中心）
        center = np.array(volume.shape) / 2.0

        # 构建仿射变换矩阵（包含中心点偏移）
        offset = center - np.dot(rotation_matrix, center)

        # 应用仿射变换
        rotated = affine_transform(
            volume,
            rotation_matrix,
            offset=offset,
            order=1,  # 三线性插值
            mode='constant',
            cval=0.0,
        )

        return rotated

    @staticmethod
    def translate_volume(
        volume: np.ndarray,
        position: Tuple[float, float, float],
        grid_origin: Tuple[float, float, float],
        grid_resolution: float,
    ) -> np.ndarray:
        """
        对3D体积应用平移变换

        将体积移动到指定位置

        Args:
            volume: 3D NumPy数组
            position: 目标位置 (mm)
            grid_origin: 网格原点 (mm)
            grid_resolution: 网格分辨率 (mm/体素)

        Returns:
            平移后的体积
        """
        # 计算平移量（体素单位）
        translation = np.array(position) - np.array(grid_origin)
        translation_voxels = translation / grid_resolution

        from scipy.ndimage import shift

        translated = shift(
            volume,
            -translation_voxels,
            order=1,
            mode='constant',
            cval=0.0,
        )

        return translated

    @staticmethod
    def scale_volume(
        volume: np.ndarray,
        scale_factor: float,
    ) -> np.ndarray:
        """
        对3D体积应用缩放变换

        Args:
            volume: 3D NumPy数组
            scale_factor: 缩放因子

        Returns:
            缩放后的体积
        """
        from scipy.ndimage import zoom

        scaled = zoom(
            volume,
            scale_factor,
            order=1,
        )

        return scaled

    @staticmethod
    def coordinate_transform(
        coordinates: np.ndarray,
        transform_matrix: np.ndarray,
    ) -> np.ndarray:
        """
        坐标系变换

        Args:
            coordinates: 坐标数组 (N x 3)
            transform_matrix: 4x4齐次变换矩阵

        Returns:
            变换后的坐标
        """
        # 转换为齐次坐标
        n_points = coordinates.shape[0]
        homogeneous = np.ones((n_points, 4))
        homogeneous[:, :3] = coordinates

        # 应用变换
        transformed = np.dot(homogeneous, transform_matrix.T)

        return transformed[:, :3]

    @staticmethod
    def image_to_world_coordinates(
        image_coords: np.ndarray,
        origin: Tuple[float, float, float],
        spacing: Tuple[float, float, float],
        direction: np.ndarray,
    ) -> np.ndarray:
        """
        图像坐标转换为世界坐标

        Args:
            image_coords: 图像坐标 (体素索引) (N x 3)
            origin: 图像原点 (mm)
            spacing: 体素间距 (mm)
            direction: 方向矩阵 (3x3)

        Returns:
            世界坐标 (mm) (N x 3)
        """
        # 应用间距和方向
        world_coords = np.dot(image_coords, np.diag(spacing))
        world_coords = np.dot(world_coords, direction.T)

        # 加上原点偏移
        world_coords += np.array(origin)

        return world_coords

    @staticmethod
    def world_to_image_coordinates(
        world_coords: np.ndarray,
        origin: Tuple[float, float, float],
        spacing: Tuple[float, float, float],
        direction: np.ndarray,
    ) -> np.ndarray:
        """
        世界坐标转换为图像坐标

        Args:
            world_coords: 世界坐标 (mm) (N x 3)
            origin: 图像原点 (mm)
            spacing: 体素间距 (mm)
            direction: 方向矩阵 (3x3)

        Returns:
            图像坐标 (体素索引) (N x 3)
        """
        # 减去原点偏移
        coords = world_coords - np.array(origin)

        # 应用方向逆矩阵
        coords = np.dot(coords, np.linalg.inv(direction).T)

        # 除以间距
        coords = coords / np.array(spacing)

        return coords

    @staticmethod
    def rotate_point(
        point: Tuple[float, float, float],
        rotation_matrix: np.ndarray,
        center: Tuple[float, float, float] = (0, 0, 0),
    ) -> Tuple[float, float, float]:
        """
        绕指定中心旋转点

        Args:
            point: 待旋转的点
            rotation_matrix: 旋转矩阵
            center: 旋转中心

        Returns:
            旋转后的点
        """
        p = np.array(point)
        c = np.array(center)

        # 平移到原点、旋转、平移回原位
        rotated = np.dot(rotation_matrix, p - c) + c

        return tuple(rotated)

    @staticmethod
    def create_translation_matrix(
        translation: Tuple[float, float, float]
    ) -> np.ndarray:
        """
        创建平移矩阵

        Args:
            translation: 平移向量 (x, y, z)

        Returns:
            4x4平移矩阵
        """
        matrix = np.eye(4)
        matrix[:3, 3] = translation
        return matrix

    @staticmethod
    def create_scale_matrix(
        scale: Tuple[float, float, float]
    ) -> np.ndarray:
        """
        创建缩放矩阵

        Args:
            scale: 缩放因子 (sx, sy, sz)

        Returns:
            4x4缩放矩阵
        """
        matrix = np.eye(4)
        matrix[0, 0] = scale[0]
        matrix[1, 1] = scale[1]
        matrix[2, 2] = scale[2]
        return matrix

    @staticmethod
    def create_rotation_matrix_axis_angle(
        axis: Tuple[float, float, float],
        angle_degrees: float,
    ) -> np.ndarray:
        """
        创建绕指定轴旋转的旋转矩阵

        Args:
            axis: 旋转轴
            angle_degrees: 旋转角度（度）

        Returns:
            4x4旋转矩阵
        """
        axis = np.array(axis, dtype=np.float64)
        axis = axis / np.linalg.norm(axis)

        angle = np.radians(angle_degrees)
        cos_a = np.cos(angle)
        sin_a = np.sin(angle)

        x, y, z = axis

        rotation = np.array([
            [cos_a + x*x*(1-cos_a), x*y*(1-cos_a) - z*sin_a, x*z*(1-cos_a) + y*sin_a, 0],
            [y*x*(1-cos_a) + z*sin_a, cos_a + y*y*(1-cos_a), y*z*(1-cos_a) - x*sin_a, 0],
            [z*x*(1-cos_a) - y*sin_a, z*y*(1-cos_a) + x*sin_a, cos_a + z*z*(1-cos_a), 0],
            [0, 0, 0, 1],
        ])

        return rotation