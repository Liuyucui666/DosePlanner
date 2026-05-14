"""
数据库模型定义
"""

from datetime import datetime, date
from typing import Optional, Dict, Any, List
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Text,
    Date,
    DateTime,
    ForeignKey,
    JSON,
    LargeBinary,
    Boolean,
)
from sqlalchemy.orm import relationship, validates
from sqlalchemy.ext.mutable import MutableDict, MutableList

from .database import Base


class SeedType(Base):
    """籽源类型模型"""

    __tablename__ = "seed_types"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False, unique=True, index=True)
    manufacturer = Column(String(100))
    model_number = Column(String(50))
    energy_kev = Column(Float, nullable=False)  # 平均能量 (keV)
    half_life_days = Column(Float, nullable=False)  # 半衰期 (天)
    dimensions_mm = Column(MutableDict.as_mutable(JSON))  # 尺寸信息
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    monte_carlo_results = relationship(
        "MonteCarloResult", back_populates="seed_type", cascade="all, delete-orphan"
    )

    @validates("energy_kev", "half_life_days")
    def validate_positive_values(self, key, value):
        """验证正值"""
        if value <= 0:
            raise ValueError(f"{key} 必须是正值")
        return value

    @validates("dimensions_mm")
    def validate_dimensions(self, key, value):
        """验证尺寸信息"""
        if not isinstance(value, dict):
            raise ValueError("dimensions_mm 必须是字典")

        required_keys = ["length", "diameter"]
        for req_key in required_keys:
            if req_key not in value:
                raise ValueError(f"dimensions_mm 必须包含 '{req_key}' 键")

        return value

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "manufacturer": self.manufacturer,
            "model_number": self.model_number,
            "energy_kev": self.energy_kev,
            "half_life_days": self.half_life_days,
            "dimensions_mm": self.dimensions_mm,
            "description": self.description,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class MonteCarloResult(Base):
    """蒙特卡洛计算结果模型"""

    __tablename__ = "monte_carlo_results"

    id = Column(Integer, primary_key=True, index=True)
    seed_type_id = Column(Integer, ForeignKey("seed_types.id"), nullable=False, index=True)
    resolution_mm = Column(Float, nullable=False)  # 空间分辨率 (mm)
    grid_size_r = Column(Integer, nullable=False)  # R方向（径向）网格点数
    grid_size_z = Column(Integer, nullable=False)  # Z方向（轴向）网格点数
    r_max = Column(Float, nullable=False)  # 径向最大距离 (mm)
    z_min = Column(Float, nullable=False)  # 轴向最小距离 (mm)，通常为负值
    z_max = Column(Float, nullable=False)  # 轴向最大距离 (mm)，通常为正值
    data_format = Column(String(10), default="npy")  # 数据格式: 'npy', 'h5'
    data_path = Column(Text, nullable=False)  # 数据文件路径
    dose_unit = Column(String(10), default="mGy")  # 剂量单位
    dose_per_decay = Column(Float, nullable=False)  # 每次衰变的剂量
    calculation_date = Column(Date, default=date.today)
    description = Column(Text)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    seed_type = relationship("SeedType", back_populates="monte_carlo_results")

    @validates("resolution_mm")
    def validate_resolution(self, key, value):
        """验证分辨率"""
        if value <= 0:
            raise ValueError("resolution_mm 必须是正值")
        return value

    @validates("grid_size_r", "grid_size_z")
    def validate_grid_size(self, key, value):
        """验证网格大小"""
        if value <= 0:
            raise ValueError(f"{key} 必须是正值")
        if value > 4096:
            raise ValueError(f"{key} 不能超过 4096")
        return value

    @validates("r_max", "z_min", "z_max")
    def validate_range(self, key, value):
        """验证范围参数"""
        if not isinstance(value, (int, float)):
            raise ValueError(f"{key} 必须是数值")
        return float(value)

    @validates("dose_per_decay")
    def validate_dose_per_decay(self, key, value):
        """验证每次衰变的剂量"""
        if value <= 0:
            raise ValueError("dose_per_decay 必须是正值")
        return value

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "seed_type_id": self.seed_type_id,
            "resolution_mm": self.resolution_mm,
            "grid_size_r": self.grid_size_r,
            "grid_size_z": self.grid_size_z,
            "r_max": self.r_max,
            "z_min": self.z_min,
            "z_max": self.z_max,
            "data_format": self.data_format,
            "data_path": self.data_path,
            "dose_unit": self.dose_unit,
            "dose_per_decay": self.dose_per_decay,
            "calculation_date": (
                self.calculation_date.isoformat() if self.calculation_date else None
            ),
            "description": self.description,
            "is_verified": self.is_verified,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class TreatmentPlan(Base):
    """治疗计划模型"""

    __tablename__ = "treatment_plans"

    id = Column(Integer, primary_key=True, index=True)
    plan_name = Column(String(100), nullable=False, index=True)
    patient_id = Column(String(50), index=True)
    patient_name = Column(String(100))
    ct_image_path = Column(Text)  # CT图像文件路径
    seed_positions = Column(MutableList.as_mutable(JSON), default=list)  # 籽源位置列表
    total_dose_data = Column(LargeBinary)  # 总剂量分布数据（压缩的）
    dvh_data = Column(JSON)  # DVH数据
    calculation_parameters = Column(JSON)  # 计算参数
    notes = Column(Text)
    is_finalized = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @validates("seed_positions")
    def validate_seed_positions(self, key, value):
        """验证籽源位置"""
        if not isinstance(value, list):
            raise ValueError("seed_positions 必须是列表")

        for i, seed in enumerate(value):
            if not isinstance(seed, dict):
                raise ValueError(f"籽源 {i} 必须是字典")

            required_keys = ["position", "orientation", "seed_type_id", "activity"]
            for req_key in required_keys:
                if req_key not in seed:
                    raise ValueError(f"籽源 {i} 缺少 '{req_key}' 键")

            # 验证位置和方向
            position = seed["position"]
            orientation = seed["orientation"]

            if not isinstance(position, list) or len(position) != 3:
                raise ValueError(f"籽源 {i} 的 position 必须是包含3个值的列表")

            if not isinstance(orientation, list) or len(orientation) != 3:
                raise ValueError(f"籽源 {i} 的 orientation 必须是包含3个值的列表")

        return value

    @validates("calculation_parameters")
    def validate_calculation_parameters(self, key, value):
        """验证计算参数"""
        if not isinstance(value, dict):
            raise ValueError("calculation_parameters 必须是字典")
        return value

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "plan_name": self.plan_name,
            "patient_id": self.patient_id,
            "patient_name": self.patient_name,
            "ct_image_path": self.ct_image_path,
            "seed_positions": self.seed_positions,
            "dvh_data": self.dvh_data,
            "calculation_parameters": self.calculation_parameters,
            "notes": self.notes,
            "is_finalized": self.is_finalized,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class UserSettings(Base):
    """用户设置模型"""

    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(50), unique=True, index=True)
    settings = Column(MutableDict.as_mutable(JSON), default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "settings": self.settings,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# 导出所有模型
__all__ = [
    "Base",
    "SeedType",
    "MonteCarloResult",
    "TreatmentPlan",
    "UserSettings",
]