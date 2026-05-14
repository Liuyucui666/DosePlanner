"""
增强型CT图像查看器 - 支持籽源路径绘制

在标准ImageViewer基础上扩展，支持在CT图像上直接绘制籽源路径，
提供坐标转换和籽源显示功能。
"""

import numpy as np
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple

from PySide6.QtCore import Qt, Signal, Slot, QPoint, QPointF,QRectF
from PySide6.QtGui import (
    QImage, QPixmap, QPainter, QPen, QColor, QBrush,
    QWheelEvent, QMouseEvent
)
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QSlider, QPushButton, QGroupBox, QRadioButton,
    QToolTip,
)

from .image_viewer import ImageViewer
from core.image_processor import ImageProcessor
from core.seed_manager import Seed
from core.transform import Transform3D
from config.constants import ImageConstants


class EnhancedImageViewer(ImageViewer):
    """
    增强型CT图像查看器

    在标准ImageViewer基础上添加：
    1. 籽源路径绘制功能
    2. 坐标转换系统
    3. 籽源显示和交互
    """

    # 新增信号
    # 路径绘制信号
    path_point_added = Signal(tuple)      # 添加单个路径点（世界坐标）
    path_drawn = Signal(list)             # 路径绘制完成（世界坐标列表）
    path_cleared = Signal()               # 路径已清空

    # 剂量查询信号
    dose_queried = Signal(str)            # 右键查询剂量结果文本

    # 籽源交互信号
    seed_selected = Signal(int)           # 籽源被选中（索引）
    seed_double_clicked = Signal(int)     # 籽源被双击（索引）

    def __init__(self, parent=None):
        """初始化增强型图像查看器"""
        super().__init__(parent)

        # 绘制模式相关属性
        self._drawing_mode = False
        self._current_path_points = []    # 当前路径点（世界坐标）
        self._is_drawing = False

        # 籽源显示相关属性
        self._seeds = []                  # Seed对象列表
        self._selected_seed_index = -1    # 选中籽源索引

        # 剂量叠加相关属性
        self._dose_grid = None            # 总积分剂量网格 (3D, mGy)
        self._dose_rate = None            # T0剂量率网格 (3D, μGy/h)
        self._dose_origin = (0, 0, 0)     # 剂量网格原点
        self._dose_spacing = (1, 1, 1)    # 剂量网格间距

        # 坐标转换缓存
        self._transform_cache = {}        # 转换参数缓存

        # 绘制样式
        self._path_color = QColor(255, 210, 0)      # 路径颜色（绿色）
        self._path_point_color = QColor(0, 255, 0, 150)  # 路径点颜色（半透明绿）
        self._seed_color = QColor(220, 20, 100)      # 籽源颜色（红色）
        self._selected_seed_color = QColor(0, 255, 200)  # 选中籽源颜色（黄色）
        self._direction_color = QColor(0, 200, 255)  # 方向指示颜色（青色）

        # 剂量叠加
        self._cached_slice_index = -1
        self._cached_axis = ""
        self._colormap = None  # 用来保存 matplotlib 色图对象
        self._dose_threshold = 200.0

        # 初始化鼠标事件处理
        self._setup_mouse_handling()

    def _setup_mouse_handling(self):
        """设置鼠标事件处理"""
        # 保存原始事件处理函数
        self._original_mouse_press = self.image_label.mousePressEvent
        self._original_mouse_move = self.image_label.mouseMoveEvent
        self._original_mouse_release = self.image_label.mouseReleaseEvent
        self._original_mouse_double_click = self.image_label.mouseDoubleClickEvent

        # 替换为增强事件处理
        self.image_label.mousePressEvent = self._enhanced_mouse_press_event
        self.image_label.mouseMoveEvent = self._enhanced_mouse_move_event
        self.image_label.mouseReleaseEvent = self._enhanced_mouse_release_event
        self.image_label.mouseDoubleClickEvent = self._enhanced_mouse_double_click_event

    # ==================== 坐标转换方法 ====================

    def _get_pixmap_offset(self) -> Tuple[int, int]:
        """计算pixmap在QLabel中的居中偏移量 (offset_x, offset_y)"""
        pixmap = self.image_label.pixmap()
        if pixmap is None or pixmap.isNull():
            return (0, 0)
        label_w = self.image_label.width()
        label_h = self.image_label.height()
        offset_x = (label_w - pixmap.width()) // 2
        offset_y = (label_h - pixmap.height()) // 2
        return (offset_x, offset_y)

    def _get_original_dims(self) -> Tuple[int, int]:
        """获取当前视图方向下原始（缩放前）的显示宽度和高度"""
        if self._image_data is None:
            return (0, 0)
        array = self._image_data["array"]
        if self._current_axis == "axial":
            return (array.shape[2], array.shape[1])
        elif self._current_axis == "coronal":
            return (array.shape[2], array.shape[0])
        else:  # sagittal
            return (array.shape[1], array.shape[0])

    def screen_to_image_coords(self, screen_pos: QPoint) -> Optional[Tuple[int, int, int]]:
        """
        屏幕坐标转换为图像坐标（体素索引）

        Args:
            screen_pos: 屏幕坐标（像素）

        Returns:
            图像坐标 (x, y, slice) 或 None（转换失败）
        """
        if self._image_data is None:
            return None

        pixmap = self.image_label.pixmap()
        if pixmap is None or pixmap.isNull():
            return None

        # 计算pixmap在label中的偏移量（AlignCenter）
        offset_x, offset_y = self._get_pixmap_offset()

        # 将label坐标转换为pixmap坐标（减去居中偏移）
        pix_x = screen_pos.x() - offset_x
        pix_y = screen_pos.y() - offset_y

        # 检查点击是否在pixmap范围内
        if pix_x < 0 or pix_x >= pixmap.width() or pix_y < 0 or pix_y >= pixmap.height():
            return None

        # 计算实际图像坐标（pixmap已应用缩放，需要除回）
        orig_w, orig_h = self._get_original_dims()
        img_x = int(pix_x * orig_w / pixmap.width())
        img_y = int(pix_y * orig_h / pixmap.height())

        # 获取当前切片索引
        slice_index = self._current_slice

        # 根据当前视图方向调整坐标顺序
        if self._current_axis == "axial":
            # 横断面：x, y, slice
            return (img_x, img_y, slice_index)
        elif self._current_axis == "coronal":
            # 冠状面：x, slice, y
            return (img_x, slice_index, img_y)
        else:  # sagittal
            # 矢状面：slice, x, y
            return (slice_index, img_x, img_y)

    def image_to_world_coords(self, image_coords: Tuple[int, int, int]) -> Optional[Tuple[float, float, float]]:
        """
        图像坐标转换为世界坐标（毫米）

        Args:
            image_coords: 图像坐标 (i, j, k) 体素索引

        Returns:
            世界坐标 (x, y, z) 毫米 或 None（转换失败）
        """
        if self._image_data is None:
            return None

        try:
            # 使用Transform3D进行转换
            coords_array = np.array([image_coords])
            world_coords = Transform3D.image_to_world_coordinates(
                coords_array,
                self._image_data["origin"],
                self._image_data["spacing"],
                self._image_data["direction"]
            )

            return tuple(world_coords[0])
        except Exception as e:
            print(f"坐标转换失败: {e}")
            return None

    def world_to_screen_coords(self, world_coords: Tuple[float, float, float]) -> Optional[QPoint]:
        """
        世界坐标转换为屏幕坐标（像素）

        Args:
            world_coords: 世界坐标 (x, y, z) 毫米

        Returns:
            屏幕坐标 QPoint 或 None（转换失败）
        """
        if self._image_data is None:
            return None

        try:
            # 世界坐标→图像坐标
            coords_array = np.array([world_coords])
            image_coords = Transform3D.world_to_image_coordinates(
                coords_array,
                self._image_data["origin"],
                self._image_data["spacing"],
                self._image_data["direction"]
            )

            # 图像坐标→屏幕坐标
            img_coord = image_coords[0]

            # 根据当前视图方向提取坐标
            if self._current_axis == "axial":
                # 横断面：x, y, z → 屏幕x, y
                img_x, img_y = img_coord[0], img_coord[1]
                current_slice = int(round(img_coord[2]))
            elif self._current_axis == "coronal":
                # 冠状面：x, z, y → 屏幕x, y
                img_x, img_y = img_coord[0], img_coord[2]
                current_slice = int(round(img_coord[1]))
            else:  # sagittal
                # 矢状面：z, x, y → 屏幕x, y
                img_x, img_y = img_coord[1], img_coord[2]
                current_slice = int(round(img_coord[0]))

            # 检查是否在当前切片上（允许一定误差）
            if abs(current_slice - self._current_slice) > 0.5:
                return None

            # 转换为pixmap坐标（用于叠加层绘制）
            pixmap = self.image_label.pixmap()
            if pixmap is None or pixmap.isNull():
                return None

            orig_w, orig_h = self._get_original_dims()
            if orig_w == 0 or orig_h == 0:
                return None

            screen_x = int(img_x * pixmap.width() / orig_w)
            screen_y = int(img_y * pixmap.height() / orig_h)

            return QPoint(screen_x, screen_y)

        except Exception as e:
            print(f"世界坐标→屏幕坐标转换失败: {e}")
            return None

    def screen_to_world_coords(self, screen_pos: QPoint) -> Optional[Tuple[float, float, float]]:
        """
        屏幕坐标转换为世界坐标（毫米）

        Args:
            screen_pos: 屏幕坐标（像素）

        Returns:
            世界坐标 (x, y, z) 毫米 或 None（转换失败）
        """
        # 屏幕坐标→图像坐标
        image_coords = self.screen_to_image_coords(screen_pos)
        if image_coords is None:
            return None

        # 图像坐标→世界坐标
        return self.image_to_world_coords(image_coords)

    # ==================== 绘制控制方法 ====================

    def set_drawing_mode(self, enabled: bool):
        """
        启用/禁用绘制模式

        Args:
            enabled: True启用绘制模式，False禁用
        """
        self._drawing_mode = enabled

        # 更新光标样式
        if enabled:
            self.image_label.setCursor(Qt.CrossCursor)
        else:
            self.image_label.setCursor(Qt.ArrowCursor)

        # 清空当前路径（如果禁用绘制模式）
        if not enabled:
            self._current_path_points.clear()
            self.update()

    def set_seeds(self, seeds: List[Seed]):
        """
        设置要显示的籽源

        Args:
            seeds: Seed对象列表
        """
        self._seeds = seeds
        self.update()

    def set_selected_seed_index(self, index: int):
        """
        设置选中的籽源索引

        Args:
            index: 籽源索引，-1表示取消选中
        """
        if index < -1 or index >= len(self._seeds):
            return

        self._selected_seed_index = index
        self.update()

    def set_dose_data(self, dose_grid, grid_origin, grid_spacing, dose_rate=None):
        """
        设置剂量数据用于2D切片叠加

        Args:
            dose_grid: 3D总积分剂量网格 (mGy)
            grid_origin: 网格原点 (mm)
            grid_spacing: 网格间距 (mm)
            dose_rate: 3D T0剂量率网格 (μGy/h)，可选
        """
        self._dose_grid = dose_grid
        self._dose_origin = tuple(grid_origin)
        self._dose_spacing = tuple(grid_spacing)
        self._dose_rate = dose_rate
        # 缓存全局对数最大值（只算一次）
        if self._dose_grid is not None and np.max(self._dose_grid) > 0:
            self._log_global_max = np.max(np.log1p(self._dose_grid))
        else:
            self._log_global_max = 0.0
        self._cached_dose_pixmap = None
        self._cached_slice_index = -1
        self.update()

    def set_dose_threshold(self, threshold_mGy: float):
        """设置等剂量线阈值（mGy）"""
        self._dose_threshold = threshold_mGy
        self._cached_dose_pixmap = None   # 清除缓存
        self.update()

    def clear_path(self):
        """清空当前路径"""
        self._current_path_points.clear()
        self.update()
        self.path_cleared.emit()

    def get_current_path_points(self) -> List[Tuple[float, float, float]]:
        """
        获取当前路径点（世界坐标）

        Returns:
            当前路径点列表
        """
        return self._current_path_points.copy()

    # ==================== 鼠标事件处理 ====================

    def _enhanced_mouse_press_event(self, event: QMouseEvent):
        """增强的鼠标按下事件处理"""
        # 右键点击查询剂量（优先处理，不受绘制模式影响）
        if event.button() == Qt.RightButton and self._dose_grid is not None:
            self._query_dose_at_screen_pos(event.pos())
            return

        # 调用原始处理函数（用于CT图像交互）
        if self._original_mouse_press is not None:
            self._original_mouse_press(event)

        # 在绘制模式下处理路径绘制
        if self._drawing_mode and event.button() == Qt.LeftButton:
            self._is_drawing = True

            # 转换坐标
            world_coords = self.screen_to_world_coords(event.pos())
            if world_coords is not None:
                self._current_path_points.append(world_coords)
                self.path_point_added.emit(world_coords)
                self.update()

    def _enhanced_mouse_move_event(self, event: QMouseEvent):
        """增强的鼠标移动事件处理"""
        # 调用原始处理函数
        if self._original_mouse_move is not None:
            self._original_mouse_move(event)

        # 在绘制模式下连续添加路径点
        if self._drawing_mode and self._is_drawing and event.buttons() & Qt.LeftButton:
            world_coords = self.screen_to_world_coords(event.pos())
            if world_coords is not None:
                self._current_path_points.append(world_coords)
                self.path_point_added.emit(world_coords)
                self.update()

    def _enhanced_mouse_release_event(self, event: QMouseEvent):
        """增强的鼠标释放事件处理"""
        # 调用原始处理函数
        if self._original_mouse_release is not None:
            self._original_mouse_release(event)

        # 结束绘制
        if self._drawing_mode and event.button() == Qt.LeftButton and self._is_drawing:
            self._is_drawing = False

            # 如果路径点足够，发射完成信号
            if len(self._current_path_points) >= 2:
                self.path_drawn.emit(self._current_path_points.copy())

            self.update()

        # 右键点击查询剂量
        if event.button() == Qt.RightButton and self._dose_grid is not None:
            self._query_dose_at_screen_pos(event.pos())

    def _enhanced_mouse_double_click_event(self, event: QMouseEvent):
        """增强的鼠标双击事件处理"""
        # 调用原始处理函数
        if self._original_mouse_double_click is not None:
            self._original_mouse_double_click(event)

        # 检查是否双击了籽源
        if event.button() == Qt.LeftButton:
            screen_pos = event.pos()

            # 将event坐标从label坐标转换为pixmap坐标
            offset_x, offset_y = self._get_pixmap_offset()
            pixmap_pos = QPoint(screen_pos.x() - offset_x, screen_pos.y() - offset_y)

            # 检查每个籽源
            for i, seed in enumerate(self._seeds):
                pixmap_coords = self.world_to_screen_coords(seed.position)
                if pixmap_coords is None:
                    continue

                # 计算距离（pixmap坐标空间）
                dx = pixmap_pos.x() - pixmap_coords.x()
                dy = pixmap_pos.y() - pixmap_coords.y()
                distance = np.sqrt(dx*dx + dy*dy)

                # 如果点击在籽源附近（10像素内）
                if distance < 10:
                    self._selected_seed_index = i
                    self.seed_selected.emit(i)
                    self.seed_double_clicked.emit(i)
                    self.update()
                    return

    # ==================== 绘制方法 ====================

    def paintEvent(self, event):
        """重写绘制事件，添加叠加层"""
        # 调用父类绘制CT图像
        super().paintEvent(event)

        # 检查是否有有效的pixmap
        pixmap = self.image_label.pixmap()
        if pixmap is None or pixmap.isNull():
            # 没有图像可绘制，直接返回
            return

        # 创建绘制器，在图像标签上绘制叠加层
        overlay_pixmap = QPixmap(pixmap)
        painter = QPainter(overlay_pixmap)
        if painter.isActive():
            try:
                # 绘制剂量叠加层（在CT之上、路径和籽源之下）
                self._draw_dose_overlay(painter)

                # 绘制路径叠加层
                self._draw_path_overlay(painter)

                # 绘制籽源叠加层
                self._draw_seeds_overlay(painter)

                # 绘制 colorbar
                self._draw_colorbar(painter) 

            except Exception as e:
                print(f"绘制叠加层时出错: {e}")
                import traceback
                traceback.print_exc()
            finally:
                painter.end()
        self.image_label.setPixmap(overlay_pixmap)


    def _draw_dose_overlay(self, painter: QPainter):
        if self._dose_grid is None or self._image_data is None:
            return

        # 检查缓存
        if (self._cached_dose_pixmap is not None and
            self._cached_slice_index == self._current_slice and
            self._cached_axis == self._current_axis):
            painter.drawPixmap(0, 0, self._cached_dose_pixmap)
            return

        from matplotlib import colormaps

        # 提取当前剂量切片
        if self._current_axis == "axial":
            dose_slice = self._dose_grid[self._current_slice, :, :]
        elif self._current_axis == "coronal":
            dose_slice = self._dose_grid[:, self._current_slice, :]
        else:  # sagittal
            dose_slice = self._dose_grid[:, :, self._current_slice]

        # 全局对数归一化
        if self._log_global_max <= 0:
            return
        dose_norm = np.log1p(dose_slice) / self._log_global_max
        dose_norm = np.clip(dose_norm, 0, 1)

        # 色图映射
        cmap = colormaps.get('jet')
        rgba_float = cmap(dose_norm)
        rgba = (rgba_float[:, :, :4] * 255).astype(np.uint8)

        # 透明度：低于阈值的区域完全透明，高于阈值按归一化剂量显示
        alpha = np.where(dose_slice >= self._dose_threshold,
                         (dose_norm * 80).astype(np.uint8),
                         0)
        rgba[:, :, 3] = alpha

        h, w = dose_slice.shape
        img_data = rgba.tobytes()
        qimage = QImage(img_data, w, h, w * 4, QImage.Format_RGBA8888)
        dose_pixmap = QPixmap.fromImage(qimage)

        # 缩放到 CT 图像大小
        ct_pixmap = self.image_label.pixmap()
        if ct_pixmap:
            dose_pixmap = dose_pixmap.scaled(
                ct_pixmap.size(), Qt.IgnoreAspectRatio, Qt.SmoothTransformation
            )
            self._cached_dose_pixmap = dose_pixmap
            self._cached_slice_index = self._current_slice
            self._cached_axis = self._current_axis

        painter.drawPixmap(0, 0, dose_pixmap)

    def _draw_colorbar(self, painter: QPainter):
        """在图像右侧绘制垂直 colorbar，对数刻度 10^2 ~ 10^8"""
        if self._dose_grid is None or self._image_data is None:
            return

        pixmap = self.image_label.pixmap()
        if pixmap is None:
            return
        pw = pixmap.width()
        ph = pixmap.height()

        bar_width = 20
        bar_height = min(200, ph - 40)
        margin_right = 10
        x_bar = pw - bar_width - margin_right
        y_bar = (ph - bar_height) // 2

        # ---- 1. 生成色条图像（从上到下：高剂量 → 低剂量） ----
        from matplotlib import colormaps
        import math
        cmap = colormaps.get('jet')
        steps = 256
        # 线性渐变：1.0 (红) ～ 0.0 (蓝) 对应从上到下（高→低）
        gradient = np.linspace(1, 0, steps)
        rgba_float = cmap(gradient[:, np.newaxis])
        rgba = (rgba_float[:, 0, :4] * 255).astype(np.uint8)

        bar_img = QImage(bar_width, bar_height, QImage.Format_RGBA8888)
        for row in range(bar_height):
            idx = int((row / (bar_height - 1)) * (steps - 1))
            r, g, b = int(rgba[idx, 0]), int(rgba[idx, 1]), int(rgba[idx, 2])
            color = QColor(r, g, b, 255)
            for col in range(bar_width):
                bar_img.setPixelColor(col, row, color)
        painter.drawImage(x_bar, y_bar, bar_img)

        # ---- 2. 对数刻度设置 ----
        global_max = np.max(self._dose_grid)
        if global_max <= 0:
            return

        # 固定刻度范围：10^2 ～ 10^8
        exp_min, exp_max = 2, 8
        dose_min = 10 ** exp_min
        dose_max = 10 ** exp_max

        # 计算对数空间中的刻度列表（仅包含 <= global_max 的整数次方）
        ticks = []
        for e in range(exp_min, exp_max + 1):
            value = 10 ** e
            if value <= global_max:
                ticks.append(value)

        # 对数映射到色条位置的函数
        log_min = np.log10(ticks[0])
        log_max = np.log10(ticks[-1])

        font = painter.font()
        font.setPixelSize(9)
        painter.setFont(font)
        painter.setPen(QColor(255, 255, 255))
        tick_length = 5

        for val in ticks:
            # 计算该值在色条高度方向的位置（0 对应底部，1 对应顶部）
            log_val = np.log10(val)
            if log_max == log_min:
                t = 1.0
            else:
                t = (log_val - log_min) / (log_max - log_min)
            # 色条底部是低剂量（ticks[0]），顶部是高剂量（ticks[-1]）
            # 底部 y = y_bar + bar_height，顶部 y = y_bar
            y_tick = y_bar + int(bar_height * (1 - t))

            # 标签：如果是 10 的整数次方且不是 0，显示 1eX，否则科学记数法
            if val == 0:
                label = "0"
            elif val == 10 ** round(np.log10(val)):
                label = f"1e{int(np.log10(val))}"
            else:
                label = f"{val:.1e}"

            # 画短线
            painter.drawLine(x_bar - tick_length, int(y_tick),
                            x_bar, int(y_tick))
            # 画文本
            text_rect = QRectF(0, int(y_tick) - 8,
                            x_bar - tick_length - 2, 16)
            painter.drawText(text_rect, Qt.AlignRight | Qt.AlignVCenter, label)

    def _draw_path_overlay(self, painter: QPainter):
        """绘制路径叠加层"""
        if not self._current_path_points:
            return

        # 设置路径绘制样式
        path_pen = QPen(self._path_color)
        path_pen.setWidth(2)
        painter.setPen(path_pen)

        # 绘制路径线
        for i in range(1, len(self._current_path_points)):
            p1 = self.world_to_screen_coords(self._current_path_points[i-1])
            p2 = self.world_to_screen_coords(self._current_path_points[i])

            if p1 is not None and p2 is not None:
                painter.drawLine(p1, p2)

        # # 设置路径点绘制样式
        # point_brush = QBrush(self._path_point_color)
        # painter.setBrush(point_brush)
        # painter.setPen(Qt.NoPen)

        # # 绘制路径点
        # for point in self._current_path_points:
        #     screen_pos = self.world_to_screen_coords(point)
        #     if screen_pos is not None:
        #         painter.drawEllipse(screen_pos, 4, 4)

    def _draw_seeds_overlay(self, painter: QPainter):
        """绘制籽源叠加层"""
        for i, seed in enumerate(self._seeds):
            # 转换为屏幕坐标
            screen_pos = self.world_to_screen_coords(seed.position)
            if screen_pos is None:
                continue

            # 根据选中状态设置颜色
            if i == self._selected_seed_index:
                color = self._selected_seed_color
                pen_width = 3
            else:
                color = self._seed_color
                pen_width = 2

            # 绘制十字标记
            painter.setPen(QPen(color, pen_width))
            size = 4
            painter.drawEllipse(screen_pos, 4, 4)
            # painter.drawLine(
            #     QPointF(screen_pos.x() - size, screen_pos.y()),
            #     QPointF(screen_pos.x() + size, screen_pos.y())
            # )
            # painter.drawLine(
            #     QPointF(screen_pos.x(), screen_pos.y() - size),
            #     QPointF(screen_pos.x(), screen_pos.y() + size)
            # )

            # # 绘制方向指示
            # dx, dy, dz = seed.orientation
            # direction_end = QPointF(
            #     screen_pos.x() + dx * 15,
            #     screen_pos.y() + dy * 15
            # )
            # painter.setPen(QPen(self._direction_color, 1))
            # painter.drawLine(screen_pos, direction_end)

            # 绘制编号
            painter.setPen(QPen(QColor(200, 200, 200), 1))
            painter.drawText(QPointF(screen_pos.x() + 5, screen_pos.y() - 5), str(i + 1))

    # ==================== 工具方法 ====================

    def _query_dose_at_screen_pos(self, screen_pos: QPoint):
        """右键点击CT图像时查询并显示该位置的剂量

        Args:
            screen_pos: 屏幕坐标（相对label）
        """
        world_coords = self.screen_to_world_coords(screen_pos)
        if world_coords is None:
            QToolTip.showText(self.image_label.mapToGlobal(screen_pos),
                              "无法获取世界坐标\n请点击CT图像区域")
            return

        wx, wy, wz = world_coords
        ox, oy, oz = self._dose_origin
        sx, sy, sz = self._dose_spacing

        # 世界坐标 → 剂量网格体素索引（剂量网格与CT对齐，axis顺序为(z,y,x)）
        vx = int(round((wx - ox) / sx))
        vy = int(round((wy - oy) / sy))
        vz = int(round((wz - oz) / sz))

        shape = self._dose_grid.shape
        if vx < 0 or vx >= shape[2] or vy < 0 or vy >= shape[1] or vz < 0 or vz >= shape[0]:
            tip = f"({wx:.1f}, {wy:.1f}, {wz:.1f}) mm\n位置超出剂量网格范围"
            self.dose_queried.emit(tip)
            QToolTip.showText(self.image_label.mapToGlobal(screen_pos), tip)
            return

        total_mGy = float(self._dose_grid[vz, vy, vx])
        rate_uGyh = float(self._dose_rate[vz, vy, vx]) if self._dose_rate is not None else 0.0

        status = (
            f"({wx:.1f}, {wy:.1f}, {wz:.1f}) mm | "
            f"T0剂量率: {rate_uGyh:.2f} μGy/h | "
            f"总积分剂量: {total_mGy:.2f} mGy"
        )
        tip = (
            f"世界坐标: ({wx:.1f}, {wy:.1f}, {wz:.1f}) mm\n"
            f"T0 剂量率: {rate_uGyh:.2f} μGy/h\n"
            f"总积分剂量: {total_mGy:.2f} mGy"
        )
        self.dose_queried.emit(status)
        QToolTip.showText(self.image_label.mapToGlobal(screen_pos), tip)

    def update_display(self):
        """更新显示（重写以包含叠加层）"""
        # 调用父类更新显示
        super()._update_display()

        # 强制重绘叠加层
        self.update()

    def _update_display(self):
        """内部更新显示方法（兼容父类）"""
        self.update_display()

    def set_image_data(self, image_data: dict):
        """
        直接从内存中的image_data恢复CT显示（从项目加载时使用）

        Args:
            image_data: 图像数据字典 (array, spacing, origin, direction)
        """
        self._current_path_points.clear()
        self._seeds.clear()
        self._selected_seed_index = -1
        self._dose_grid = None
        self._dose_rate = None

        self._image_data = image_data
        max_slices = image_data["array"].shape[0] - 1
        self.slice_slider.setMaximum(max_slices)
        self.slice_slider.setValue(max_slices // 2)
        self._current_slice = max_slices // 2

        shape = image_data["array"].shape
        spacing = image_data["spacing"]
        self.info_label.setText(
            f"图像尺寸: {shape[2]}x{shape[1]}x{shape[0]} | "
            f"体素间距: {spacing[0]:.2f}x{spacing[1]:.2f}x{spacing[2]:.2f} mm"
        )
        self._update_display()

    def restore_viewer_state(self, state: dict):
        """
        恢复查看状态（切片、方向、窗宽窗位）

        Args:
            state: 查看状态字典
        """
        axis = state.get("axis", "axial")
        if axis == "axial":
            self.axial_radio.setChecked(True)
        elif axis == "coronal":
            self.coronal_radio.setChecked(True)
        else:
            self.sagittal_radio.setChecked(True)

        ww = int(state.get("window_width", 400))
        wl = int(state.get("window_level", 40))
        self.width_slider.setValue(ww)
        self.level_slider.setValue(wl)

        slice_idx = state.get("slice_index", 0)
        max_val = self.slice_slider.maximum()
        self.slice_slider.setValue(min(slice_idx, max_val))

    def load_image(self, filepath: str):
        """
        加载CT图像（重写以清空路径）

        Args:
            filepath: 图像文件路径
        """
        # 清空当前路径、籽源和剂量数据
        self._current_path_points.clear()
        self._seeds.clear()
        self._selected_seed_index = -1
        self._dose_grid = None
        self._dose_rate = None

        # 调用父类加载图像
        super().load_image(filepath)