"""
剂量计算器测试
"""

import numpy as np
from core.dose_calculator import DoseCalculator
from .fixtures.test_data import create_test_dose_grid, create_test_seeds, create_test_mc_data


class TestDoseCalculator:
    """剂量计算器测试类"""

    def setup_method(self):
        self.calculator = DoseCalculator(db_session=None)
        self.mc_data = create_test_mc_data()

    def test_calculate_total_dose_empty_seeds(self):
        """测试空籽源列表"""
        dose_grid, origin, _ = self.calculator.calculate_total_dose([], grid_size=32)
        assert dose_grid.shape == (32, 32, 32)
        assert np.all(dose_grid == 0)

    def test_calculate_total_dose_basic(self):
        """测试基本剂量计算（R-Z查表法）"""
        seeds = create_test_seeds(count=3, center=(16, 16, 16), spacing=10.0)
        dose_grid, origin, _ = self.calculator.calculate_total_dose(
            seeds, grid_size=32, mc_data_override=self.mc_data
        )

        assert len(dose_grid.shape) == 3
        assert dose_grid.shape[0] >= 32  # 网格可能自动扩展
        assert np.any(dose_grid > 0)

    def test_calculate_total_dose_single_seed_symmetry(self):
        """测试单籽源剂量分布的圆柱对称性"""
        seeds = [{
            "position": (16.0, 16.0, 16.0),
            "orientation": (0.0, 0.0, 1.0),
            "seed_type_id": 1,
            "activity": 100.0,
        }]
        dose_grid, origin, _ = self.calculator.calculate_total_dose(
            seeds, grid_size=32, mc_data_override=self.mc_data
        )

        # 同一半径上的剂量应该相等（圆柱对称性）
        z_idx = dose_grid.shape[2] // 2
        r1 = dose_grid[18, 16, z_idx] - dose_grid[14, 16, z_idx]
        assert abs(r1) < 1.0, f"圆柱对称性检查失败: r1={r1}"

    def test_calculate_total_dose_two_seeds_superposition(self):
        """测试两个籽源的叠加性"""
        pos = (16.0, 16.0, 16.0)
        seed1 = {
            "position": pos,
            "orientation": (0.0, 0.0, 1.0),
            "seed_type_id": 1,
            "activity": 50.0,
        }
        seed2 = {
            "position": pos,
            "orientation": (0.0, 0.0, 1.0),
            "seed_type_id": 1,
            "activity": 50.0,
        }
        seed_combined = {
            "position": pos,
            "orientation": (0.0, 0.0, 1.0),
            "seed_type_id": 1,
            "activity": 100.0,
        }

        dose_grid, _, _ = self.calculator.calculate_total_dose(
            [seed1], grid_size=32, mc_data_override=self.mc_data
        )
        dose1_only = dose_grid.copy()
        dose_grid, _, _ = self.calculator.calculate_total_dose(
            [seed2], grid_size=32, mc_data_override=self.mc_data
        )
        dose2_only = dose_grid.copy()
        dose_grid, _, _ = self.calculator.calculate_total_dose(
            [seed1, seed2], grid_size=32, mc_data_override=self.mc_data
        )
        dose_combined = dose_grid.copy()
        dose_grid, _, _ = self.calculator.calculate_total_dose(
            [seed_combined], grid_size=32, mc_data_override=self.mc_data
        )
        dose_single_2x = dose_grid.copy()

        assert np.allclose(dose_combined, dose1_only + dose2_only, rtol=1e-5, atol=1e-5), \
            "叠加性检查失败"
        assert np.allclose(dose_combined, dose_single_2x, rtol=1e-5, atol=1e-5), \
            "2x单源与双源不等价"

    def test_calculate_dvh(self):
        """测试DVH计算"""
        dose_grid = create_test_dose_grid(32)
        target = dose_grid > 10

        dvh = self.calculator.calculate_dvh(dose_grid, target)
        assert "dose" in dvh
        assert "volume" in dvh
        assert "d95" in dvh
        assert "v100" in dvh
        assert len(dvh["dose"]) > 0
        assert len(dvh["volume"]) > 0