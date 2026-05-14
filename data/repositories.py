"""
数据访问层（仓库模式）
"""

from typing import List, Optional, Dict, Any
from datetime import date, datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc

from .models import SeedType, MonteCarloResult, TreatmentPlan, UserSettings


class BaseRepository:
    """基础仓库类"""

    def __init__(self, session: Session):
        self.session = session


class SeedTypeRepository(BaseRepository):
    """籽源类型仓库"""

    def get(self, seed_type_id: int) -> Optional[SeedType]:
        """根据ID获取籽源类型"""
        return self.session.query(SeedType).filter(SeedType.id == seed_type_id).first()

    def get_by_name(self, name: str) -> Optional[SeedType]:
        """根据名称获取籽源类型"""
        return self.session.query(SeedType).filter(SeedType.name == name).first()

    def get_all(self, active_only: bool = True) -> List[SeedType]:
        """获取所有籽源类型"""
        query = self.session.query(SeedType)
        if active_only:
            query = query.filter(SeedType.is_active == True)
        return query.order_by(SeedType.name).all()

    def get_by_energy_range(
        self, min_energy: float, max_energy: float, active_only: bool = True
    ) -> List[SeedType]:
        """根据能量范围获取籽源类型"""
        query = self.session.query(SeedType).filter(
            and_(
                SeedType.energy_kev >= min_energy,
                SeedType.energy_kev <= max_energy,
            )
        )
        if active_only:
            query = query.filter(SeedType.is_active == True)
        return query.order_by(SeedType.energy_kev).all()

    def create(self, seed_type_data: Dict[str, Any]) -> SeedType:
        """创建籽源类型"""
        seed_type = SeedType(**seed_type_data)
        self.session.add(seed_type)
        self.session.flush()
        return seed_type

    def update(self, seed_type_id: int, update_data: Dict[str, Any]) -> Optional[SeedType]:
        """更新籽源类型"""
        seed_type = self.get(seed_type_id)
        if not seed_type:
            return None

        for key, value in update_data.items():
            if hasattr(seed_type, key):
                setattr(seed_type, key, value)

        seed_type.updated_at = datetime.utcnow()
        self.session.flush()
        return seed_type

    def delete(self, seed_type_id: int) -> bool:
        """删除籽源类型（软删除）"""
        seed_type = self.get(seed_type_id)
        if not seed_type:
            return False

        seed_type.is_active = False
        seed_type.updated_at = datetime.utcnow()
        self.session.flush()
        return True

    def search(self, search_term: str, active_only: bool = True) -> List[SeedType]:
        """搜索籽源类型"""
        query = self.session.query(SeedType).filter(
            or_(
                SeedType.name.ilike(f"%{search_term}%"),
                SeedType.manufacturer.ilike(f"%{search_term}%"),
                SeedType.model_number.ilike(f"%{search_term}%"),
                SeedType.description.ilike(f"%{search_term}%"),
            )
        )
        if active_only:
            query = query.filter(SeedType.is_active == True)
        return query.order_by(SeedType.name).all()


class MonteCarloResultRepository(BaseRepository):
    """蒙特卡洛计算结果仓库"""

    def get(self, result_id: int) -> Optional[MonteCarloResult]:
        """根据ID获取蒙特卡洛结果"""
        return (
            self.session.query(MonteCarloResult)
            .filter(MonteCarloResult.id == result_id)
            .first()
        )

    def get_by_seed_type(
        self, seed_type_id: int, verified_only: bool = True
    ) -> List[MonteCarloResult]:
        """根据籽源类型获取蒙特卡洛结果"""
        query = self.session.query(MonteCarloResult).filter(
            MonteCarloResult.seed_type_id == seed_type_id
        )
        if verified_only:
            query = query.filter(MonteCarloResult.is_verified == True)
        return query.order_by(desc(MonteCarloResult.resolution_mm)).all()

    def get_by_resolution(
        self, seed_type_id: int, resolution_mm: float, verified_only: bool = True
    ) -> Optional[MonteCarloResult]:
        """根据籽源类型和分辨率获取蒙特卡洛结果"""
        query = self.session.query(MonteCarloResult).filter(
            and_(
                MonteCarloResult.seed_type_id == seed_type_id,
                MonteCarloResult.resolution_mm == resolution_mm,
            )
        )
        if verified_only:
            query = query.filter(MonteCarloResult.is_verified == True)
        return query.first()

    def get_closest_resolution(
        self, seed_type_id: int, target_resolution_mm: float, verified_only: bool = True
    ) -> Optional[MonteCarloResult]:
        """获取最接近目标分辨率的蒙特卡洛结果"""
        query = self.session.query(MonteCarloResult).filter(
            MonteCarloResult.seed_type_id == seed_type_id
        )
        if verified_only:
            query = query.filter(MonteCarloResult.is_verified == True)

        results = query.all()
        if not results:
            return None

        # 找到分辨率最接近的结果
        closest_result = min(
            results,
            key=lambda r: abs(r.resolution_mm - target_resolution_mm),
        )
        return closest_result

    def get_all(self, verified_only: bool = True) -> List[MonteCarloResult]:
        """获取所有蒙特卡洛结果"""
        query = self.session.query(MonteCarloResult)
        if verified_only:
            query = query.filter(MonteCarloResult.is_verified == True)
        return query.order_by(desc(MonteCarloResult.calculation_date)).all()

    def create(self, result_data: Dict[str, Any]) -> MonteCarloResult:
        """创建蒙特卡洛结果"""
        result = MonteCarloResult(**result_data)
        self.session.add(result)
        self.session.flush()
        return result

    def update(self, result_id: int, update_data: Dict[str, Any]) -> Optional[MonteCarloResult]:
        """更新蒙特卡洛结果"""
        result = self.get(result_id)
        if not result:
            return None

        for key, value in update_data.items():
            if hasattr(result, key):
                setattr(result, key, value)

        self.session.flush()
        return result

    def delete(self, result_id: int) -> bool:
        """删除蒙特卡洛结果"""
        result = self.get(result_id)
        if not result:
            return False

        self.session.delete(result)
        self.session.flush()
        return True

    def verify(self, result_id: int) -> bool:
        """验证蒙特卡洛结果"""
        result = self.get(result_id)
        if not result:
            return False

        result.is_verified = True
        self.session.flush()
        return True


class TreatmentPlanRepository(BaseRepository):
    """治疗计划仓库"""

    def get(self, plan_id: int) -> Optional[TreatmentPlan]:
        """根据ID获取治疗计划"""
        return (
            self.session.query(TreatmentPlan).filter(TreatmentPlan.id == plan_id).first()
        )

    def get_by_patient(self, patient_id: str) -> List[TreatmentPlan]:
        """根据患者ID获取治疗计划"""
        return (
            self.session.query(TreatmentPlan)
            .filter(TreatmentPlan.patient_id == patient_id)
            .order_by(desc(TreatmentPlan.created_at))
            .all()
        )

    def get_by_name(self, plan_name: str) -> Optional[TreatmentPlan]:
        """根据计划名称获取治疗计划"""
        return (
            self.session.query(TreatmentPlan)
            .filter(TreatmentPlan.plan_name == plan_name)
            .first()
        )

    def get_all(self, finalized_only: bool = False) -> List[TreatmentPlan]:
        """获取所有治疗计划"""
        query = self.session.query(TreatmentPlan)
        if finalized_only:
            query = query.filter(TreatmentPlan.is_finalized == True)
        return query.order_by(desc(TreatmentPlan.created_at)).all()

    def create(self, plan_data: Dict[str, Any]) -> TreatmentPlan:
        """创建治疗计划"""
        plan = TreatmentPlan(**plan_data)
        self.session.add(plan)
        self.session.flush()
        return plan

    def update(self, plan_id: int, update_data: Dict[str, Any]) -> Optional[TreatmentPlan]:
        """更新治疗计划"""
        plan = self.get(plan_id)
        if not plan:
            return None

        for key, value in update_data.items():
            if hasattr(plan, key):
                setattr(plan, key, value)

        plan.updated_at = datetime.utcnow()
        self.session.flush()
        return plan

    def delete(self, plan_id: int) -> bool:
        """删除治疗计划"""
        plan = self.get(plan_id)
        if not plan:
            return False

        self.session.delete(plan)
        self.session.flush()
        return True

    def finalize(self, plan_id: int) -> bool:
        """最终化治疗计划"""
        plan = self.get(plan_id)
        if not plan:
            return False

        plan.is_finalized = True
        plan.updated_at = datetime.utcnow()
        self.session.flush()
        return True

    def duplicate(self, plan_id: int, new_plan_name: str) -> Optional[TreatmentPlan]:
        """复制治疗计划"""
        original_plan = self.get(plan_id)
        if not original_plan:
            return None

        # 创建新计划数据
        new_plan_data = {
            "plan_name": new_plan_name,
            "patient_id": original_plan.patient_id,
            "patient_name": original_plan.patient_name,
            "ct_image_path": original_plan.ct_image_path,
            "seed_positions": original_plan.seed_positions.copy()
            if original_plan.seed_positions
            else [],
            "dvh_data": original_plan.dvh_data.copy() if original_plan.dvh_data else None,
            "calculation_parameters": (
                original_plan.calculation_parameters.copy()
                if original_plan.calculation_parameters
                else None
            ),
            "notes": f"复制自: {original_plan.plan_name}\n{original_plan.notes or ''}",
            "is_finalized": False,
        }

        return self.create(new_plan_data)

    def search(
        self,
        search_term: str,
        finalized_only: bool = False,
    ) -> List[TreatmentPlan]:
        """搜索治疗计划"""
        query = self.session.query(TreatmentPlan).filter(
            or_(
                TreatmentPlan.plan_name.ilike(f"%{search_term}%"),
                TreatmentPlan.patient_id.ilike(f"%{search_term}%"),
                TreatmentPlan.patient_name.ilike(f"%{search_term}%"),
                TreatmentPlan.notes.ilike(f"%{search_term}%"),
            )
        )
        if finalized_only:
            query = query.filter(TreatmentPlan.is_finalized == True)
        return query.order_by(desc(TreatmentPlan.created_at)).all()


class UserSettingsRepository(BaseRepository):
    """用户设置仓库"""

    def get(self, user_id: str) -> Optional[UserSettings]:
        """根据用户ID获取用户设置"""
        return (
            self.session.query(UserSettings)
            .filter(UserSettings.user_id == user_id)
            .first()
        )

    def get_all(self) -> List[UserSettings]:
        """获取所有用户设置"""
        return self.session.query(UserSettings).order_by(UserSettings.user_id).all()

    def create_or_update(self, user_id: str, settings: Dict[str, Any]) -> UserSettings:
        """创建或更新用户设置"""
        user_settings = self.get(user_id)

        if user_settings:
            # 更新现有设置
            user_settings.settings = settings
            user_settings.updated_at = datetime.utcnow()
        else:
            # 创建新设置
            user_settings = UserSettings(user_id=user_id, settings=settings)
            self.session.add(user_settings)

        self.session.flush()
        return user_settings

    def update_settings(self, user_id: str, update_data: Dict[str, Any]) -> Optional[UserSettings]:
        """更新用户设置（部分更新）"""
        user_settings = self.get(user_id)
        if not user_settings:
            return None

        # 合并设置
        current_settings = user_settings.settings or {}
        current_settings.update(update_data)
        user_settings.settings = current_settings
        user_settings.updated_at = datetime.utcnow()

        self.session.flush()
        return user_settings

    def delete(self, user_id: str) -> bool:
        """删除用户设置"""
        user_settings = self.get(user_id)
        if not user_settings:
            return False

        self.session.delete(user_settings)
        self.session.flush()
        return True

    def get_setting(self, user_id: str, key: str, default=None) -> Any:
        """获取特定设置值"""
        user_settings = self.get(user_id)
        if not user_settings or not user_settings.settings:
            return default

        return user_settings.settings.get(key, default)


# 导出所有仓库
__all__ = [
    "BaseRepository",
    "SeedTypeRepository",
    "MonteCarloResultRepository",
    "TreatmentPlanRepository",
    "UserSettingsRepository",
]