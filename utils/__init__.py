"""
工具模块

提供文件IO、数据验证、日志配置和并行计算等通用工具。
"""

from .file_io import (
    load_npy_data,
    save_npy_data,
    load_dicom_series,
    save_dose_result,
    load_dose_result,
)
from .validation import (
    validate_seed_parameters,
    validate_dose_grid,
    validate_orientation,
    validate_position,
)
from .logging_config import setup_logging, get_logger
from .parallel import (
    parallel_map,
    cached_computation,
    CachedFunction,
)
from .project_io import (
    save_project,
    load_project,
    create_project_name,
    list_projects,
)

__all__ = [
    # 文件IO
    "load_npy_data",
    "save_npy_data",
    "load_dicom_series",
    "save_dose_result",
    "load_dose_result",

    # 项目IO
    "save_project",
    "load_project",
    "create_project_name",
    "list_projects",

    # 验证
    "validate_seed_parameters",
    "validate_dose_grid",
    "validate_orientation",
    "validate_position",

    # 日志
    "setup_logging",
    "get_logger",

    # 并行计算
    "parallel_map",
    "cached_computation",
    "CachedFunction",
]