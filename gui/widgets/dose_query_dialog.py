"""
位置剂量查询对话框

输入世界坐标 (x, y, z) mm，查询该点的:
  - T0 时刻剂量率 (μGy/h)
  - 总积分剂量 (mGy)
  - 每颗籽源的贡献
"""

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QGroupBox, QLabel, QLineEdit, QPushButton,
    QTextEdit, QDoubleSpinBox,
)


class DoseQueryDialog(QDialog):
    """位置剂量查询对话框"""

    def __init__(self, dose_calculator, seeds, params, parent=None):
        super().__init__(parent)
        self._calc = dose_calculator
        self._seeds = seeds
        self._params = params
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle("位置剂量查询")
        self.setMinimumSize(500, 400)
        self.resize(550, 500)

        layout = QVBoxLayout(self)

        # ---- 坐标输入 ----
        coord_group = QGroupBox("查询位置 (世界坐标 mm)")
        coord_layout = QFormLayout(coord_group)

        self.x_spin = QDoubleSpinBox()
        self.x_spin.setRange(-9999, 9999)
        self.x_spin.setDecimals(1)
        self.x_spin.setSuffix(" mm")
        coord_layout.addRow("X:", self.x_spin)

        self.y_spin = QDoubleSpinBox()
        self.y_spin.setRange(-9999, 9999)
        self.y_spin.setDecimals(1)
        self.y_spin.setSuffix(" mm")
        coord_layout.addRow("Y:", self.y_spin)

        self.z_spin = QDoubleSpinBox()
        self.z_spin.setRange(-9999, 9999)
        self.z_spin.setDecimals(1)
        self.z_spin.setSuffix(" mm")
        coord_layout.addRow("Z:", self.z_spin)

        layout.addWidget(coord_group)

        # ---- 预设位置 ----
        preset_layout = QHBoxLayout()
        self.seed_center_btn = QPushButton("籽源中心")
        self.seed_center_btn.setToolTip("取所有籽源位置的平均值")
        self.seed_center_btn.clicked.connect(self._on_seed_center)
        preset_layout.addWidget(self.seed_center_btn)

        self.origin_btn = QPushButton("原点 (0,0,0)")
        self.origin_btn.clicked.connect(self._on_origin)
        preset_layout.addWidget(self.origin_btn)

        layout.addLayout(preset_layout)

        # ---- 查询按钮 ----
        self.query_btn = QPushButton("查询剂量")
        self.query_btn.setStyleSheet(
            "QPushButton { background-color: #2196F3; color: white; font-weight: bold; }"
        )
        self.query_btn.clicked.connect(self._on_query)
        layout.addWidget(self.query_btn)

        # ---- 结果展示 ----
        result_group = QGroupBox("查询结果")
        result_layout = QVBoxLayout(result_group)

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setStyleSheet("QTextEdit { font-family: monospace; font-size: 12px; }")
        result_layout.addWidget(self.result_text)

        layout.addWidget(result_group, stretch=1)

    def _on_seed_center(self):
        if not self._seeds:
            return
        positions = np.array([s["position"] for s in self._seeds])
        center = positions.mean(axis=0)
        self.x_spin.setValue(center[0])
        self.y_spin.setValue(center[1])
        self.z_spin.setValue(center[2])

    def _on_origin(self):
        self.x_spin.setValue(0)
        self.y_spin.setValue(0)
        self.z_spin.setValue(0)

    def _on_query(self):
        pos = (self.x_spin.value(), self.y_spin.value(), self.z_spin.value())
        irradiation = self._params.get("irradiation_time_days", None)
        grid_res = self._params.get("grid_resolution", 1.0)

        try:
            result = self._calc.query_point_dose(
                pos, self._seeds,
                grid_resolution=grid_res,
                irradiation_time_days=irradiation,
            )
        except Exception as e:
            self.result_text.setHtml(f"<p style='color:red'>查询失败: {e}</p>")
            return

        lines = []
        lines.append(f"<b>查询位置:</b> ({pos[0]:.1f}, {pos[1]:.1f}, {pos[2]:.1f}) mm")
        lines.append("")
        lines.append(f"<b>T0 时刻剂量率:</b> <span style='color:#2196F3'>{result['dose_rate_uGy_per_h']:.2f} μGy/h</span>")
        lines.append(f"<b>总积分剂量:</b> <span style='color:#FF5722'>{result['total_dose_mGy']:.2f} mGy</span>")
        lines.append("")

        mc_range = result.get("mc_range", {})
        if mc_range:
            lines.append(
                f"MC数据范围: R ≤ {mc_range['r_max_mm']:.0f} mm, "
                f"Z ∈ [{mc_range['z_min_mm']:.0f}, {mc_range['z_max_mm']:.0f}] mm"
            )

        time_str = "永久植入" if irradiation is None else f"{irradiation:.0f} 天"
        lines.append(f"照射时间: {time_str} | 籽源数: {len(self._seeds)}")
        lines.append("<hr>")
        lines.append("<b>各籽源贡献 (R, Z 为相对查询点的柱坐标):</b>")

        for c in result["per_seed_contributions"]:
            line = (
                f"  籽源 {c['seed_index'] + 1}: "
                f"R={c['r_mm']:.1f}mm Z={c['z_mm']:.1f}mm | "
                f"剂量率 {c['dose_rate_uGy_per_h']:.2f} μGy/h | "
                f"总剂量 {c['total_dose_mGy']:.2f} mGy | "
                f"活度 {c['activity_mCi']:.2f} mCi"
            )
            lines.append(line)

        self.result_text.setHtml("<br>".join(lines))
