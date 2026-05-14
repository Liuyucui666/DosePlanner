# src/dose_planner/gui/widgets/seed_management_panel.py

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QGroupBox, QLabel, QComboBox, QDoubleSpinBox, QSpinBox,
    QPushButton, QListWidget, QCheckBox, QAbstractItemView
)
from config.constants import Defaults

class SeedManagementPanel(QWidget):
    """左侧种子管理面板：参数 + 列表 + 按钮"""

    # 信号：当参数变化时发出（可选）
    parameters_changed = Signal(dict)
    # 请求计算剂量
    calculate_requested = Signal()
    seeds_changed = Signal(list)
    clear_path_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._seeds = []          # 存储种子字典列表
        self._selected_index = -1

        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)

        # ---- 籽源参数组 ----
        seed_group = QGroupBox("籽源参数")
        seed_form = QFormLayout(seed_group)

        self.seed_type_combo = QComboBox()
        self.seed_type_combo.addItems(["I-125", "Pd-103", "Cs-131"])
        seed_form.addRow("类型:", self.seed_type_combo)

        self.activity_spin = QDoubleSpinBox()
        self.activity_spin.setRange(0.01, 100.0)
        self.activity_spin.setValue(Defaults.SEED_ACTIVITY)
        self.activity_spin.setSuffix(" mCi")
        self.activity_spin.setDecimals(2)
        self.activity_spin.setSingleStep(0.1)
        seed_form.addRow("活度:", self.activity_spin)

        # self.count_spin = QSpinBox()
        # self.count_spin.setRange(1, 1000)
        # self.count_spin.setValue(Defaults.SEED_COUNT)
        # seed_form.addRow("个数:", self.count_spin)

        self.spacing_spin = QDoubleSpinBox()
        self.spacing_spin.setRange(0.5, 50.0)
        self.spacing_spin.setValue(Defaults.SEED_SPACING)
        self.spacing_spin.setSuffix(" mm")
        self.spacing_spin.setDecimals(1)
        self.spacing_spin.setSingleStep(0.5)
        seed_form.addRow("间距:", self.spacing_spin)

        main_layout.addWidget(seed_group)

        # ---- 籽源列表 ----
        list_label = QLabel("籽源列表")
        list_label.setStyleSheet("font-weight: bold;")
        main_layout.addWidget(list_label)

        self.seed_list_widget = QListWidget()
        self.seed_list_widget.setSelectionMode(QAbstractItemView.SingleSelection)
        self.seed_list_widget.currentRowChanged.connect(self._on_list_row_changed)
        main_layout.addWidget(self.seed_list_widget, stretch=1)

        # ---- 列表操作按钮 ----
        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("添加")
        self.add_btn.clicked.connect(self._on_add_seed)
        btn_layout.addWidget(self.add_btn)

        self.remove_btn = QPushButton("删除")
        self.remove_btn.clicked.connect(self._on_remove_seed)
        btn_layout.addWidget(self.remove_btn)

        self.clear_btn = QPushButton("清空")
        self.clear_btn.clicked.connect(self._on_clear_seeds)
        btn_layout.addWidget(self.clear_btn)
        main_layout.addLayout(btn_layout)

        # ---- 计算参数组（移到列表下方） ----
        calc_group = QGroupBox("计算参数")
        calc_form = QFormLayout(calc_group)

        self.irradiation_spin = QDoubleSpinBox()
        self.irradiation_spin.setRange(1.0, 3650.0)
        self.irradiation_spin.setValue(Defaults.IRRADIATION_TIME_DAYS)
        self.irradiation_spin.setSuffix(" 天")
        self.irradiation_spin.setDecimals(0)
        self.irradiation_spin.setSingleStep(30)
        self.irradiation_spin.setToolTip('照射时间（天），勾选"永久植入"则不计时间衰减')
        calc_form.addRow("照射时间:", self.irradiation_spin)

        self.permanent_check = QCheckBox("永久植入")
        self.permanent_check.setChecked(False)
        self.permanent_check.setToolTip("永久植入：T→∞，积分全部衰变剂量")
        self.permanent_check.toggled.connect(self._on_permanent_toggled)
        calc_form.addRow("", self.permanent_check)

        self.parallel_check = QCheckBox("启用并行计算")
        self.parallel_check.setChecked(True)
        calc_form.addRow("", self.parallel_check)

        main_layout.addWidget(calc_group)

        # ---- 计算剂量按钮 ----
        self.calc_button = QPushButton("计算剂量")
        self.calc_button.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; font-weight: bold; }"
            "QPushButton:hover { background-color: #45a049; }"
        )
        self.calc_button.clicked.connect(self.calculate_requested.emit)
        main_layout.addWidget(self.calc_button)

        # 连接参数变化信号（可选）
        for widget in [self.activity_spin, self.spacing_spin, self.seed_type_combo]:
            if hasattr(widget, 'valueChanged'):
                widget.valueChanged.connect(self._on_any_param_changed)
            elif hasattr(widget, 'currentTextChanged'):
                widget.currentTextChanged.connect(self._on_any_param_changed)

    def set_parameters(self, params: dict):
        """从保存的参数字典恢复控件状态"""
        seed_type = params.get("seed_type", "I-125")
        idx = self.seed_type_combo.findText(seed_type)
        if idx >= 0:
            self.seed_type_combo.setCurrentIndex(idx)
        self.activity_spin.setValue(params.get("activity", 3.0))
        self.spacing_spin.setValue(params.get("spacing", 10.0))
        irradiation = params.get("irradiation_time_days", None)
        if irradiation is None:
            self.permanent_check.setChecked(True)
        else:
            self.permanent_check.setChecked(False)
            self.irradiation_spin.setValue(irradiation)
        self.parallel_check.setChecked(params.get("parallel", True))

    def _on_permanent_toggled(self, checked: bool):
        self.irradiation_spin.setEnabled(not checked)

    def _on_any_param_changed(self):
        self.parameters_changed.emit(self.get_parameters())

    def _on_list_row_changed(self, row):
        self._selected_index = row if row >= 0 else -1

    def _on_add_seed(self):
        # 默认在原点添加一个种子，实际应由路径生成
        from core.seed_manager import Seed
        seed = {
            'position': (0.0, 0.0, 0.0),
            'orientation': (0.0, 0.0, 1.0),
            'seed_type_id': self._get_seed_type_id(),
            'activity': self.activity_spin.value()
        }
        self._seeds.append(seed)
        self._update_list()
        self.seeds_changed.emit(self._seeds.copy())

    def _on_remove_seed(self):
        if 0 <= self._selected_index < len(self._seeds):
            del self._seeds[self._selected_index]
            self._update_list()
            self.seeds_changed.emit(self._seeds.copy())

    def _on_clear_seeds(self):
        self._seeds.clear()
        self._update_list()
        self.seeds_changed.emit(self._seeds.copy())
        self.clear_path_requested.emit()

    def _update_list(self):
        self.seed_list_widget.clear()
        for i, s in enumerate(self._seeds):
            pos = s['position']
            text = f"籽源 {i+1}: ({pos[0]:.1f}, {pos[1]:.1f}, {pos[2]:.1f}) [{s['activity']:.2f} mCi]"
            self.seed_list_widget.addItem(text)

    def _get_seed_type_id(self):
        name = self.seed_type_combo.currentText()
        mapping = {"I-125": 1, "Pd-103": 2, "Cs-131": 3}
        return mapping.get(name, 1)

    def set_seeds(self, seeds_list):
        """从外部设置籽源列表（字典列表）"""
        self._seeds = seeds_list
        self._update_list()
        self.seeds_changed.emit(self._seeds.copy()) 

    def get_seeds(self):
        """返回当前籽源字典列表"""
        return self._seeds

    def get_parameters(self) -> dict:
        """获取所有参数（籽源+计算）"""
        irradiation = None if self.permanent_check.isChecked() else self.irradiation_spin.value()
        return {
            'seed_type': self.seed_type_combo.currentText(),
            'activity': self.activity_spin.value(),
            'spacing': self.spacing_spin.value(),
            'irradiation_time_days': irradiation,
            'parallel': self.parallel_check.isChecked(),
            'colormap': 'viridis',
            'show_isodose': True
        }