"""
主窗口
"""

from pathlib import Path
from PySide6.QtCore import Qt, Signal, Slot, QThread
from PySide6.QtGui import QAction, QKeySequence
import numpy as np
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QMenuBar,
    QMenu,
    QToolBar,
    QStatusBar,
    QMessageBox,
    QFileDialog,
    QDockWidget,
    QApplication,
)

from utils.logging_config import get_logger
from utils.project_io import save_project, load_project, create_project_name
from core.dose_calculator import DoseCalculator

logger = get_logger(__name__)

class ComputeWorker(QThread):
    """后台剂量计算线程"""
    result_ready = Signal(np.ndarray, tuple, tuple, np.ndarray)  # dose_grid, origin, spacing, dose_rate
    progress = Signal(int)  # 0-100 百分比
    error_occurred = Signal(str)

    def __init__(self, seeds, params, ct_grid=None):
        super().__init__()
        self.seeds = seeds
        self.params = params
        self.ct_grid = ct_grid

    def run(self):
        try:
            calc = DoseCalculator()
            grid_res = self.params.get('grid_resolution', 1.0)
            grid_size = self.params.get('grid_size', 32)
            irradiation_time_days = self.params.get('irradiation_time_days', None)

            def on_progress(completed, _total):
                self.progress.emit(int(completed / _total * 100))

            total_dose, origin, dose_rate = calc.calculate_total_dose(
                self.seeds,
                grid_resolution=grid_res,
                grid_size=grid_size,
                progress_callback=on_progress,
                ct_grid=self.ct_grid,
                irradiation_time_days=irradiation_time_days,
            )
            if self.ct_grid:
                spacing = tuple(self.ct_grid["spacing"])
            else:
                spacing = (grid_res, grid_res, grid_res)
            self.result_ready.emit(total_dose, origin, spacing, dose_rate)
        except Exception as e:
            self.error_occurred.emit(str(e))


class MainWindow(QMainWindow):
    """应用程序主窗口"""

    def __init__(self, settings=None):
        """
        初始化主窗口

        Args:
            settings: 应用程序设置
        """
        super().__init__()
        self.settings = settings
        self._current_ct_source = None     # 原始 CT 文件路径
        self._current_project_dir = None   # 当前项目目录（自动保存用）
        self._setup_ui()
        self._create_menus()
        self._create_toolbar()
        self._create_status_bar()
        self._connect_signals()

        logger.info("主窗口初始化完成")

    def _setup_ui(self):
        """设置UI布局"""
        self.setWindowTitle("Dose Planner - 介入科剂量计划软件")
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)

        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 主布局
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(2, 2, 2, 2)

        # 左面板（参数设置）
        self._create_parameter_dock()

        # 中央区域（图像显示和路径编辑）
        self._create_central_area()

        # 右面板（3D可视化）
        self._create_visualization_dock()

    def _create_parameter_dock(self):
        """创建参数设置停靠面板"""
        from .widgets.seed_management_panel import SeedManagementPanel
        self.seed_panel = SeedManagementPanel()
        self.parameter_dock = QDockWidget("参数设置", self)
        self.parameter_dock.setAllowedAreas(
            Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea
        )
        self.parameter_dock.setMinimumWidth(250)
        self.parameter_dock.setWidget(self.seed_panel)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.parameter_dock)

    def _create_central_area(self):
        """创建中央区域"""
        # 图像视图（使用增强型查看器，支持籽源绘制）
        from .widgets.enhanced_image_viewer import EnhancedImageViewer
        self.image_viewer = EnhancedImageViewer()
        self.setCentralWidget(self.image_viewer)

    def _create_visualization_dock(self):
        """创建3D剂量可视化停靠面板"""
        from .widgets.dose_visualizer import DoseVisualizer
        self.visualization_dock = QDockWidget("3D剂量可视化", self)
        self.visualization_dock.setAllowedAreas(
            Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea
        )
        self.visualization_dock.setMinimumWidth(400)

        self.dose_visualizer = DoseVisualizer()
        self.visualization_dock.setWidget(self.dose_visualizer)
        self.addDockWidget(Qt.RightDockWidgetArea, self.visualization_dock)

    def _create_menus(self):
        """创建菜单栏"""
        menubar = self.menuBar()

        # 文件菜单
        file_menu = menubar.addMenu("文件(&F)")

        open_ct_action = QAction("打开CT图像(&O)...", self)
        open_ct_action.setShortcut(QKeySequence.Open)
        open_ct_action.triggered.connect(self._on_open_ct)
        file_menu.addAction(open_ct_action)

        open_ct_dir_action = QAction("打开CT目录(批量)(&D)...", self)
        open_ct_dir_action.triggered.connect(self._on_open_ct_dir)
        file_menu.addAction(open_ct_dir_action)

        open_plan_action = QAction("打开计划(&P)...", self)
        open_plan_action.triggered.connect(self._on_open_plan)
        file_menu.addAction(open_plan_action)

        file_menu.addSeparator()

        save_plan_action = QAction("保存计划(&S)", self)
        save_plan_action.setShortcut(QKeySequence.Save)
        save_plan_action.triggered.connect(self._on_save_plan)
        file_menu.addAction(save_plan_action)

        save_as_action = QAction("另存为(&A)...", self)
        save_as_action.setShortcut(QKeySequence.SaveAs)
        save_as_action.triggered.connect(self._on_save_plan_as)
        file_menu.addAction(save_as_action)

        file_menu.addSeparator()

        export_action = QAction("导出结果(&E)...", self)
        export_action.triggered.connect(self._on_export)
        file_menu.addAction(export_action)

        file_menu.addSeparator()

        exit_action = QAction("退出(&X)", self)
        exit_action.setShortcut(QKeySequence.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # 编辑菜单
        edit_menu = menubar.addMenu("编辑(&E)")

        undo_action = QAction("撤销(&U)", self)
        undo_action.setShortcut(QKeySequence.Undo)
        edit_menu.addAction(undo_action)

        redo_action = QAction("重做(&R)", self)
        redo_action.setShortcut(QKeySequence.Redo)
        edit_menu.addAction(redo_action)

        edit_menu.addSeparator()

        preferences_action = QAction("首选项(&P)...", self)
        preferences_action.triggered.connect(self._on_preferences)
        edit_menu.addAction(preferences_action)

        # 计算菜单
        calc_menu = menubar.addMenu("计算(&C)")

        calculate_action = QAction("计算剂量(&C)", self)
        calculate_action.setShortcut(QKeySequence("F5"))
        calculate_action.triggered.connect(self._on_calculate)
        calc_menu.addAction(calculate_action)

        calc_menu.addSeparator()

        dose_query_action = QAction("位置剂量查询(&Q)...", self)
        dose_query_action.setShortcut(QKeySequence("F6"))
        dose_query_action.triggered.connect(self._on_dose_query)
        calc_menu.addAction(dose_query_action)

        calc_menu.addSeparator()

        clear_action = QAction("清除结果", self)
        clear_action.triggered.connect(self._on_clear_results)
        calc_menu.addAction(clear_action)

        # 视图菜单
        view_menu = menubar.addMenu("视图(&V)")

        view_menu.addAction(self.parameter_dock.toggleViewAction())

        # 帮助菜单
        help_menu = menubar.addMenu("帮助(&H)")

        about_action = QAction("关于(&A)...", self)
        about_action.triggered.connect(self._on_about)
        help_menu.addAction(about_action)

    def _create_toolbar(self):
        """创建工具栏"""
        toolbar = QToolBar("主工具栏", self)
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        # 添加常用操作到工具栏
        open_ct_action = QAction("打开CT", self)
        open_ct_action.triggered.connect(self._on_open_ct)
        toolbar.addAction(open_ct_action)

        save_action = QAction("保存", self)
        save_action.triggered.connect(self._on_save_plan)
        toolbar.addAction(save_action)

        toolbar.addSeparator()

        # 绘制模式切换按钮
        self.drawing_mode_action = QAction("绘制模式", self)
        self.drawing_mode_action.setCheckable(True)
        self.drawing_mode_action.setChecked(False)
        self.drawing_mode_action.toggled.connect(self._on_drawing_mode_toggled)
        toolbar.addAction(self.drawing_mode_action)

        toolbar.addSeparator()

        calculate_action = QAction("计算剂量", self)
        calculate_action.triggered.connect(self._on_calculate)
        toolbar.addAction(calculate_action)

    def _create_status_bar(self):
        """创建状态栏"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪", 5000)

    def _connect_signals(self):
        """连接信号"""
        self.seed_panel.calculate_requested.connect(self._on_calculate)
        # 图像查看器的路径绘制完成信号 → 生成籽源
        self.image_viewer.path_drawn.connect(self._on_path_drawn)
        # 右键剂量查询信号 → 状态栏显示
        self.image_viewer.dose_queried.connect(self._on_dose_queried)
        # 可选：参数变化时在状态栏显示（非必须）
        self.seed_panel.parameters_changed.connect(self._on_parameters_changed)
        self.seed_panel.seeds_changed.connect(self._on_seeds_changed)
        self.seed_panel.clear_path_requested.connect(self.image_viewer.clear_path)
        self.image_viewer.slice_changed.connect(self._on_slice_changed)

    @Slot(bool)
    def _on_drawing_mode_toggled(self, enabled: bool):
        """绘制模式切换回调"""
        if hasattr(self, 'image_viewer') and hasattr(self.image_viewer, 'set_drawing_mode'):
            self.image_viewer.set_drawing_mode(enabled)

            # 更新状态栏提示
            if enabled:
                self.status_bar.showMessage("绘制模式已启用 - 在CT图像上点击绘制籽源路径", 3000)
            else:
                self.status_bar.showMessage("绘制模式已禁用", 2000)

    @Slot(int, str)
    def _on_slice_changed(self, slice_index, axis):
        """CT 切片或方向改变时，更新 3D 视图中的切面平面"""
        if not hasattr(self, 'dose_visualizer'):
            return
        img_data = self.image_viewer.get_image_data()
        if img_data is not None:
            self.dose_visualizer.update_cut_plane(axis, slice_index, img_data)

    @Slot(list)
    def _on_path_drawn(self, path_points):
        """路径绘制完成后，根据当前参数生成籽源，并更新左侧列表"""
        params = self.seed_panel.get_parameters()
        spacing = params['spacing']
        activity = params['activity']
        seed_type_id = self.seed_panel._get_seed_type_id()  # 或者从 mapping 获取

        from core.seed_manager import SeedManager
        seed_manager = SeedManager()
        seed_manager.add_seeds_from_path(
            path_points,
            spacing=spacing,
            seed_type_id=seed_type_id,
            activity=activity,
        )
        seeds = seed_manager.get_seeds_as_dict()
        # 更新左侧面板的列表
        self.seed_panel.set_seeds(seeds)
        self.status_bar.showMessage(f"已生成 {len(seeds)} 颗籽源", 3000)

    @Slot(list)
    def _on_seeds_changed(self, seeds_dict_list):
        """当籽源列表变化时，同步到图像查看器"""
        from core.seed_manager import SeedManager, Seed
        # 将字典列表转换为 Seed 对象列表（图像查看器需要）
        seed_objs = []
        for s in seeds_dict_list:
            seed_objs.append(Seed(
                position=s['position'],
                orientation=s['orientation'],
                seed_type_id=s['seed_type_id'],
                activity=s['activity']
            ))
        self.image_viewer.set_seeds(seed_objs)

    @Slot()
    def _on_open_ct(self):
        """打开CT图像（支持多文件选择）"""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "选择CT图像文件（可多选）",
            "",
            "医学图像文件 (*.dcm *.nii *.nii.gz *.hdr *.img);;DICOM (*.dcm);;NIfTI (*.nii *.nii.gz);;所有文件 (*.*)",
        )

        if file_paths:
            loaded = 0
            errors = []
            for file_path in file_paths:
                try:
                    self.image_viewer.load_image(file_path)
                    loaded += 1
                except Exception as e:
                    errors.append(f"{file_path}: {e}")
                    logger.error(f"CT图像加载失败: {file_path}: {e}")

            if loaded > 0:
                self._current_ct_source = file_paths[0] if len(file_paths) == 1 else None
                self.status_bar.showMessage(f"已加载 {loaded} 个CT图像", 5000)
                logger.info(f"批量加载CT图像成功: {loaded} 个")

            if errors:
                QMessageBox.warning(
                    self, "部分加载失败",
                    f"成功加载 {loaded}/{len(file_paths)} 个文件\n\n失败详情:\n" + "\n".join(errors[:5])
                )

    @Slot()
    def _on_open_ct_dir(self):
        """打开CT目录（导入目录下所有DICOM系列）"""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "选择CT图像目录",
            "",
        )

        if dir_path:
            try:
                from pathlib import Path
                import SimpleITK as sitk

                # 扫描目录下所有DICOM文件
                dcm_files = list(Path(dir_path).glob("*.dcm"))
                dcm_files.extend(Path(dir_path).glob("*.DCM"))
                nii_files = list(Path(dir_path).glob("*.nii"))
                nii_files.extend(Path(dir_path).glob("*.nii.gz"))

                total = len(dcm_files) + len(nii_files)

                if total == 0:
                    QMessageBox.information(self, "提示", f"目录中未找到医学图像文件\n{dir_path}")
                    return

                # 先尝试作为DICOM系列加载
                if dcm_files:
                    try:
                        self.image_viewer.load_image(dir_path)
                        self._current_ct_source = dir_path
                        self.status_bar.showMessage(f"已加载DICOM系列: {dir_path} ({len(dcm_files)}个文件)", 5000)
                        logger.info(f"DICOM系列加载成功: {dir_path}")
                        return
                    except Exception as e:
                        logger.warning(f"DICOM系列加载失败，尝试逐个加载: {e}")

                # 逐个加载NIfTI文件
                loaded = 0
                for nii_file in nii_files:
                    try:
                        self.image_viewer.load_image(str(nii_file))
                        loaded += 1
                    except Exception as e:
                        logger.error(f"NIfTI加载失败: {nii_file}: {e}")

                if loaded > 0:
                    self._current_ct_source = str(nii_files[0]) if len(nii_files) == 1 else dir_path
                    self.status_bar.showMessage(f"已加载 {loaded} 个NIfTI文件", 5000)
                else:
                    QMessageBox.warning(self, "加载失败", "无法加载目录中的医学图像文件")

            except Exception as e:
                QMessageBox.critical(self, "加载错误", f"无法加载CT目录:\n{e}")
                logger.error(f"CT目录加载失败: {e}")

    @Slot()
    def _on_open_plan(self):
        """打开治疗计划（选择项目文件夹）"""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "选择项目文件夹",
            "",
        )
        if dir_path:
            self._load_project_dir(dir_path)

    @Slot()
    def _on_save_plan(self):
        """保存治疗计划（覆盖已有项目目录或另存为）"""
        if self._current_project_dir:
            self._save_to_dir(self._current_project_dir)
            self.status_bar.showMessage(f"项目已保存: {self._current_project_dir}", 5000)
        else:
            self._on_save_plan_as()

    @Slot()
    def _on_save_plan_as(self):
        """另存为治疗计划（选择父目录，自动创建时间戳子文件夹）"""
        parent_dir = QFileDialog.getExistingDirectory(
            self,
            "选择保存位置",
            "",
        )
        if parent_dir:
            from utils.project_io import create_project_name
            project_name = create_project_name()
            project_dir = str(Path(parent_dir) / project_name)
            self._save_to_dir(project_dir)
            self._current_project_dir = project_dir
            self.status_bar.showMessage(f"项目已保存: {project_dir}", 5000)

    @Slot()
    def _on_export(self):
        """导出结果（保存到项目文件夹）"""
        self._on_save_plan_as()

    @Slot()
    def _on_preferences(self):
        """打开首选项对话框"""
        # TODO: 实现首选项对话框
        pass

    @Slot()
    def _on_calculate(self):
        """计算剂量"""
        try:
            # 获取参数
            params = self.seed_panel.get_parameters()
            seeds_data = self.seed_panel.get_seeds()
            if not seeds_data:
                QMessageBox.warning(self, "警告", "请先绘制路径并生成籽源")
                return

            # 提取CT网格参数（如果已加载CT图像）
            ct_grid = None
            if hasattr(self, 'image_viewer') and self.image_viewer._image_data is not None:
                ct_data = self.image_viewer._image_data
                ct_grid = {
                    "origin": tuple(ct_data["origin"]),
                    "spacing": tuple(ct_data["spacing"]),
                    "shape": tuple(ct_data["array"].shape),
                }

            # 更新状态
            self.status_bar.showMessage("正在计算剂量...")
            QApplication.processEvents()

            # 启动后台计算线程
            self.compute_thread = ComputeWorker(seeds_data, params, ct_grid=ct_grid)
            self.compute_thread.result_ready.connect(self._on_dose_computed)
            self.compute_thread.error_occurred.connect(self._on_dose_error)
            self.compute_thread.progress.connect(self._on_calc_progress)
            self.compute_thread.start()

        except Exception as e:
            self.status_bar.showMessage(f"计算失败: {e}", 5000)
            QMessageBox.critical(self, "计算错误", f"剂量计算失败:\n{e}")
            logger.error(f"剂量计算失败: {e}")

    @Slot(np.ndarray, tuple, tuple, np.ndarray)
    def _on_dose_computed(self, dose_grid, origin, spacing, dose_rate):
        """计算完成，更新CT图像上的剂量叠加显示，并自动保存项目"""
        try:
            # 更新 3D 视图
            if hasattr(self, 'dose_visualizer'):
                self.dose_visualizer.display_dose(dose_grid, origin, spacing)

            # 更新 CT 图像上的剂量叠加显示
            if hasattr(self, 'image_viewer') and self.image_viewer._image_data is not None:
                self.image_viewer.set_dose_data(dose_grid, origin, spacing, dose_rate)
                threshold = self.dose_visualizer.isodose_level_mGy
                self.image_viewer.set_dose_threshold(threshold)

            # 如果已加载 CT 图像，同步切面平面（带CT纹理和剂量叠加）
            if hasattr(self, 'dose_visualizer') and hasattr(self, 'image_viewer'):
                img_data = self.image_viewer.get_image_data()
                if img_data is not None:
                    self.dose_visualizer.update_cut_plane(
                        self.image_viewer._current_axis,
                        self.image_viewer._current_slice,
                        img_data
                    )
            
            # 自动保存
            project_name = create_project_name()
            project_dir = str(Path("projects") / project_name)
            self._save_to_dir(project_dir)
            self._current_project_dir = project_dir

            self.status_bar.showMessage(f"剂量计算完成 - 项目已自动保存: {project_dir}", 8000)
            logger.info(f"剂量计算完成，项目已保存: {project_dir}")
        except Exception as e:
            logger.exception("显示剂量时出错")
            QMessageBox.critical(self, "显示错误", f"显示剂量时出错:\n{e}")

    @Slot(int)
    def _on_calc_progress(self, pct):
        """计算进度更新"""
        self.status_bar.showMessage(f"正在计算剂量... {pct}%")

    @Slot(str)
    def _on_dose_error(self, error_msg):
        """计算出错"""
        self.status_bar.showMessage(f"计算失败: {error_msg}", 5000)
        QMessageBox.critical(self, "计算错误", f"剂量计算失败:\n{error_msg}")
        logger.error(f"剂量计算失败: {error_msg}")

    @Slot()
    def _on_dose_query(self):
        """打开位置剂量查询对话框"""
        seeds_data = self.seed_panel.get_seeds()
        if not seeds_data:
            QMessageBox.warning(self, "警告", "请先绘制路径并生成籽源")
            return

        params = self.seed_panel.get_parameters()
        calc = DoseCalculator()
        from .widgets.dose_query_dialog import DoseQueryDialog

        dialog = DoseQueryDialog(calc, seeds_data, params, self)
        dialog.exec_()

    @Slot(str)
    def _on_dose_queried(self, text):
        """右键剂量查询结果在状态栏显示"""
        self.status_bar.showMessage(text, 8000)

    @Slot()
    def _on_clear_results(self):
        """清除计算结果"""
        # TODO: 实现结果清除
        pass

    @Slot()
    def _on_about(self):
        """显示关于对话框"""
        QMessageBox.about(
            self,
            "关于 Dose Planner",
            "<h3>Dose Planner v0.1.0</h3>"
            "<p>介入科放射性籽源植入剂量计划软件</p>"
            "<p>用于放射性籽源植入治疗的剂量计划计算和可视化。</p>"
            "<hr>"
            "<p>技术栈: Python, PySide6, SimpleITK</p>",
        )

    @Slot()
    def _on_parameters_changed(self, parameters):
        """参数变更处理"""
        logger.debug(f"参数已变更: {parameters}")
        self.status_bar.showMessage(
            f"参数: 活度={parameters.get('activity', 'N/A')} mCi, "
            f"间距={parameters.get('spacing', 'N/A')} mm",
            3000,
        )

    def _save_to_dir(self, project_dir: str):
        """收集当前状态并调用 save_project()"""
        ct_data = self.image_viewer._image_data
        if ct_data is None:
            QMessageBox.warning(self, "警告", "没有CT图像数据可保存")
            return

        ct_array = ct_data["array"]
        ct_metadata = {
            "spacing": ct_data["spacing"],
            "origin": ct_data["origin"],
            "direction": ct_data["direction"],
        }

        dose_grid = self.image_viewer._dose_grid
        dose_rate = self.image_viewer._dose_rate
        dose_origin = self.image_viewer._dose_origin
        dose_spacing = self.image_viewer._dose_spacing

        seeds = self.seed_panel.get_seeds()
        params = self.seed_panel.get_parameters()
        viewer_state = self.image_viewer.get_current_slice_info()

        save_project(
            project_dir=project_dir,
            ct_array=ct_array,
            ct_metadata=ct_metadata,
            dose_grid=dose_grid,
            dose_rate=dose_rate,
            dose_origin=dose_origin,
            dose_spacing=dose_spacing,
            seeds=seeds,
            params=params,
            viewer_state=viewer_state,
            ct_source_path=self._current_ct_source,
        )

    def _load_project_dir(self, project_dir: str):
        """从项目目录加载并恢复全部状态"""
        try:
            data = load_project(project_dir)
        except Exception as e:
            QMessageBox.critical(self, "加载错误", f"无法加载项目:\n{e}")
            logger.error(f"项目加载失败: {e}")
            return

        # 恢复 CT
        ct_array = data.get("ct_array")
        ct_meta = data.get("ct_metadata")
        if ct_array is not None and ct_meta is not None:
            self.image_viewer.set_image_data({
                "array": ct_array,
                "spacing": ct_meta["spacing"],
                "origin": ct_meta["origin"],
                "direction": ct_meta["direction"],
            })
            self._current_ct_source = ct_meta.get("source_filepath", "")

        # 恢复剂量
        dose_grid = data.get("dose_grid")
        dose_origin = data.get("dose_origin")
        dose_spacing = data.get("dose_spacing")
        dose_rate = data.get("dose_rate")
        if dose_grid is not None and dose_origin is not None and dose_spacing is not None:
            self.image_viewer.set_dose_data(dose_grid, dose_origin, dose_spacing, dose_rate)

        # 恢复参数和籽源
        if data.get("params"):
            self.seed_panel.set_parameters(data["params"])
        if data.get("seeds"):
            self.seed_panel.set_seeds(data["seeds"])

        # 恢复查看状态
        if data.get("viewer_state"):
            self.image_viewer.restore_viewer_state(data["viewer_state"])

        self._current_project_dir = project_dir
        self.status_bar.showMessage(f"项目已加载: {project_dir}", 5000)
        logger.info(f"项目加载成功: {project_dir}")

    def closeEvent(self, event):
        """关闭事件"""
        # TODO: 检查是否有未保存的更改
        reply = QMessageBox.question(
            self,
            "确认退出",
            "确定要退出程序吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            logger.info("应用程序正常退出")
            event.accept()
        else:
            event.ignore()