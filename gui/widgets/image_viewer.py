"""
CT图像显示组件
"""

import numpy as np
from pathlib import Path
from typing import Optional, Dict, Any

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QImage, QPixmap, QPainter, QPen, QColor, QWheelEvent
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QSlider,
    QPushButton,
    QGroupBox,
    QRadioButton,
    QScrollArea,
)

from core.image_processor import ImageProcessor
from config.constants import ImageConstants


class ImageViewer(QWidget):
    """CT图像显示组件"""

    # 切片变更信号
    slice_changed = Signal(int, str)
    # 窗宽窗位变更信号
    window_level_changed = Signal(float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._image_data = None
        self._current_slice = 0
        self._current_axis = "axial"
        self._window_width = ImageConstants.DEFAULT_WINDOW_WIDTH
        self._window_level = ImageConstants.DEFAULT_WINDOW_LEVEL
        self._zoom_factor = 1.0
        self._image_processor = ImageProcessor()
        self._setup_ui()

    def _setup_ui(self):
        """设置UI布局"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)

        # 工具栏
        toolbar_layout = QHBoxLayout()

        # 方向选择
        axis_group = QGroupBox("方向")
        axis_layout = QHBoxLayout(axis_group)

        self.axial_radio = QRadioButton("横断面")
        self.axial_radio.setChecked(True)
        self.axial_radio.toggled.connect(lambda: self._on_axis_change("axial"))
        axis_layout.addWidget(self.axial_radio)

        self.coronal_radio = QRadioButton("冠状面")
        self.coronal_radio.toggled.connect(lambda: self._on_axis_change("coronal"))
        axis_layout.addWidget(self.coronal_radio)

        self.sagittal_radio = QRadioButton("矢状面")
        self.sagittal_radio.toggled.connect(lambda: self._on_axis_change("sagittal"))
        axis_layout.addWidget(self.sagittal_radio)

        toolbar_layout.addWidget(axis_group)

        # 缩放按钮
        self.zoom_in_btn = QPushButton("放大")
        self.zoom_in_btn.clicked.connect(self._on_zoom_in)
        toolbar_layout.addWidget(self.zoom_in_btn)

        self.zoom_out_btn = QPushButton("缩小")
        self.zoom_out_btn.clicked.connect(self._on_zoom_out)
        toolbar_layout.addWidget(self.zoom_out_btn)

        self.fit_btn = QPushButton("适应")
        self.fit_btn.clicked.connect(self._on_fit)
        toolbar_layout.addWidget(self.fit_btn)

        toolbar_layout.addStretch()

        main_layout.addLayout(toolbar_layout)

        # 图像显示区域
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumSize(400, 300)
        self.image_label.setStyleSheet(
            "QLabel { background-color: black; border: 0px solid gray; }"
        )
        self.image_label.mousePressEvent = self._on_image_click
        self.image_label.wheelEvent = self._on_image_wheel

        # 创建滚动区域
        self.scroll_area = QScrollArea()
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: black;
                border: none;
            }
            QScrollArea > QWidget > QWidget {
                background-color: black;
            }
        """)
        self.scroll_area.setWidget(self.image_label)
        self.scroll_area.setWidgetResizable(False)  # 关键：不让滚动区域自动缩放 label，而是显示真实尺寸
        self.scroll_area.setAlignment(Qt.AlignCenter)

        main_layout.addWidget(self.scroll_area, stretch=1)

        # 切片滑块
        slice_layout = QHBoxLayout()
        slice_layout.addWidget(QLabel("切片:"))

        self.slice_slider = QSlider(Qt.Horizontal)
        self.slice_slider.setMinimum(0)
        self.slice_slider.setMaximum(0)
        self.slice_slider.valueChanged.connect(self._on_slider_changed)
        slice_layout.addWidget(self.slice_slider)

        self.slice_label = QLabel("0/0")
        self.slice_label.setMinimumWidth(60)
        slice_layout.addWidget(self.slice_label)

        main_layout.addLayout(slice_layout)

        # 窗宽窗位
        wl_layout = QHBoxLayout()
        wl_layout.addWidget(QLabel("窗位:"))

        self.level_slider = QSlider(Qt.Horizontal)
        self.level_slider.setMinimum(-1000)
        self.level_slider.setMaximum(1000)
        self.level_slider.setValue(40)
        self.level_slider.valueChanged.connect(self._on_level_changed)
        wl_layout.addWidget(self.level_slider)

        self.level_value_label = QLabel("40")
        self.level_value_label.setMinimumWidth(40)
        wl_layout.addWidget(self.level_value_label)

        wl_layout.addWidget(QLabel("窗宽:"))

        self.width_slider = QSlider(Qt.Horizontal)
        self.width_slider.setMinimum(1)
        self.width_slider.setMaximum(2000)
        self.width_slider.setValue(400)
        self.width_slider.valueChanged.connect(self._on_width_changed)
        wl_layout.addWidget(self.width_slider)

        self.width_value_label = QLabel("400")
        self.width_value_label.setMinimumWidth(40)
        wl_layout.addWidget(self.width_value_label)

        main_layout.addLayout(wl_layout)

        # 状态信息
        self.info_label = QLabel("就绪")
        self.info_label.setStyleSheet("QLabel { color: gray; font-size: 10px; }")
        main_layout.addWidget(self.info_label)

    def load_image(self, filepath: str):
        """
        加载CT图像

        Args:
            filepath: 图像文件路径
        """
        self._image_data = self._image_processor.load_image(filepath)

        # 更新切片滑块范围
        max_slices = self._image_data["array"].shape[0] - 1
        self.slice_slider.setMaximum(max_slices)
        self.slice_slider.setValue(max_slices // 2)
        self._current_slice = max_slices // 2

        # 更新信息
        shape = self._image_data["array"].shape
        spacing = self._image_data["spacing"]
        self.info_label.setText(
            f"图像尺寸: {shape[2]}x{shape[1]}x{shape[0]} | "
            f"体素间距: {spacing[0]:.2f}x{spacing[1]:.2f}x{spacing[2]:.2f} mm"
        )

        # 显示图像
        self._update_display()

    def _update_display(self):
        """更新图像显示"""
        if self._image_data is None:
            return

        # 获取当前切片
        slice_data = self._image_processor.get_slice(
            self._image_data, self._current_axis, self._current_slice
        )

        # 应用窗宽窗位
        display_data = self._image_processor.apply_window_level(
            slice_data, self._window_width, self._window_level
        )

        # 转换为QImage
        height, width = display_data.shape
        bytes_per_line = width
        q_image = QImage(
            display_data.data, width, height, bytes_per_line, QImage.Format_Grayscale8
        )

        # 应用缩放
        if self._zoom_factor != 1.0:
            new_width = int(width * self._zoom_factor)
            new_height = int(height * self._zoom_factor)
            q_image = q_image.scaled(
                new_width, new_height,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )

        # 显示
        pixmap = QPixmap.fromImage(q_image)
        self.image_label.setPixmap(pixmap)
        self.image_label.adjustSize()

        # 更新标签
        max_slices = self.slice_slider.maximum()
        self.slice_label.setText(f"{self._current_slice}/{max_slices}")

    def _on_slider_changed(self, value: int):
        """切片滑块变更"""
        self._current_slice = value
        self._update_display()
        self.slice_changed.emit(value, self._current_axis)

    def _on_axis_change(self, axis: str):
        """方向切换"""
        if self._image_data is None:
            return

        self._current_axis = axis

        # 更新滑块范围
        array = self._image_data["array"]
        if axis == "axial":
            max_slices = array.shape[0] - 1
        elif axis == "coronal":
            max_slices = array.shape[1] - 1
        else:
            max_slices = array.shape[2] - 1

        self.slice_slider.setMaximum(max_slices)
        self._current_slice = max_slices // 2
        self.slice_slider.setValue(self._current_slice)

        self._update_display()
        self.slice_changed.emit(self._current_slice, axis)

    def _on_level_changed(self, value: int):
        """窗位变更"""
        self._window_level = float(value)
        self.level_value_label.setText(str(value))
        self._update_display()
        self.window_level_changed.emit(self._window_width, self._window_level)

    def _on_width_changed(self, value: int):
        """窗宽变更"""
        self._window_width = float(value)
        self.width_value_label.setText(str(value))
        self._update_display()
        self.window_level_changed.emit(self._window_width, self._window_level)

    def _on_zoom_in(self):
        """放大"""
        self._zoom_factor *= 1.2
        self._update_display()

    def _on_zoom_out(self):
        """缩小"""
        self._zoom_factor *= 0.8
        if self._zoom_factor < 0.1:
            self._zoom_factor = 0.1
        self._update_display()

    def _on_fit(self):
        """适应窗口"""
        self._zoom_factor = 1.0
        self._update_display()

    def _on_image_click(self, event):
        """图像点击事件"""
        if self._image_data is None:
            return

        # 获取点击位置（图像坐标）
        pos = event.pos()
        pixmap = self.image_label.pixmap()
        if pixmap is None or pixmap.isNull():
            return

        # 计算pixmap在label中的偏移量（AlignCenter）
        label_w = self.image_label.width()
        label_h = self.image_label.height()
        offset_x = (label_w - pixmap.width()) // 2
        offset_y = (label_h - pixmap.height()) // 2

        # 将label坐标转换为pixmap坐标
        pix_x = pos.x() - offset_x
        pix_y = pos.y() - offset_y

        # 检查点击是否在pixmap范围内
        if pix_x < 0 or pix_x >= pixmap.width() or pix_y < 0 or pix_y >= pixmap.height():
            return

        # 获取像素值
        slice_data = self._image_processor.get_slice(
            self._image_data, self._current_axis, self._current_slice
        )

        # 从切片数据获取原始图像尺寸，计算实际图像坐标
        orig_h, orig_w = slice_data.shape
        img_x = int(pix_x * orig_w / pixmap.width())
        img_y = int(pix_y * orig_h / pixmap.height())

        if 0 <= img_y < slice_data.shape[0] and 0 <= img_x < slice_data.shape[1]:
            pixel_value = slice_data[img_y, img_x]
            self.info_label.setText(
                f"坐标: ({img_x}, {img_y}, 切片 {self._current_slice}) | "
                f"像素值: {pixel_value:.1f} HU"
            )

    def _on_image_wheel(self, event: QWheelEvent):
        """鼠标滚轮事件（切换切片）"""
        if self._image_data is None:
            return

        delta = event.angleDelta().y()
        if delta > 0:
            # 向上滚动，增加切片
            new_value = min(self._current_slice + 1, self.slice_slider.maximum())
        else:
            # 向下滚动，减少切片
            new_value = max(self._current_slice - 1, self.slice_slider.minimum())

        self.slice_slider.setValue(new_value)

    def get_image_data(self) -> Optional[Dict[str, Any]]:
        """
        获取图像数据

        Returns:
            图像数据字典
        """
        return self._image_data

    def get_current_slice_info(self) -> dict:
        """
        获取当前切片信息

        Returns:
            切片信息
        """
        return {
            "axis": self._current_axis,
            "slice_index": self._current_slice,
            "window_width": self._window_width,
            "window_level": self._window_level,
            "zoom": self._zoom_factor,
        }