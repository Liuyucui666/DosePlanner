"""
首选项对话框
"""

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QSpinBox,
    QDoubleSpinBox,
    QComboBox,
    QCheckBox,
    QPushButton,
    QTabWidget,
    QWidget,
    QFileDialog,
)
from PySide6.QtCore import Qt


class SettingsDialog(QDialog):
    """首选项对话框"""

    def __init__(self, settings=None, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("首选项")
        self.setMinimumSize(500, 400)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # 创建选项卡
        tabs = QTabWidget()

        # 通用设置
        general_tab = self._create_general_tab()
        tabs.addTab(general_tab, "通用")

        # 计算设置
        calculation_tab = self._create_calculation_tab()
        tabs.addTab(calculation_tab, "计算")

        # 可视化设置
        visualization_tab = self._create_visualization_tab()
        tabs.addTab(visualization_tab, "可视化")

        layout.addWidget(tabs)

        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(self.accept)
        btn_layout.addWidget(ok_btn)

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)

    def _create_general_tab(self) -> QWidget:
        """创建通用设置选项卡"""
        tab = QWidget()
        layout = QFormLayout(tab)

        # 数据目录
        data_dir_layout = QHBoxLayout()
        self.data_dir_edit = QLineEdit("./data")
        data_dir_layout.addWidget(self.data_dir_edit)

        browse_btn = QPushButton("浏览...")
        browse_btn.clicked.connect(self._on_browse_data_dir)
        data_dir_layout.addWidget(browse_btn)

        layout.addRow("数据目录:", data_dir_layout)

        # 日志级别
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        layout.addRow("日志级别:", self.log_level_combo)

        return tab

    def _create_calculation_tab(self) -> QWidget:
        """创建计算设置选项卡"""
        tab = QWidget()
        layout = QFormLayout(tab)

        # 默认网格分辨率
        self.grid_resolution_spin = QDoubleSpinBox()
        self.grid_resolution_spin.setRange(0.1, 10.0)
        self.grid_resolution_spin.setValue(1.0)
        self.grid_resolution_spin.setSuffix(" mm")
        layout.addRow("网格分辨率:", self.grid_resolution_spin)

        # 默认网格大小
        self.grid_size_spin = QSpinBox()
        self.grid_size_spin.setRange(32, 512)
        self.grid_size_spin.setValue(256)
        layout.addRow("网格大小:", self.grid_size_spin)

        # 并行处理
        self.parallel_check = QCheckBox("启用并行处理")
        self.parallel_check.setChecked(True)
        layout.addRow("", self.parallel_check)

        # 最大线程数
        self.max_workers_spin = QSpinBox()
        self.max_workers_spin.setRange(1, 32)
        self.max_workers_spin.setValue(4)
        layout.addRow("最大线程数:", self.max_workers_spin)

        return tab

    def _create_visualization_tab(self) -> QWidget:
        """创建可视化设置选项卡"""
        tab = QWidget()
        layout = QFormLayout(tab)

        # 默认色图
        self.colormap_combo = QComboBox()
        self.colormap_combo.addItems([
            "viridis", "plasma", "inferno", "magma", "hot", "cool", "jet"
        ])
        layout.addRow("默认色图:", self.colormap_combo)

        # 显示等剂量线
        self.isodose_check = QCheckBox("显示等剂量线")
        self.isodose_check.setChecked(True)
        layout.addRow("", self.isodose_check)

        # 渲染质量
        self.render_quality_combo = QComboBox()
        self.render_quality_combo.addItems(["低", "中", "高"])
        layout.addRow("渲染质量:", self.render_quality_combo)

        return tab

    def _on_browse_data_dir(self):
        """浏览数据目录"""
        dir_path = QFileDialog.getExistingDirectory(self, "选择数据目录")
        if dir_path:
            self.data_dir_edit.setText(dir_path)

    def get_settings(self) -> dict:
        """获取设置值"""
        return {
            "data_dir": self.data_dir_edit.text(),
            "log_level": self.log_level_combo.currentText(),
            "grid_resolution": self.grid_resolution_spin.value(),
            "grid_size": self.grid_size_spin.value(),
            "parallel": self.parallel_check.isChecked(),
            "max_workers": self.max_workers_spin.value(),
            "colormap": self.colormap_combo.currentText(),
            "show_isodose": self.isodose_check.isChecked(),
            "render_quality": self.render_quality_combo.currentIndex(),
        }