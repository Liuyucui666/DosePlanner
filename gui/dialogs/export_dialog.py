"""
导出对话框
"""

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QLabel,
    QCheckBox,
    QPushButton,
    QFileDialog,
    QLineEdit,
    QRadioButton,
)
from PySide6.QtCore import Qt


class ExportDialog(QDialog):
    """结果导出对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("导出结果")
        self.setFixedSize(400, 300)
        self._export_path = ""
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # 导出内容
        content_group = QGroupBox("导出内容")
        content_layout = QVBoxLayout(content_group)

        self.dose_check = QCheckBox("剂量分布数据 (.npy)")
        self.dose_check.setChecked(True)
        content_layout.addWidget(self.dose_check)

        self.isodose_check = QCheckBox("等剂量面 (.stl)")
        self.isodose_check.setChecked(True)
        content_layout.addWidget(self.isodose_check)

        self.dvh_check = QCheckBox("DVH数据 (.csv)")
        self.dvh_check.setChecked(True)
        content_layout.addWidget(self.dvh_check)

        self.screenshot_check = QCheckBox("截图 (.png)")
        content_layout.addWidget(self.screenshot_check)

        layout.addWidget(content_group)

        # 导出路径
        path_group = QGroupBox("导出路径")
        path_layout = QHBoxLayout(path_group)

        self.path_edit = QLineEdit()
        path_layout.addWidget(self.path_edit)

        browse_btn = QPushButton("浏览...")
        browse_btn.clicked.connect(self._on_browse)
        path_layout.addWidget(browse_btn)

        layout.addWidget(path_group)

        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        export_btn = QPushButton("导出")
        export_btn.clicked.connect(self.accept)
        btn_layout.addWidget(export_btn)

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)

    def _on_browse(self):
        """浏览导出路径"""
        dir_path = QFileDialog.getExistingDirectory(self, "选择导出目录")
        if dir_path:
            self.path_edit.setText(dir_path)

    def get_export_options(self) -> dict:
        """获取导出选项"""
        return {
            "export_dose": self.dose_check.isChecked(),
            "export_isodose": self.isodose_check.isChecked(),
            "export_dvh": self.dvh_check.isChecked(),
            "export_screenshot": self.screenshot_check.isChecked(),
            "export_path": self.path_edit.text() or "./exports",
        }