"""
关于对话框
"""

from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt


class AboutDialog(QDialog):
    """关于对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("关于 Dose Planner")
        self.setFixedSize(400, 300)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        title = QLabel("Dose Planner")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        version = QLabel("版本 1.0.0")
        version.setAlignment(Qt.AlignCenter)
        layout.addWidget(version)

        desc = QLabel("介入科放射性籽源植入剂量计划软件")
        desc.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc)

        layout.addStretch()

        tech = QLabel("技术栈: Python, PySide6, PyVista, SimpleITK")
        tech.setAlignment(Qt.AlignCenter)
        tech.setStyleSheet("color: gray;")
        layout.addWidget(tech)

        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)