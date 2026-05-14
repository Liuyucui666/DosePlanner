"""
籽源类型管理
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from .models import SeedType
from .repositories import SeedTypeRepository
from config.constants import SeedConstants


class SeedTypeManager:
    """籽源类型管理器"""

    def __init__(self, session: Session):
        self.session = session
        self.repository = SeedTypeRepository(session)

    def add_default_seed_types(self) -> List[SeedType]:
        """添加默认籽源类型"""
        default_seeds = []

        for seed_name, seed_data in SeedConstants.COMMON_SEED_TYPES.items():
            # 检查是否已存在
            existing = self.repository.get_by_name(seed_name)
            if existing:
                continue

            # 创建籽源类型
            seed_type_data = {
                "name": seed_name,
                "manufacturer": "Various",
                "model_number": f"{seed_name}-Standard",
                "energy_kev": seed_data["energy_kev"],
                "half_life_days": seed_data["half_life_days"],
                "dimensions_mm": {
                    "length": SeedConstants.TYPICAL_SEED_LENGTH,
                    "diameter": SeedConstants.TYPICAL_SEED_DIAMETER,
                },
                "description": f"Standard {seed_name} seed for brachytherapy",
                "is_active": True,
            }

            seed_type = self.repository.create(seed_type_data)
            default_seeds.append(seed_type)

        return default_seeds

    def get_seed_type(self, seed_type_id: int) -> Optional[SeedType]:
        """获取籽源类型"""
        return self.repository.get(seed_type_id)

    def get_seed_type_by_name(self, name: str) -> Optional[SeedType]:
        """根据名称获取籽源类型"""
        return self.repository.get_by_name(name)

    def get_all_seed_types(self, active_only: bool = True) -> List[SeedType]:
        """获取所有籽源类型"""
        return self.repository.get_all(active_only)

    def create_seed_type(self, seed_type_data: Dict[str, Any]) -> SeedType:
        """创建籽源类型"""
        # 验证必需字段
        required_fields = ["name", "energy_kev", "half_life_days"]
        for field in required_fields:
            if field not in seed_type_data:
                raise ValueError(f"Missing required field: {field}")

        # 设置默认值
        if "dimensions_mm" not in seed_type_data:
            seed_type_data["dimensions_mm"] = {
                "length": SeedConstants.TYPICAL_SEED_LENGTH,
                "diameter": SeedConstants.TYPICAL_SEED_DIAMETER,
            }

        if "is_active" not in seed_type_data:
            seed_type_data["is_active"] = True

        return self.repository.create(seed_type_data)

    def update_seed_type(
        self, seed_type_id: int, update_data: Dict[str, Any]
    ) -> Optional[SeedType]:
        """更新籽源类型"""
        return self.repository.update(seed_type_id, update_data)

    def delete_seed_type(self, seed_type_id: int) -> bool:
        """删除籽源类型（软删除）"""
        return self.repository.delete(seed_type_id)

    def search_seed_types(self, search_term: str, active_only: bool = True) -> List[SeedType]:
        """搜索籽源类型"""
        return self.repository.search(search_term, active_only)

    def get_seed_types_by_energy(
        self, min_energy: float, max_energy: float, active_only: bool = True
    ) -> List[SeedType]:
        """根据能量范围获取籽源类型"""
        return self.repository.get_by_energy_range(min_energy, max_energy, active_only)

    def validate_seed_type_data(self, seed_type_data: Dict[str, Any]) -> List[str]:
        """验证籽源类型数据"""
        errors = []

        # 验证名称
        name = seed_type_data.get("name")
        if not name or not isinstance(name, str) or len(name.strip()) == 0:
            errors.append("Name is required and must be a non-empty string")

        # 验证能量
        energy_kev = seed_type_data.get("energy_kev")
        if energy_kev is None:
            errors.append("Energy (keV) is required")
        elif not isinstance(energy_kev, (int, float)) or energy_kev <= 0:
            errors.append("Energy (keV) must be a positive number")

        # 验证半衰期
        half_life_days = seed_type_data.get("half_life_days")
        if half_life_days is None:
            errors.append("Half-life (days) is required")
        elif not isinstance(half_life_days, (int, float)) or half_life_days <= 0:
            errors.append("Half-life (days) must be a positive number")

        # 验证尺寸
        dimensions_mm = seed_type_data.get("dimensions_mm")
        if dimensions_mm is not None:
            if not isinstance(dimensions_mm, dict):
                errors.append("Dimensions must be a dictionary")
            else:
                required_dimensions = ["length", "diameter"]
                for dim in required_dimensions:
                    if dim not in dimensions_mm:
                        errors.append(f"Dimensions must contain '{dim}'")
                    else:
                        value = dimensions_mm[dim]
                        if not isinstance(value, (int, float)) or value <= 0:
                            errors.append(f"Dimension '{dim}' must be a positive number")

        return errors

    def get_seed_type_info(self, seed_type_id: int) -> Optional[Dict[str, Any]]:
        """获取籽源类型详细信息"""
        seed_type = self.get_seed_type(seed_type_id)
        if not seed_type:
            return None

        info = seed_type.to_dict()

        # 添加计算信息
        info["decay_constant"] = self.calculate_decay_constant(seed_type.half_life_days)
        info["typical_activity_mbq"] = SeedConstants.COMMON_SEED_TYPES.get(
            seed_type.name, {}
        ).get("typical_activity_mbq", 100.0)

        return info

    @staticmethod
    def calculate_decay_constant(half_life_days: float) -> float:
        """计算衰变常数（每天）"""
        import math

        # λ = ln(2) / T½
        return math.log(2) / half_life_days

    @staticmethod
    def calculate_activity_at_time(
        initial_activity: float, half_life_days: float, time_days: float
    ) -> float:
        """计算指定时间后的活度"""
        import math

        # A = A₀ * e^(-λt)
        decay_constant = math.log(2) / half_life_days
        return initial_activity * math.exp(-decay_constant * time_days)

    def get_seed_type_summary(self) -> Dict[str, Any]:
        """获取籽源类型摘要"""
        seed_types = self.get_all_seed_types(active_only=True)

        summary = {
            "total_count": len(seed_types),
            "by_manufacturer": {},
            "energy_range": {"min": float("inf"), "max": float("-inf")},
            "half_life_range": {"min": float("inf"), "max": float("-inf")},
        }

        for seed_type in seed_types:
            # 按制造商统计
            manufacturer = seed_type.manufacturer or "Unknown"
            summary["by_manufacturer"][manufacturer] = (
                summary["by_manufacturer"].get(manufacturer, 0) + 1
            )

            # 能量范围
            summary["energy_range"]["min"] = min(
                summary["energy_range"]["min"], seed_type.energy_kev
            )
            summary["energy_range"]["max"] = max(
                summary["energy_range"]["max"], seed_type.energy_kev
            )

            # 半衰期范围
            summary["half_life_range"]["min"] = min(
                summary["half_life_range"]["min"], seed_type.half_life_days
            )
            summary["half_life_range"]["max"] = max(
                summary["half_life_range"]["max"], seed_type.half_life_days
            )

        # 处理无穷大值
        if summary["energy_range"]["min"] == float("inf"):
            summary["energy_range"]["min"] = 0
        if summary["energy_range"]["max"] == float("-inf"):
            summary["energy_range"]["max"] = 0
        if summary["half_life_range"]["min"] == float("inf"):
            summary["half_life_range"]["min"] = 0
        if summary["half_life_range"]["max"] == float("-inf"):
            summary["half_life_range"]["max"] = 0

        return summary