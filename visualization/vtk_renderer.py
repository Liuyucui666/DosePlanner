"""
VTK渲染引擎封装
"""

import numpy as np
from typing import Optional, Tuple, List, Dict, Any


class VTKRenderer:
    """VTK渲染引擎"""

    def __init__(self, parent_widget=None):
        """
        初始化渲染器

        Args:
            parent_widget: 父级Qt组件
        """
        self._renderer = None
        self._render_window = None
        self._actors = []
        self._parent = parent_widget
        self._init_renderer()

    def _init_renderer(self):
        """初始化渲染器"""
        try:
            import vtk

            # 创建渲染器
            self._renderer = vtk.vtkRenderer()
            self._renderer.SetBackground(0.1, 0.1, 0.15)

            # 创建渲染窗口
            if self._parent:
                self._render_window = vtk.vtkRenderWindow()
                self._render_window.AddRenderer(self._renderer)

                # 创建窗口交互器
                self._interactor = vtk.vtkRenderWindowInteractor()
                self._interactor.SetRenderWindow(self._render_window)

                # 设置交互样式
                style = vtk.vtkInteractorStyleTrackballCamera()
                self._interactor.SetInteractorStyle(style)

        except ImportError:
            print("Warning: VTK is not available")

    def render_dose_volume(
        self,
        dose_grid: np.ndarray,
        grid_origin: Tuple[float, float, float] = (0, 0, 0),
        grid_spacing: Tuple[float, float, float] = (1, 1, 1),
        opacity: float = 0.7,
    ):
        """
        渲染剂量体积数据

        Args:
            dose_grid: 剂量网格 (3D数组)
            grid_origin: 网格原点
            grid_spacing: 网格间距
            opacity: 不透明度
        """
        try:
            import vtk
            from vtk.util import numpy_support

            # 创建VTK图像数据
            vtk_image = vtk.vtkImageData()
            vtk_image.SetDimensions(dose_grid.shape)
            vtk_image.SetSpacing(grid_spacing)
            vtk_image.SetOrigin(grid_origin)

            # 转换NumPy数组到VTK数组
            flat_data = dose_grid.flatten(order="F")
            vtk_array = numpy_support.numpy_to_vtk(flat_data)
            vtk_array.SetName("Dose")
            vtk_image.GetPointData().AddArray(vtk_array)

            # 创建体积渲染属性
            volume_property = vtk.vtkVolumeProperty()
            volume_property.ShadeOn()
            volume_property.SetInterpolationTypeToLinear()

            # 创建颜色映射函数
            color_func = vtk.vtkColorTransferFunction()
            dose_min = float(np.min(dose_grid))
            dose_max = float(np.max(dose_grid))
            dose_range = dose_max - dose_min

            if dose_range > 0:
                color_func.AddRGBPoint(dose_min, 0.0, 0.0, 0.0)
                color_func.AddRGBPoint(dose_min + dose_range * 0.25, 0.0, 0.0, 1.0)
                color_func.AddRGBPoint(dose_min + dose_range * 0.5, 0.0, 1.0, 0.0)
                color_func.AddRGBPoint(dose_min + dose_range * 0.75, 1.0, 1.0, 0.0)
                color_func.AddRGBPoint(dose_max, 1.0, 0.0, 0.0)

            volume_property.SetColor(color_func)

            # 创建不透明度映射函数
            opacity_func = vtk.vtkPiecewiseFunction()
            opacity_func.AddPoint(dose_min, 0.0)
            opacity_func.AddPoint(dose_min + dose_range * 0.1, opacity * 0.2)
            opacity_func.AddPoint(dose_min + dose_range * 0.5, opacity * 0.6)
            opacity_func.AddPoint(dose_max, opacity)

            volume_property.SetScalarOpacity(opacity_func)

            # 创建体积映射器
            volume_mapper = vtk.vtkSmartVolumeMapper()
            volume_mapper.SetInputData(vtk_image)
            volume_mapper.SetRequestedRenderModeToGPU()

            # 创建体积对象
            volume = vtk.vtkVolume()
            volume.SetMapper(volume_mapper)
            volume.SetProperty(volume_property)

            # 添加到渲染器
            self._renderer.AddVolume(volume)
            self._actors.append(volume)

        except ImportError:
            print("Warning: VTK is not available for dose volume rendering")

    def render_isodose_surface(
        self,
        dose_grid: np.ndarray,
        level: float,
        color: Tuple[float, float, float] = (1, 0, 0),
        opacity: float = 0.5,
    ):
        """
        渲染等剂量面

        Args:
            dose_grid: 剂量网格
            level: 等剂量水平
            color: 颜色 (r, g, b)
            opacity: 不透明度
        """
        try:
            import vtk
            from vtk.util import numpy_support

            # 创建VTK图像数据
            vtk_image = vtk.vtkImageData()
            vtk_image.SetDimensions(dose_grid.shape)
            vtk_image.SetSpacing(1.0, 1.0, 1.0)

            flat_data = dose_grid.flatten(order="F")
            vtk_array = numpy_support.numpy_to_vtk(flat_data)
            vtk_array.SetName("Dose")
            vtk_image.GetPointData().AddArray(vtk_array)

            # 使用Marching Cubes提取等值面
            contour = vtk.vtkMarchingCubes()
            contour.SetInputData(vtk_image)
            contour.ComputeNormalsOn()
            contour.SetValue(0, level)

            # 创建映射器
            mapper = vtk.vtkPolyDataMapper()
            mapper.SetInputConnection(contour.GetOutputPort())
            mapper.ScalarVisibilityOff()

            # 创建演员
            actor = vtk.vtkActor()
            actor.SetMapper(mapper)
            actor.GetProperty().SetColor(color)
            actor.GetProperty().SetOpacity(opacity)

            # 添加到渲染器
            self._renderer.AddActor(actor)
            self._actors.append(actor)

        except ImportError:
            pass

    def render_ct_slice(
        self,
        ct_array: np.ndarray,
        position: Tuple[float, float, float] = (0, 0, 0),
    ):
        """
        渲染CT切片

        Args:
            ct_array: CT切片数据
            position: 切片位置
        """
        try:
            import vtk
            from vtk.util import numpy_support

            # 创建纹理
            height, width = ct_array.shape

            # 归一化到0-255
            ct_normalized = ((ct_array - ct_array.min()) / (ct_array.max() - ct_array.min()) * 255)
            ct_normalized = ct_normalized.astype(np.uint8)

            # 转换为VTK数组
            vtk_array = numpy_support.numpy_to_vtk(ct_normalized.ravel(), deep=True)
            vtk_array.SetNumberOfComponents(1)

            # 创建纹理
            texture = vtk.vtkTexture()
            texture_input = vtk.vtkImageData()
            texture_input.SetDimensions(width, height, 1)
            texture_input.GetPointData().SetScalars(vtk_array)
            texture.SetInputData(texture_input)
            texture.InterpolateOn()

            # 创建平面
            plane = vtk.vtkPlaneSource()
            plane.SetOrigin(-width/2, -height/2, 0)
            plane.SetPoint1(width/2, -height/2, 0)
            plane.SetPoint2(-width/2, height/2, 0)

            # 创建映射器和演员
            mapper = vtk.vtkPolyDataMapper()
            mapper.SetInputConnection(plane.GetOutputPort())

            actor = vtk.vtkActor()
            actor.SetMapper(mapper)
            actor.SetTexture(texture)
            actor.SetPosition(position)

            # 添加到渲染器
            self._renderer.AddActor(actor)
            self._actors.append(actor)

        except ImportError:
            pass

    def add_seed_marker(
        self,
        position: Tuple[float, float, float],
        color: Tuple[float, float, float] = (0, 1, 0),
        size: float = 5.0,
    ):
        """
        添加籽源标记

        Args:
            position: 位置
            color: 颜色
            size: 大小
        """
        try:
            import vtk

            # 创建球体
            sphere = vtk.vtkSphereSource()
            sphere.SetCenter(position)
            sphere.SetRadius(size)

            # 创建映射器和演员
            mapper = vtk.vtkPolyDataMapper()
            mapper.SetInputConnection(sphere.GetOutputPort())

            actor = vtk.vtkActor()
            actor.SetMapper(mapper)
            actor.GetProperty().SetColor(color)

            # 添加到渲染器
            self._renderer.AddActor(actor)
            self._actors.append(actor)

        except ImportError:
            pass

    def add_orientation_indicator(
        self,
        position: Tuple[float, float, float],
        direction: Tuple[float, float, float],
        color: Tuple[float, float, float] = (1, 1, 0),
        length: float = 15.0,
    ):
        """
        添加方向指示器

        Args:
            position: 起点位置
            direction: 方向向量
            color: 颜色
            length: 长度
        """
        try:
            import vtk

            # 创建线
            end_point = (
                position[0] + direction[0] * length,
                position[1] + direction[1] * length,
                position[2] + direction[2] * length,
            )

            line_source = vtk.vtkLineSource()
            line_source.SetPoint1(position)
            line_source.SetPoint2(end_point)

            # 创建映射器和演员
            mapper = vtk.vtkPolyDataMapper()
            mapper.SetInputConnection(line_source.GetOutputPort())

            actor = vtk.vtkActor()
            actor.SetMapper(mapper)
            actor.GetProperty().SetColor(color)
            actor.GetProperty().SetLineWidth(2)

            # 添加到渲染器
            self._renderer.AddActor(actor)
            self._actors.append(actor)

        except ImportError:
            pass

    def add_actor(self, actor):
        """添加演员到场景"""
        self._renderer.AddActor(actor)
        self._actors.append(actor)

    def clear(self):
        """清空场景"""
        for actor in self._actors:
            self._renderer.RemoveActor(actor)
        self._actors.clear()

    def reset_camera(self):
        """重置相机视角"""
        if self._renderer:
            self._renderer.ResetCamera()

    def render(self):
        """渲染场景"""
        if self._render_window:
            self._render_window.Render()

    def get_renderer(self):
        """获取VTK渲染器"""
        return self._renderer

    def get_render_window(self):
        """获取VTK渲染窗口"""
        return self._render_window