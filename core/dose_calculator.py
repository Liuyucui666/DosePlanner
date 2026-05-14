"""
剂量计算引擎

基于蒙特卡洛预计算的R-Z柱坐标系剂量表（FLUKA 模拟结果，单位 GeV/g/primary），
根据籽源位置和方向，通过投影查表叠加所有籽源得到总剂量分布。

物理模型：
  - FLUKA 剂量表: GeV/g/primary
  - 转换: 1 GeV/g = 1.602e-4 mGy
  - 活度: mCi → Bq (×3.7e7)
  - 时间积分: 考虑核素指数衰变 ∫₀ᵀ A₀·e^(-λt) dt

剂量单位: mGy
剂量率单位: μGy/h
"""

import math
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from data.repositories import MonteCarloResultRepository, SeedTypeRepository
from data.database import get_session
from utils.file_io import load_npy_data
from config.constants import PhysicalConstants


class DoseCalculator:
    """剂量计算器（R-Z柱坐标查表法 + 衰变时间积分）"""

    def __init__(self, db_session=None):
        """
        初始化剂量计算器

        Args:
            db_session: 数据库会话
        """
        self.session = db_session or get_session()
        self.mc_repository = MonteCarloResultRepository(self.session)
        self.seed_type_repository = SeedTypeRepository(self.session)
        self._half_life_cache = {}  # seed_type_id → half_life_days

    def _get_half_life(self, seed_type_id: int) -> float:
        """获取核素半衰期（天），带缓存"""
        if seed_type_id not in self._half_life_cache:
            st = self.seed_type_repository.get(seed_type_id)
            if st is not None:
                self._half_life_cache[seed_type_id] = st.half_life_days
            else:
                self._half_life_cache[seed_type_id] = 59.4  # 默认 I-125
        return self._half_life_cache[seed_type_id]

    def _compute_physics_scale(
        self,
        activity_mCi: float,
        half_life_days: float,
        irradiation_time_days: Optional[float],
    ) -> float:
        """
        计算单个籽源的物理缩放因子

        将 FLUKA 插值结果（GeV/g/primary）转换为 mGy 总积分剂量:

            scale = GEV_PER_G_TO_mGy × A₀_Bq × ∫₀ᵀ e^(-λt) dt

        Args:
            activity_mCi: 初始活度 (mCi)
            half_life_days: 核素半衰期 (天)
            irradiation_time_days: 照射时间 (天)，None 表示永久植入 (T→∞)

        Returns:
            物理缩放因子
        """
        # FLUKA GeV/g/primary → mGy/primary
        gev_to_mgy = PhysicalConstants.GEV_PER_G_TO_mGy

        # 活度 mCi → Bq (decays/s)
        A0_Bq = activity_mCi * PhysicalConstants.MCi_TO_Bq

        # 衰变常数 λ (s⁻¹)
        lam = PhysicalConstants.LN2 / (half_life_days * PhysicalConstants.DAYS_TO_SECONDS)

        # 时间积分因子 (s)
        if irradiation_time_days is None:
            # 永久植入：T → ∞，∫ = 1/λ
            time_factor = 1.0 / lam
        else:
            T_s = irradiation_time_days * PhysicalConstants.DAYS_TO_SECONDS
            time_factor = (1.0 - math.exp(-lam * T_s)) / lam

        return gev_to_mgy * A0_Bq * time_factor

    def calculate_total_dose(
        self,
        seeds: List[Dict[str, Any]],
        grid_resolution: float = 1.0,
        grid_size: int = 32,
        mc_data_override: Optional[Dict[str, Any]] = None,
        progress_callback=None,
        ct_grid: Optional[Dict[str, Any]] = None,
        irradiation_time_days: Optional[float] = None,
    ) -> Tuple[np.ndarray, Tuple[float, float, float], np.ndarray]:
        """
        计算总剂量分布（mGy）和 T0 剂量率分布（μGy/h）

        Args:
            seeds: 籽源列表，每籽源含 position, orientation, seed_type_id, activity(mCi)
            grid_resolution: 网格分辨率 (mm)，无CT时使用
            grid_size: 网格大小，无CT时使用
            mc_data_override: 可选，直接传入MC数据字典（用于测试）
            progress_callback: 进度回调 callable(completed, total)
            ct_grid: 可选，CT网格参数 {"origin": (ox,oy,oz), "spacing": (sx,sy,sz), "shape": (nx,ny,nz)}
            irradiation_time_days: 照射时间（天），None=永久植入

        Returns:
            total_dose: 总剂量分布 (3D NumPy数组, mGy)
            grid_origin: 网格原点坐标
            dose_rate: T0剂量率分布 (3D NumPy数组, μGy/h)
        """
        if not seeds:
            if ct_grid:
                z = np.zeros(ct_grid["shape"], dtype=np.float32)
                return z, ct_grid["origin"], z.copy()
            z = np.zeros((grid_size, grid_size, grid_size), dtype=np.float32)
            return z, (0, 0, 0), z.copy()

        if mc_data_override is not None:
            mc_data = mc_data_override
            half_life_days = mc_data.get("half_life_days", 59.4)
        else:
            mc_data = self._load_mc_data(seeds[0]["seed_type_id"], grid_resolution)
            if mc_data is None:
                if ct_grid:
                    z = np.zeros(ct_grid["shape"], dtype=np.float32)
                    return z, ct_grid["origin"], z.copy()
                z = np.zeros((grid_size, grid_size, grid_size), dtype=np.float32)
                return z, (0, 0, 0), z.copy()
            half_life_days = self._get_half_life(seeds[0]["seed_type_id"])

        mc_extent = max(mc_data["r_max"], abs(mc_data["z_min"]), abs(mc_data["z_max"]))
        positions = np.array([seed["position"] for seed in seeds])

        time_factor = self._get_time_factor(half_life_days, irradiation_time_days)

        if ct_grid is not None:
            # --- CT 对齐模式：每籽源独立子 ROI，累加到全零 CT 网格 ---
            grid_origin = tuple(ct_grid["origin"])  # SimpleITK: (ox, oy, oz) in (x,y,z)
            ct_spacing_itk = ct_grid["spacing"]     # SimpleITK: (sx, sy, sz)
            ct_shape_np = np.array(ct_grid["shape"], dtype=np.int32)  # numpy: (nz, ny, nx)

            sx, sy, sz = float(ct_spacing_itk[0]), float(ct_spacing_itk[1]), float(ct_spacing_itk[2])
            ox, oy, oz = float(grid_origin[0]), float(grid_origin[1]), float(grid_origin[2])
            nz, ny, nx = int(ct_shape_np[0]), int(ct_shape_np[1]), int(ct_shape_np[2])

            ct_origin_arr = np.array([ox, oy, oz], dtype=np.float32)
            ct_max_w = np.array([ox + nx * sx, oy + ny * sy, oz + nz * sz], dtype=np.float32)

            full = np.zeros((nz, ny, nx), dtype=np.float32)
            dose_rate = np.zeros_like(full)
            interpolator = self._build_interpolator(mc_data)

            for idx, seed in enumerate(seeds):
                seed_pos = np.array(seed["position"], dtype=np.float32)

                # 该籽源的子 ROI（仅 MC 数据覆盖范围），坐标均为 (x, y, z) 序
                seed_roi_min = np.maximum(seed_pos - mc_extent, ct_origin_arr)
                seed_roi_max = np.minimum(seed_pos + mc_extent, ct_max_w)

                sv_xyz_min = np.floor((seed_roi_min - ct_origin_arr) / [sx, sy, sz]).astype(np.int32)
                sv_xyz_max = np.ceil((seed_roi_max - ct_origin_arr) / [sx, sy, sz]).astype(np.int32)
                sv_xyz_min = np.maximum(sv_xyz_min, 0)
                sv_xyz_max = np.minimum(sv_xyz_max, [nx, ny, nz])

                # 转为 numpy 轴序 (z, y, x)
                sv_min = np.array([sv_xyz_min[2], sv_xyz_min[1], sv_xyz_min[0]], dtype=np.int32)
                sv_max = np.array([sv_xyz_max[2], sv_xyz_max[1], sv_xyz_max[0]], dtype=np.int32)

                if np.any(sv_max <= sv_min):
                    continue

                i, j, k = np.mgrid[sv_min[0]:sv_max[0],   # z
                                   sv_min[1]:sv_max[1],   # y
                                   sv_min[2]:sv_max[2]]   # x

                # 组装世界坐标 (x, y, z) 列
                seed_coords = np.stack([
                    k * sx + ox,   # x
                    j * sy + oy,   # y
                    i * sz + oz,   # z
                ], axis=-1).astype(np.float32).reshape(-1, 3)

                contrib = self._compute_seed_contribution(
                    seed, seed_coords, mc_data, interpolator,
                    half_life_days, irradiation_time_days,
                )
                sub_shape = tuple(sv_max - sv_min)
                contrib_2d = contrib.reshape(sub_shape).astype(np.float32)
                full[sv_min[0]:sv_max[0],
                     sv_min[1]:sv_max[1],
                     sv_min[2]:sv_max[2]] += contrib_2d
                dose_rate[sv_min[0]:sv_max[0],
                          sv_min[1]:sv_max[1],
                          sv_min[2]:sv_max[2]] += contrib_2d / time_factor * 3600.0 * 1000.0

                if progress_callback:
                    progress_callback(idx + 1, len(seeds))

            return full, grid_origin, dose_rate

        else:
            # --- 无 CT 模式：自动计算网格 ---
            min_pos = positions.min(axis=0) - mc_extent - grid_resolution
            max_pos = positions.max(axis=0) + mc_extent + grid_resolution

            actual_range = max_pos - min_pos
            needed_size = int(np.ceil(actual_range.max() / grid_resolution))
            grid_size = max(grid_size, needed_size)
            grid_origin = tuple(min_pos)

            i, j, k = np.mgrid[0:grid_size, 0:grid_size, 0:grid_size]
            world_coords_flat = (
                np.stack([i, j, k], axis=-1).astype(np.float32) * grid_resolution
                + np.array(grid_origin, dtype=np.float32)
            ).reshape(-1, 3)

            interpolator = self._build_interpolator(mc_data)
            total_dose = np.zeros(world_coords_flat.shape[0], dtype=np.float64)
            for idx, seed in enumerate(seeds):
                total_dose += self._compute_seed_contribution(
                    seed, world_coords_flat, mc_data, interpolator,
                    half_life_days, irradiation_time_days,
                )
                if progress_callback:
                    progress_callback(idx + 1, len(seeds))
            total_dose = total_dose.reshape(grid_size, grid_size, grid_size).astype(np.float32)
            dose_rate = total_dose / time_factor * 3600.0 * 1000.0
            return total_dose, grid_origin, dose_rate

    def _get_time_factor(
        self, half_life_days: float, irradiation_time_days: Optional[float]
    ) -> float:
        """计算时间积分因子 (s)"""
        lam = PhysicalConstants.LN2 / (half_life_days * PhysicalConstants.DAYS_TO_SECONDS)
        if irradiation_time_days is None:
            return 1.0 / lam
        T_s = irradiation_time_days * PhysicalConstants.DAYS_TO_SECONDS
        return (1.0 - math.exp(-lam * T_s)) / lam

    def _compute_seed_contribution(
        self,
        seed: Dict[str, Any],
        world_coords_flat: np.ndarray,
        mc_data: Dict[str, Any],
        interpolator,
        half_life_days: float = 59.4,
        irradiation_time_days: Optional[float] = None,
    ) -> np.ndarray:
        """
        计算单个籽源对所有体素的剂量贡献 (mGy)

        物理流程：
            1. 世界坐标 → (R, Z) 柱坐标投影
            2. 插值 FLUKA 剂量表 → GeV/g/primary
            3. × 物理缩放因子 → mGy 总积分剂量

        Args:
            seed: 籽源字典 {position, orientation, seed_type_id, activity(mCi)}
            world_coords_flat: 世界坐标数组 (M, 3)
            mc_data: MC数据字典
            interpolator: RegularGridInterpolator
            half_life_days: 核素半衰期 (天)
            irradiation_time_days: 照射时间 (天), None=永久植入

        Returns:
            dose_contribution: 剂量贡献 (M,) in mGy
        """
        pos = np.array(seed["position"], dtype=np.float64)
        direction = np.array(seed["orientation"], dtype=np.float64)
        direction_norm = np.linalg.norm(direction)
        if direction_norm < 1e-10:
            direction = np.array([0.0, 0.0, 1.0])
        else:
            direction = direction / direction_norm

        V = world_coords_flat - pos
        Z = np.dot(V, direction)
        V_sq = np.sum(V * V, axis=1)
        R_sq = V_sq - Z * Z
        np.maximum(R_sq, 0.0, out=R_sq)
        R = np.sqrt(R_sq)

        r_max = mc_data["r_max"]
        z_min = mc_data["z_min"]
        z_max = mc_data["z_max"]
        mask_in = (R <= r_max) & (Z >= z_min) & (Z <= z_max)

        contrib = np.zeros(V.shape[0], dtype=np.float64)

        if mask_in.any():
            points = np.column_stack([R[mask_in], Z[mask_in]])
            contrib[mask_in] = interpolator(points)

        # MC 范围外：clamp 到边界，平方反比衰减
        mask_out = ~mask_in
        if mask_out.any():
            R_clamped = np.clip(R[mask_out], 0.0, r_max)
            Z_clamped = np.clip(Z[mask_out], z_min, z_max)
            points_clamped = np.column_stack([R_clamped, Z_clamped])
            boundary = interpolator(points_clamped)
            d_boundary = np.sqrt(R_clamped**2 + Z_clamped**2)
            d = np.sqrt(R[mask_out]**2 + Z[mask_out]**2)
            safe = d > 1e-10
            scale = np.ones_like(d)
            scale[safe] = (d_boundary[safe] / d[safe]) ** 2
            contrib[mask_out] = boundary * scale

        contrib = np.nan_to_num(contrib, nan=0.0, posinf=0.0, neginf=0.0)

        # 物理缩放: FLUKA GeV/g/primary → mGy 总积分剂量
        activity_mCi = seed.get("activity", 3.0)
        scale = self._compute_physics_scale(activity_mCi, half_life_days, irradiation_time_days)
        contrib = contrib * scale

        return contrib.astype(np.float64)

    def _load_mc_data(
        self, seed_type_id: int, resolution_mm: float
    ) -> Optional[Dict[str, Any]]:
        """
        加载蒙特卡洛预计算数据（2D R-Z表）

        Args:
            seed_type_id: 籽源类型ID
            resolution_mm: 空间分辨率

        Returns:
            MC数据字典，包含 dose_table, R_values, Z_values, metadata
        """
        mc_result = self.mc_repository.get_closest_resolution(
            seed_type_id, resolution_mm, verified_only=True
        )

        if mc_result is None:
            return None

        data_path = Path(mc_result.data_path)
        if not data_path.exists():
            return None

        if mc_result.data_format == "npz":
            # npz格式：文件中包含 dose_table + r_values + z_values（+ 可选 error_table）
            data = dict(np.load(data_path))
            dose_table = data["dose_table"]
            r_values = data["r_values"]
            z_values = data["z_values"]
            return {
                "dose_table": dose_table,
                "r_values": r_values,
                "z_values": z_values,
                "r_max": float(r_values[-1]),
                "z_min": float(z_values[0]),
                "z_max": float(z_values[-1]),
                "grid_size_r": len(r_values),
                "grid_size_z": len(z_values),
                "resolution_mm": float(mc_result.resolution_mm),
                "dose_per_decay": float(mc_result.dose_per_decay),
            }
        elif mc_result.data_format == "npy":
            dose_table = load_npy_data(data_path)
        elif mc_result.data_format in ("h5", "hdf5"):
            dose_table = self._load_h5_data(data_path)
        else:
            return None

        r_max = float(mc_result.r_max)
        z_min = float(mc_result.z_min)
        z_max = float(mc_result.z_max)
        grid_size_r = int(mc_result.grid_size_r)
        grid_size_z = int(mc_result.grid_size_z)

        return {
            "dose_table": dose_table,
            "r_max": r_max,
            "z_min": z_min,
            "z_max": z_max,
            "grid_size_r": grid_size_r,
            "grid_size_z": grid_size_z,
            "resolution_mm": float(mc_result.resolution_mm),
            "dose_per_decay": float(mc_result.dose_per_decay),
        }

    def _build_interpolator(self, mc_data: Dict[str, Any]):
        """构建R-Z插值器"""
        from scipy.interpolate import RegularGridInterpolator

        dose_table = mc_data["dose_table"]

        # 优先使用文件中读取的实际坐标轴（npz格式），否则从DB元数据重建（npy格式）
        if "r_values" in mc_data:
            r_values = mc_data["r_values"]
            z_values = mc_data["z_values"]
        else:
            r_values = np.linspace(0, mc_data["r_max"], mc_data["grid_size_r"])
            z_values = np.linspace(mc_data["z_min"], mc_data["z_max"], mc_data["grid_size_z"])

        return RegularGridInterpolator(
            (r_values, z_values),
            dose_table,
            bounds_error=False,
            fill_value=0.0,
        )

    def _load_h5_data(self, filepath: Path) -> np.ndarray:
        """加载HDF5格式数据"""
        try:
            import h5py

            with h5py.File(filepath, "r") as f:
                for key in ["dose", "dose_grid", "data", "distribution"]:
                    if key in f:
                        return np.array(f[key])
                first_key = list(f.keys())[0]
                return np.array(f[first_key])
        except ImportError:
            raise ImportError("h5py is required to load HDF5 files")

    def query_point_dose(
        self,
        world_pos: Tuple[float, float, float],
        seeds: List[Dict[str, Any]],
        grid_resolution: float = 1.0,
        mc_data_override: Optional[Dict[str, Any]] = None,
        irradiation_time_days: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        查询指定世界坐标处的剂量率和总积分剂量

        Args:
            world_pos: 世界坐标 (x, y, z) mm
            seeds: 籽源列表
            grid_resolution: MC数据分辨率
            mc_data_override: MC数据覆盖（测试用）
            irradiation_time_days: 照射时间（天），None=永久植入

        Returns:
            {
                "position": (x, y, z),
                "dose_rate_uGy_per_h": float,    # T0 时刻剂量率 (μGy/h)
                "total_dose_mGy": float,          # 总积分剂量 (mGy)
                "per_seed_contributions": [...]   # 每颗籽源的贡献
            }
        """
        if not seeds:
            return {
                "position": tuple(world_pos),
                "dose_rate_uGy_per_h": 0.0,
                "total_dose_mGy": 0.0,
                "per_seed_contributions": [],
            }

        pos_arr = np.array([world_pos], dtype=np.float32)

        if mc_data_override is not None:
            mc_data = mc_data_override
            half_life_days = mc_data.get("half_life_days", 59.4)
        else:
            mc_data = self._load_mc_data(seeds[0]["seed_type_id"], grid_resolution)
            if mc_data is None:
                return {
                    "position": tuple(world_pos),
                    "dose_rate_uGy_per_h": 0.0,
                    "total_dose_mGy": 0.0,
                    "per_seed_contributions": [],
                }
            half_life_days = self._get_half_life(seeds[0]["seed_type_id"])

        interpolator = self._build_interpolator(mc_data)

        r_max = mc_data["r_max"]
        z_min = mc_data["z_min"]
        z_max = mc_data["z_max"]

        per_seed = []
        total_mGy = 0.0
        total_rate_uGyh = 0.0

        for seed in seeds:
            # 计算查询点相对该籽源的 (R, Z) 柱坐标
            seed_pos = np.array(seed["position"], dtype=np.float64)
            seed_dir = np.array(seed.get("orientation", (0.0, 0.0, 1.0)), dtype=np.float64)
            seed_dir_norm = np.linalg.norm(seed_dir)
            if seed_dir_norm < 1e-10:
                seed_dir = np.array([0.0, 0.0, 1.0])
            else:
                seed_dir = seed_dir / seed_dir_norm
            V = np.array(world_pos, dtype=np.float64) - seed_pos
            z_val = float(np.dot(V, seed_dir))
            r_val = float(np.sqrt(np.dot(V, V) - z_val * z_val))

            contrib_mGy = float(self._compute_seed_contribution(
                seed, pos_arr, mc_data, interpolator,
                half_life_days, irradiation_time_days,
            )[0])

            # 计算 T0 剂量率 = 总剂量 / 时间积分因子
            activity_mCi = seed.get("activity", 3.0)
            lam = PhysicalConstants.LN2 / (half_life_days * PhysicalConstants.DAYS_TO_SECONDS)
            if irradiation_time_days is None:
                time_factor = 1.0 / lam
            else:
                T_s = irradiation_time_days * PhysicalConstants.DAYS_TO_SECONDS
                time_factor = (1.0 - math.exp(-lam * T_s)) / lam

            dose_rate_mGy_per_s = contrib_mGy / time_factor if time_factor > 0 else 0.0
            dose_rate_uGy_per_h = dose_rate_mGy_per_s * 3600.0 * 1000.0  # mGy/s → μGy/h

            total_mGy += contrib_mGy
            total_rate_uGyh += dose_rate_uGy_per_h
            per_seed.append({
                "seed_index": len(per_seed),
                "activity_mCi": activity_mCi,
                "r_mm": r_val,
                "z_mm": z_val,
                "total_dose_mGy": contrib_mGy,
                "dose_rate_uGy_per_h": dose_rate_uGy_per_h,
            })

        return {
            "position": tuple(world_pos),
            "dose_rate_uGy_per_h": total_rate_uGyh,
            "total_dose_mGy": total_mGy,
            "per_seed_contributions": per_seed,
            "mc_range": {
                "r_max_mm": float(r_max),
                "z_min_mm": float(z_min),
                "z_max_mm": float(z_max),
            },
        }

    def calculate_dvh(
        self,
        dose_grid: np.ndarray,
        target_volume: np.ndarray,
        step_size: float = 1.0,
    ) -> Dict[str, Any]:
        """
        计算剂量体积直方图(DVH)

        Args:
            dose_grid: 剂量网格
            target_volume: 靶区体积掩膜（布尔数组）
            step_size: 剂量步长 (mGy)

        Returns:
            DVH数据字典
        """
        target_doses = dose_grid[target_volume]

        if len(target_doses) == 0:
            return {"dose": [], "volume": [], "d95": 0, "v100": 0}

        max_dose = np.max(target_doses)
        dose_bins = np.arange(0, max_dose + step_size, step_size)

        volume_hist = np.zeros_like(dose_bins)
        for i, dose_level in enumerate(dose_bins):
            volume_hist[i] = np.sum(target_doses >= dose_level) / len(target_doses) * 100

        d95_idx = np.searchsorted(volume_hist[::-1], 95)
        d95 = dose_bins[len(dose_bins) - 1 - d95_idx] if d95_idx < len(dose_bins) else 0

        v100 = volume_hist[np.searchsorted(dose_bins, 100)] if len(dose_bins) > 100 else 0

        return {
            "dose": dose_bins.tolist(),
            "volume": volume_hist.tolist(),
            "d95": float(d95),
            "v100": float(v100),
            "max_dose": float(max_dose),
            "mean_dose": float(np.mean(target_doses)),
            "min_dose": float(np.min(target_doses)),
        }

    def calculate_isodose_levels(
        self,
        dose_grid: np.ndarray,
        prescription_dose: float = 100.0,
        levels: List[float] = None,
    ) -> Dict[float, np.ndarray]:
        """
        计算等剂量面

        Args:
            dose_grid: 剂量网格
            prescription_dose: 处方剂量 (mGy)
            levels: 等剂量线级别（百分比）

        Returns:
            等剂量面数据字典 {level: surface_vertices}
        """
        if levels is None:
            levels = [50, 80, 90, 100]

        absolute_levels = [prescription_dose * level / 100 for level in levels]

        isodose_surfaces = {}
        for level, abs_level in zip(levels, absolute_levels):
            try:
                from skimage import measure

                verts, faces, normals, values = measure.marching_cubes(
                    dose_grid, level=abs_level
                )
                isodose_surfaces[level] = {
                    "vertices": verts,
                    "faces": faces,
                    "normals": normals,
                }
            except (ImportError, Exception):
                pass

        return isodose_surfaces
