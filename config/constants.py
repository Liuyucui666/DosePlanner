"""
应用程序常量定义
"""

import numpy as np
from enum import Enum

# ============================================================================
# 物理常数
# ============================================================================

class PhysicalConstants:
    """物理常数"""

    # 通用常数
    SPEED_OF_LIGHT = 2.99792458e8  # m/s

    # 放射性衰变常数
    DAYS_TO_SECONDS = 86400  # 天到秒的转换
    LN2 = 0.6931471805599453  # ln(2)

    # 剂量单位转换
    GRAY_TO_CENTIGRAY = 100  # 1 Gy = 100 cGy
    GRAY_TO_MILLIGRAY = 1000  # 1 Gy = 1000 mGy
    MBq_TO_Bq = 1e6  # 1 MBq = 1e6 Bq
    MCi_TO_Bq = 3.7e7  # 1 mCi = 3.7e7 Bq = 3.7e7 decays/s

    # FLUKA 剂量单位转换: 1 GeV/g = 1.602e-7 Gy = 1.602e-4 mGy
    GEV_PER_G_TO_mGy = 1.602176634e-4

    # 组织参数（近似值）
    TISSUE_DENSITY = 1.0  # g/cm³（水等效组织）
    AIR_DENSITY = 0.0012  # g/cm³


# ============================================================================
# 籽源相关常量
# ============================================================================

class SeedConstants:
    """籽源相关常量"""

    # 常见籽源类型
    COMMON_SEED_TYPES = {
        "I-125": {
            "energy_kev": 27.4,  # 平均能量
            "half_life_days": 59.4,  # 半衰期（天）
            "typical_activity_mCi": 3.0,  # 典型活度 mCi（≈111 MBq）
        },
        "Pd-103": {
            "energy_kev": 20.7,
            "half_life_days": 17.0,
            "typical_activity_mCi": 3.4,  # ≈125 MBq
        },
        "Cs-131": {
            "energy_kev": 30.4,
            "half_life_days": 9.7,
            "typical_activity_mCi": 4.1,  # ≈150 MBq
        }
    }

    # 籽源尺寸（mm）
    TYPICAL_SEED_LENGTH = 4.5  # 典型长度
    TYPICAL_SEED_DIAMETER = 0.8  # 典型直径

    # 籽源方向
    DEFAULT_ORIENTATION = (0.0, 0.0, 1.0)  # 默认方向（沿Z轴）


# ============================================================================
# 剂量计算常量
# ============================================================================

class DoseConstants:
    """剂量计算常量"""

    # 网格参数
    DEFAULT_GRID_RESOLUTION = 1.0  # mm
    DEFAULT_GRID_SIZE = 32  # 每个维度的体素数

    # 剂量单位
    DOSE_UNIT = "mGy"  # 剂量单位
    DOSE_RATE_UNIT = "μGy/h"  # 剂量率单位

    # 等剂量线级别（百分比）
    DEFAULT_ISODOSE_LEVELS = [50, 80, 90, 100]

    # MC数据默认范围
    MC_R_MAX_DEFAULT = 15.0  # mm，径向默认范围
    MC_Z_MIN_DEFAULT = -10.0  # mm，轴向默认最小（负值 = 籽源中心以下）
    MC_Z_MAX_DEFAULT = 10.0  # mm，轴向默认最大（正值 = 籽源中心以上）

    # 剂量限制
    MAX_DOSE_THRESHOLD = 1e6  # mGy，超过此值可能为计算错误
    MIN_DOSE_THRESHOLD = 1e-6  # mGy，低于此值视为零


# ============================================================================
# 图像处理常量
# ============================================================================

class ImageConstants:
    """图像处理常量"""

    # CT值范围（HU）
    CT_AIR_HU = -1000
    CT_WATER_HU = 0
    CT_BONE_HU = 1000

    # 默认窗宽窗位
    DEFAULT_WINDOW_WIDTH = 400
    DEFAULT_WINDOW_LEVEL = 40

    # 图像方向
    AXIAL = "axial"
    CORONAL = "coronal"
    SAGITTAL = "sagittal"

    # 坐标系
    PATIENT_COORDINATE_SYSTEM = "patient"
    IMAGE_COORDINATE_SYSTEM = "image"
    DOSE_COORDINATE_SYSTEM = "dose"


# ============================================================================
# 可视化常量
# ============================================================================

class VisualizationConstants:
    """可视化常量"""

    # 颜色映射
    DOSE_COLORMAPS = {
        "viridis": "Viridis",
        "plasma": "Plasma",
        "inferno": "Inferno",
        "magma": "Magma",
        "hot": "Hot",
        "cool": "Cool",
        "rainbow": "Rainbow",
        "jet": "Jet",
    }

    # 默认颜色映射
    DEFAULT_DOSE_COLORMAP = "viridis"
    DEFAULT_CT_COLORMAP = "gray"

    # 透明度
    DOSE_OPACITY = 0.7
    SEED_OPACITY = 1.0
    CT_OPACITY = 1.0

    # 渲染质量
    RENDER_QUALITY_LOW = "low"
    RENDER_QUALITY_MEDIUM = "medium"
    RENDER_QUALITY_HIGH = "high"

    # 默认渲染质量
    DEFAULT_RENDER_QUALITY = RENDER_QUALITY_MEDIUM


# ============================================================================
# 应用程序常量
# ============================================================================

class AppConstants:
    """应用程序常量"""

    # 应用程序信息
    APP_NAME = "Dose Planner"
    APP_VERSION = "0.1.0"
    ORGANIZATION_NAME = "Medical Physics"

    # 文件扩展名
    DICOM_EXTENSIONS = [".dcm", ".dicom"]
    NIFTI_EXTENSIONS = [".nii", ".nii.gz", ".hdr", ".img"]
    DOSE_EXTENSIONS = [".npy", ".h5", ".hdf5"]
    PROJECT_EXTENSIONS = [".doseplan"]

    # 默认文件路径
    DEFAULT_PROJECT_DIR = "projects"
    DEFAULT_EXPORT_DIR = "exports"
    DEFAULT_TEMPLATE_DIR = "templates"

    # 用户界面
    DEFAULT_WINDOW_WIDTH = 1200
    DEFAULT_WINDOW_HEIGHT = 800
    MIN_WINDOW_WIDTH = 800
    MIN_WINDOW_HEIGHT = 600


# ============================================================================
# 枚举类型
# ============================================================================

class CalculationMethod(Enum):
    """剂量计算方法"""
    MONTE_CARLO = "monte_carlo"
    ANALYTICAL = "analytical"
    POINT_SOURCE = "point_source"
    LINE_SOURCE = "line_source"


class SeedPlacementMode(Enum):
    """籽源放置模式"""
    MANUAL = "manual"
    GRID = "grid"
    OPTIMIZED = "optimized"


class ViewMode(Enum):
    """视图模式"""
    AXIAL = "axial"
    CORONAL = "coronal"
    SAGITTAL = "sagittal"
    THREE_D = "3d"


class DoseDisplayMode(Enum):
    """剂量显示模式"""
    ISODOSE = "isodose"
    VOLUME = "volume"
    SLICE = "slice"
    DVH = "dvh"


# ============================================================================
# 单位转换函数
# ============================================================================

def mm_to_cm(value_mm: float) -> float:
    """毫米转换为厘米"""
    return value_mm / 10.0


def cm_to_mm(value_cm: float) -> float:
    """厘米转换为毫米"""
    return value_cm * 10.0


def mbq_to_bq(value_mbq: float) -> float:
    """MBq转换为Bq"""
    return value_mbq * 1e6


def bq_to_mbq(value_bq: float) -> float:
    """Bq转换为MBq"""
    return value_bq / 1e6


def gy_to_cgy(value_gy: float) -> float:
    """Gy转换为cGy"""
    return value_gy * 100.0


def cgy_to_gy(value_cgy: float) -> float:
    """cGy转换为Gy"""
    return value_cgy / 100.0


def days_to_seconds(value_days: float) -> float:
    """天转换为秒"""
    return value_days * 86400.0


def seconds_to_days(value_seconds: float) -> float:
    """秒转换为天"""
    return value_seconds / 86400.0


def mci_to_bq(value_mci: float) -> float:
    """mCi转换为Bq"""
    return value_mci * 3.7e7


def bq_to_mci(value_bq: float) -> float:
    """Bq转换为mCi"""
    return value_bq / 3.7e7


def mgy_to_ugy(value_mgy: float) -> float:
    """mGy转换为μGy"""
    return value_mgy * 1000.0


def ugy_to_mgy(value_ugy: float) -> float:
    """μGy转换为mGy"""
    return value_ugy / 1000.0


def decay_constant_per_second(half_life_days: float) -> float:
    """从半衰期（天）计算衰变常数 λ (s⁻¹)"""
    return 0.6931471805599453 / (half_life_days * 86400.0)


def time_integration_factor(half_life_days: float, irradiation_days: float) -> float:
    """
    计算时间积分因子 ∫₀ᵀ e^(-λt) dt = (1 - e^(-λT)) / λ

    Args:
        half_life_days: 核素半衰期（天）
        irradiation_days: 照射时间（天）

    Returns:
        积分因子（有效秒数）
    """
    import math
    lam = decay_constant_per_second(half_life_days)
    T = irradiation_days * 86400.0
    return (1.0 - math.exp(-lam * T)) / lam


# ============================================================================
# 默认值
# ============================================================================

class Defaults:
    """默认值"""

    # 籽源参数
    SEED_ACTIVITY = 3.0  # mCi
    SEED_SPACING = 10.0  # mm
    SEED_COUNT = 10
    IRRADIATION_TIME_DAYS = 90.0  # 默认照射时间（天），None = 永久植入

    # 计算参数
    GRID_RESOLUTION = 1.0  # mm
    GRID_SIZE = 32

    # 可视化参数
    COLORMAP = "viridis"
    ISODOSE_LEVELS = [50, 80, 90, 100]

    # 图像参数
    WINDOW_WIDTH = 400
    WINDOW_LEVEL = 40


# ============================================================================
# 错误消息
# ============================================================================

class ErrorMessages:
    """错误消息"""

    # 文件错误
    FILE_NOT_FOUND = "文件未找到: {path}"
    FILE_FORMAT_NOT_SUPPORTED = "不支持的文件格式: {format}"
    FILE_CORRUPTED = "文件损坏: {path}"

    # 计算错误
    CALCULATION_FAILED = "剂量计算失败: {reason}"
    INVALID_PARAMETERS = "无效的参数: {parameters}"
    INSUFFICIENT_MEMORY = "内存不足，无法完成计算"

    # 数据库错误
    DATABASE_CONNECTION_FAILED = "数据库连接失败"
    DATABASE_QUERY_FAILED = "数据库查询失败"

    # 用户界面错误
    INVALID_INPUT = "无效的输入: {field}"
    OPERATION_FAILED = "操作失败: {operation}"

    # 通用错误
    UNEXPECTED_ERROR = "发生未知错误: {error}"


# ============================================================================
# 成功消息
# ============================================================================

class SuccessMessages:
    """成功消息"""

    # 文件操作
    FILE_LOADED = "文件加载成功: {path}"
    FILE_SAVED = "文件保存成功: {path}"

    # 计算
    CALCULATION_COMPLETED = "剂量计算完成"
    CALCULATION_OPTIMIZED = "剂量计算优化完成"

    # 数据库
    DATABASE_CONNECTED = "数据库连接成功"
    DATABASE_INITIALIZED = "数据库初始化成功"

    # 用户界面
    OPERATION_COMPLETED = "操作完成: {operation}"


# ============================================================================
# 验证规则
# ============================================================================

class ValidationRules:
    """验证规则"""

    # 籽源参数
    MIN_SEED_ACTIVITY = 0.01  # mCi
    MAX_SEED_ACTIVITY = 100.0  # mCi

    MIN_SEED_SPACING = 0.5  # mm
    MAX_SEED_SPACING = 50.0  # mm

    MIN_SEED_COUNT = 1
    MAX_SEED_COUNT = 1000

    # 照射时间
    MIN_IRRADIATION_TIME = 1.0  # days
    MAX_IRRADIATION_TIME = 3650.0  # days (10 years)

    # 网格参数
    MIN_GRID_RESOLUTION = 0.1  # mm
    MAX_GRID_RESOLUTION = 10.0  # mm

    MIN_GRID_SIZE = 32
    MAX_GRID_SIZE = 1024

    # 剂量参数
    MIN_DOSE_VALUE = 0.0  # mGy
    MAX_DOSE_VALUE = 1e6  # mGy


# ============================================================================
# 导出
# ============================================================================

__all__ = [
    # 常量类
    "PhysicalConstants",
    "SeedConstants",
    "DoseConstants",
    "ImageConstants",
    "VisualizationConstants",
    "AppConstants",

    # 枚举
    "CalculationMethod",
    "SeedPlacementMode",
    "ViewMode",
    "DoseDisplayMode",

    # 单位转换函数
    "mm_to_cm",
    "cm_to_mm",
    "mbq_to_bq",
    "bq_to_mbq",
    "mci_to_bq",
    "bq_to_mci",
    "gy_to_cgy",
    "cgy_to_gy",
    "mgy_to_ugy",
    "ugy_to_mgy",
    "days_to_seconds",
    "seconds_to_days",
    "decay_constant_per_second",
    "time_integration_factor",

    # 默认值
    "Defaults",

    # 消息
    "ErrorMessages",
    "SuccessMessages",

    # 验证规则
    "ValidationRules",
]