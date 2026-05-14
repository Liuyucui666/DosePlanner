"""
输入验证和错误检查
"""

from typing import Dict, Any, List, Optional, Tuple
import numpy as np

from config.constants import ValidationRules


class ValidationError(Exception):
    """验证错误"""
    pass


def validate_seed_parameters(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """
    验证籽源参数

    Args:
        parameters: 籽源参数字典

    Returns:
        验证后的参数字典

    Raises:
        ValidationError: 参数验证失败
    """
    errors = []

    # 验证活度
    if "activity" in parameters:
        activity = parameters["activity"]
        if not isinstance(activity, (int, float)):
            errors.append("活度必须是数值")
        elif activity < ValidationRules.MIN_SEED_ACTIVITY:
            errors.append(f"活度不能小于 {ValidationRules.MIN_SEED_ACTIVITY} mCi")
        elif activity > ValidationRules.MAX_SEED_ACTIVITY:
            errors.append(f"活度不能大于 {ValidationRules.MAX_SEED_ACTIVITY} mCi")

    # 验证个数
    if "count" in parameters:
        count = parameters["count"]
        if not isinstance(count, int):
            errors.append("个数必须是整数")
        elif count < ValidationRules.MIN_SEED_COUNT:
            errors.append(f"个数不能小于 {ValidationRules.MIN_SEED_COUNT}")
        elif count > ValidationRules.MAX_SEED_COUNT:
            errors.append(f"个数不能大于 {ValidationRules.MAX_SEED_COUNT}")

    # 验证间距
    if "spacing" in parameters:
        spacing = parameters["spacing"]
        if not isinstance(spacing, (int, float)):
            errors.append("间距必须是数值")
        elif spacing < ValidationRules.MIN_SEED_SPACING:
            errors.append(f"间距不能小于 {ValidationRules.MIN_SEED_SPACING} mm")
        elif spacing > ValidationRules.MAX_SEED_SPACING:
            errors.append(f"间距不能大于 {ValidationRules.MAX_SEED_SPACING} mm")

    if errors:
        raise ValidationError("\n".join(errors))

    return parameters


def validate_dose_grid(dose_grid: np.ndarray) -> bool:
    """
    验证剂量网格

    Args:
        dose_grid: 剂量网格数组

    Returns:
        是否有效

    Raises:
        ValidationError: 剂量网格无效
    """
    if not isinstance(dose_grid, np.ndarray):
        raise ValidationError("剂量网格必须是NumPy数组")

    if dose_grid.ndim != 3:
        raise ValidationError(f"剂量网格必须是3D数组，当前维度: {dose_grid.ndim}")

    if dose_grid.size == 0:
        raise ValidationError("剂量网格为空")

    if not np.all(np.isfinite(dose_grid)):
        raise ValidationError("剂量网格包含非有限值（NaN或Inf）")

    min_val = np.min(dose_grid)
    if min_val < 0:
        raise ValidationError(f"剂量网格包含负值: {min_val}")

    return True


def validate_orientation(
    orientation: Tuple[float, float, float],
) -> Tuple[float, float, float]:
    """
    验证方向向量

    Args:
        orientation: 方向向量 (dx, dy, dz)

    Returns:
        归一化后的方向向量

    Raises:
        ValidationError: 方向向量无效
    """
    if len(orientation) != 3:
        raise ValidationError(f"方向向量必须包含3个分量，当前: {len(orientation)}")

    vec = np.array(orientation, dtype=np.float64)

    if not np.all(np.isfinite(vec)):
        raise ValidationError("方向向量包含非有限值")

    norm = np.linalg.norm(vec)
    if norm < 1e-10:
        raise ValidationError("方向向量不能为零向量")

    # 归一化
    normalized = tuple(vec / norm)
    return normalized


def validate_position(
    position: Tuple[float, float, float],
) -> Tuple[float, float, float]:
    """
    验证位置坐标

    Args:
        position: 位置坐标 (x, y, z) mm

    Returns:
        验证通过的位置坐标

    Raises:
        ValidationError: 位置坐标无效
    """
    if len(position) != 3:
        raise ValidationError(f"位置坐标必须包含3个分量，当前: {len(position)}")

    for i, value in enumerate(position):
        if not isinstance(value, (int, float)):
            raise ValidationError(f"位置坐标分量 {i} 必须是数值")
        if not np.isfinite(value):
            raise ValidationError(f"位置坐标分量 {i} 包含非有限值")

    return position


def validate_positive_number(value: float, name: str, min_val: float = 0) -> float:
    """
    验证正数

    Args:
        value: 要验证的值
        name: 参数名称
        min_val: 最小值

    Returns:
        验证通过的值

    Raises:
        ValidationError: 数值无效
    """
    if not isinstance(value, (int, float)):
        raise ValidationError(f"{name} 必须是数值")

    if value < min_val:
        raise ValidationError(f"{name} 不能小于 {min_val}")

    return value


def validate_range(
    value: float,
    name: str,
    min_val: float,
    max_val: float,
) -> float:
    """
    验证数值范围

    Args:
        value: 要验证的值
        name: 参数名称
        min_val: 最小值
        max_val: 最大值

    Returns:
        验证通过的值

    Raises:
        ValidationError: 数值超出范围
    """
    if not isinstance(value, (int, float)):
        raise ValidationError(f"{name} 必须是数值")

    if value < min_val or value > max_val:
        raise ValidationError(f"{name} 必须在 {min_val} 到 {max_val} 之间")

    return value


def validate_file_extension(
    filename: str,
    allowed_extensions: List[str],
) -> bool:
    """
    验证文件扩展名

    Args:
        filename: 文件名
        allowed_extensions: 允许的扩展名列表

    Returns:
        是否有效

    Raises:
        ValidationError: 文件扩展名无效
    """
    import os

    ext = os.path.splitext(filename)[1].lower()
    if ext not in allowed_extensions:
        raise ValidationError(f"不支持的文件格式: {ext}，支持: {allowed_extensions}")

    return True


def validate_grid_parameters(
    grid_resolution: float,
    grid_size: int,
) -> Dict[str, Any]:
    """
    验证网格参数

    Args:
        grid_resolution: 网格分辨率
        grid_size: 网格大小

    Returns:
        验证后的参数字典

    Raises:
        ValidationError: 参数无效
    """
    errors = []

    if not isinstance(grid_resolution, (int, float)):
        errors.append("网格分辨率必须是数值")
    elif grid_resolution < ValidationRules.MIN_GRID_RESOLUTION:
        errors.append(f"网格分辨率不能小于 {ValidationRules.MIN_GRID_RESOLUTION} mm")
    elif grid_resolution > ValidationRules.MAX_GRID_RESOLUTION:
        errors.append(f"网格分辨率不能大于 {ValidationRules.MAX_GRID_RESOLUTION} mm")

    if not isinstance(grid_size, int):
        errors.append("网格大小必须是整数")
    elif grid_size < ValidationRules.MIN_GRID_SIZE:
        errors.append(f"网格大小不能小于 {ValidationRules.MIN_GRID_SIZE}")
    elif grid_size > ValidationRules.MAX_GRID_SIZE:
        errors.append(f"网格大小不能大于 {ValidationRules.MAX_GRID_SIZE}")

    if errors:
        raise ValidationError("\n".join(errors))

    return {
        "grid_resolution": grid_resolution,
        "grid_size": grid_size,
    }