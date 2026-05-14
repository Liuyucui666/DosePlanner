# gui/widgets/dose_visualizer.py
"""
3D剂量分布可视化组件（固定视角+人体模型+半透明切面+绝对剂量等值面）
使用PyVista实现，切面为半透明平面，不显示CT纹理。
"""

import numpy as np
from typing import Optional, Dict, Any

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QGroupBox
)

from config.constants import VisualizationConstants


class DoseVisualizer(QWidget):
    """3D剂量分布可视化组件"""

    # 信号：当切面更新时通知外部
    cut_plane_changed = Signal(str, int)  # axis, slice_index

    def __init__(self, parent=None):
        super().__init__(parent)
        self._dose_grid = None
        self._grid_origin = (0, 0, 0)
        self._grid_spacing = (1.0, 1.0, 1.0)

        # CT图像数据（用于计算包围盒、切面定位）
        self._image_data = None

        # 当前切面参数
        self._current_cut_axis = None
        self._current_cut_slice = None

        # 固定场景元素引用
        self._body_actor = None        # 人体模型
        self._cut_plane_actor = None   # 切面指示平面
        self._isodose_actors = []      # 等剂量面列表

        # 默认等剂量水平 (mGy)
        self.isodose_level_mGy = 200.0

        # CT数据导入（HU）
        self._body_threshold = -500  
        self._body_actor = None
        self._first_ct_loaded = True    # 标记是否首次加载 CT
        self._old_ct_shape = None
        self._body_actor = None

        self._setup_ui()

    def _setup_ui(self):
        """设置UI布局"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 35, 5, 5)

        title_label = QLabel("3D剂量分布")
        title_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        main_layout.addWidget(title_label)

        # PyVista渲染窗口
        self._init_vtk_widget()
        main_layout.addWidget(self._render_widget, stretch=1)

        # 精简控制栏（只保留刷新与截图）
        control_layout = QHBoxLayout()
        self.refresh_btn = QPushButton("刷新剂量")
        self.refresh_btn.clicked.connect(self._on_refresh_dose)
        control_layout.addWidget(self.refresh_btn)

        self.screenshot_btn = QPushButton("截图")
        self.screenshot_btn.clicked.connect(self._on_screenshot)
        control_layout.addWidget(self.screenshot_btn)
        control_layout.addStretch()
        main_layout.addLayout(control_layout)

        self.info_label = QLabel("等待计算结果")
        self.info_label.setStyleSheet("color: gray; font-size: 10px;")
        main_layout.addWidget(self.info_label)

    def _init_vtk_widget(self):
        """初始化VTK渲染窗口并设置固定视角和人体模型"""
        try:
            import pyvista as pv
            from pyvistaqt import QtInteractor

            self.plotter = QtInteractor(self)
            self._render_widget = self.plotter
            self.plotter.set_background("black")
            self.plotter.show_axes()
            self.plotter.camera_position = 'iso'
        except ImportError:
            self._render_widget = QLabel("3D视图 (需要安装pyvistaqt)")
            self._render_widget.setAlignment(Qt.AlignCenter)
            self._render_widget.setStyleSheet("background-color: #1e1e1e; color: gray;")
            self.plotter = None

    # ==================== 公开接口 ====================

    def display_dose(self, dose_grid: np.ndarray, grid_origin=None, grid_spacing=None):
        """显示剂量分布，重建场景（等值面等）"""
        self._dose_grid = dose_grid
        self._grid_origin = grid_origin if grid_origin else (0,0,0)
        self._grid_spacing = grid_spacing if grid_spacing else (1,1,1)

        for actor in self._isodose_actors:
            self.plotter.remove_actor(actor)
        self._isodose_actors = []
        if self._cut_plane_actor is not None:
            self.plotter.remove_actor(self._cut_plane_actor)
            self._cut_plane_actor = None

        # 重新创建切面（如果有当前轴信息）
        if self._current_cut_axis and self._image_data is not None:
            self._add_cut_plane(self._current_cut_axis, self._current_cut_slice,
                                self._image_data)

        # 添加等值面
        self._add_isodose_surfaces(dose_grid, grid_origin, grid_spacing)
        self.plotter.render()

        self.info_label.setText(
            f"剂量范围: {dose_grid.min():.1f} - {dose_grid.max():.1f} mGy | "
            f"等剂量面: {self.isodose_level_mGy} mGy"
        )

    def update_cut_plane(self, axis, slice_index, image_data):
        """更新切面，并在首次加载CT时重建体表"""
        self._image_data = image_data

        # 如果是第一次加载 CT，或者 CT 形状发生变化，重建体表
        if self._first_ct_loaded or (image_data is not None and self._old_ct_shape != image_data['array'].shape):
            self._update_body_surface(image_data)
            self._first_ct_loaded = False
            self._old_ct_shape = image_data['array'].shape
            # 重置相机以显示完整患者
            self.plotter.reset_camera()

        # 移除旧切面
        if self._cut_plane_actor is not None:
            self.plotter.remove_actor(self._cut_plane_actor)
            self._cut_plane_actor = None

        # 添加新切面
        self._add_cut_plane(axis, slice_index, image_data)

        self._current_cut_axis = axis
        self._current_cut_slice = slice_index
        self.plotter.render()

    def clear_display(self):
        """清空剂量和切面，但保留患者模型"""
        if self.plotter:
            for actor in self._isodose_actors:
                self.plotter.remove_actor(actor)
            self._isodose_actors = []
            if self._cut_plane_actor:
                self.plotter.remove_actor(self._cut_plane_actor)
                self._cut_plane_actor = None
            self.plotter.render()

    # 在 DoseVisualizer 类中添加
    def reset_view(self):
        """重置相机以包含所有场景物体"""
        if self.plotter:
            self.plotter.reset_camera()
            self.plotter.render()

    # ==================== 场景构建方法 ====================

    def _update_body_surface(self, image_data):
        import pyvista as pv

        if self._body_actor is not None:
            self.plotter.remove_actor(self._body_actor)
            self._body_actor = None

        if image_data is None:
            return

        array = image_data['array']                    # (z, y, x)
        spacing = image_data['spacing']                # (sx, sy, sz)
        origin = image_data['origin']                  # (ox, oy, oz)

        # 降采样加速（可选）
        stride = 2  # 可根据需求调整
        if stride > 1:
            array = array[::stride, ::stride, ::stride]
            spacing = (spacing[0] * stride, spacing[1] * stride, spacing[2] * stride)

        nz, ny, nx = array.shape

        # 创建 ImageData，dimensions = 顶点数 = 体素数 + 1
        grid = pv.ImageData()
        grid.dimensions = np.array([nx + 1, ny + 1, nz + 1])   # ← 关键修正
        grid.origin = origin
        grid.spacing = spacing

        # 体素数据存入 cell_data
        grid.cell_data['HU'] = array.transpose(2, 1, 0).flatten(order='F')
        # 转换为点数据（用于 contour）
        grid = grid.cell_data_to_point_data()

        # 提取表面
        try:
            body_mesh = grid.contour(isosurfaces=[self._body_threshold], scalars='HU')
        except Exception as e:
            print(f"体表提取失败: {e}")
            return

        if body_mesh.n_points == 0:
            return

        # 平滑处理
        body_mesh = body_mesh.smooth(n_iter=20, relaxation_factor=0.1)

        # 显示不透明体表
        self._body_actor = self.plotter.add_mesh(
            body_mesh,
            color='#FFDBB4',   # 肉色
            opacity=1,
            smooth_shading=True,
            label='患者体表'
        )

    def _add_cut_plane(self, axis: str, slice_index: int, image_data: Dict[str, Any]):
        """添加半透明切面指示平面（无纹理）"""
        import pyvista as pv

        array = image_data['array']
        origin = np.array(image_data['origin'])
        spacing = np.array(image_data['spacing'])
        direction = np.array(image_data['direction']).reshape(3, 3)

        # 根据视图方向提取切片参数
        if axis == 'axial':
            img_center_y = (array.shape[1] - 1) / 2
            img_center_x = (array.shape[2] - 1) / 2
            point_local = np.array([img_center_x, img_center_y, slice_index])
            normal_local = np.array([0, 0, 1])
            phys_width = array.shape[2] * spacing[0]   # x extent
            phys_height = array.shape[1] * spacing[1]  # y extent
        elif axis == 'coronal':
            img_center_x = (array.shape[2] - 1) / 2
            img_center_z = (array.shape[0] - 1) / 2
            point_local = np.array([img_center_x, slice_index, img_center_z])
            normal_local = np.array([0, 1, 0])
            phys_width = array.shape[2] * spacing[0]
            phys_height = array.shape[0] * spacing[2]
        else:  # sagittal
            img_center_y = (array.shape[1] - 1) / 2
            img_center_z = (array.shape[0] - 1) / 2
            point_local = np.array([slice_index, img_center_y, img_center_z])
            normal_local = np.array([1, 0, 0])
            phys_width = array.shape[1] * spacing[1]
            phys_height = array.shape[0] * spacing[2]

        # 世界坐标中心与法线
        world_center = origin + direction @ (spacing * point_local)
        normal_world = direction @ normal_local
        normal_world = normal_world / np.linalg.norm(normal_world)

        # 创建半透明平面
        plane = pv.Plane(
            center=world_center,
            direction=normal_world,
            i_size=phys_width,
            j_size=phys_height
        )

        self._cut_plane_actor = self.plotter.add_mesh(
            plane,
            color='#90CAF9',
            opacity=0.65,       # 提高至 0.65，增强实体感
            lighting=False,     # 关闭光照使颜色更纯
            label=f'{axis} 切面 (切片 {slice_index})'
        )

    def _add_isodose_surfaces(self, dose_grid, origin, spacing):
        """添加绝对剂量等值面（默认 200 mGy）"""
        import pyvista as pv

        if dose_grid is None or np.max(dose_grid) <= 0:
            return

        nz, ny, nx = dose_grid.shape
        grid = pv.ImageData()
        grid.dimensions = np.array([nx + 1, ny + 1, nz + 1])
        grid.origin = origin
        grid.spacing = spacing
        grid.cell_data['dose'] = dose_grid.transpose(2, 1, 0).flatten(order='F')
        grid = grid.cell_data_to_point_data()

        level = self.isodose_level_mGy
        try:
            contour = grid.contour(isosurfaces=[level], scalars='dose')
            actor = self.plotter.add_mesh(
                contour,
                color='red',
                opacity=0.6,
                label=f'{level:.0f} mGy 等剂量面'
            )
            self._isodose_actors.append(actor)
        except Exception as e:
            print(f"等值面提取失败: {e}")

    # ==================== 按钮回调 ====================

    def _on_refresh_dose(self):
        """刷新剂量显示"""
        if self._dose_grid is not None:
            self.display_dose(self._dose_grid, self._grid_origin, self._grid_spacing)

    def _on_screenshot(self):
        """截图保存"""
        if self.plotter:
            from PySide6.QtWidgets import QFileDialog
            file_path, _ = QFileDialog.getSaveFileName(
                self, "保存截图", "",
                "PNG图像 (*.png);;JPEG图像 (*.jpg)"
            )
            if file_path:
                self.plotter.screenshot(file_path)
                self.info_label.setText(f"截图已保存: {file_path}")

    def get_plotter(self):
        return self.plotter