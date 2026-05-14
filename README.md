# Dose Planner - 介入科剂量计划软件

用于放射性籽源植入治疗的剂量计划桌面软件。基于 FLUKA 蒙特卡洛预计算的 R-Z 柱坐标剂量表（GeV/g/primary），结合核素衰变时间积分实现物理精确的剂量计算，支持 CT 图像引导下的籽源路径规划和 2D 剂量叠加显示。

## 功能特性

- **CT 图像加载**：支持 DICOM 目录/文件、NIfTI (.nii/.nii.gz) 格式
- **籽源路径规划**：在 CT 图像上交互式绘制籽源路径，自动按间距生成籽源
- **剂量计算**：基于 FLUKA 蒙特卡洛预计算数据（GeV/g/primary）的 R-Z 柱坐标查表 + 核素衰变时间积分，逐籽源独立子 ROI 计算（内存友好）
- **2D 剂量叠加**：剂量色图半透明叠加于 CT 切面，支持轴向/冠状/矢状三视图，随切片滚动实时更新
- **位置剂量查询**：输入世界坐标查询（F6），或剂量计算后右键点击 CT 图像，显示 T0 时刻剂量率（μGy/h）和总积分剂量（mGy）
- **结果分析**：剂量体积直方图 (DVH)、等剂量面提取、D95/V100 指标

## 系统要求

- Python 3.9+
- 支持的操作系统：Windows 10/11、macOS、Linux
- **Windows 用户**：PySide6/Qt6 需要 MSVC 运行时，若 DLL 加载失败，程序会自动使用 PyQt5 后端（通过 qtpy 抽象层）

## 安装

### 1. 创建虚拟环境并安装依赖

```bash
cd dosePlannerV1.0.0
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/macOS
source venv/bin/activate

pip install -e ".[full]"
```

核心依赖：numpy, scipy, qtpy, SimpleITK, sqlalchemy, pydantic, joblib, loguru
可选依赖：pydicom, h5py, matplotlib

### 2. 初始化数据库

```bash
python scripts/setup_database.py
```

这会创建 SQLite 数据库并插入默认籽源类型（I-125、Pd-103、Cs-131）。

### 3. 导入 FLUKA 蒙特卡洛数据

```bash
python scripts/import_fluka_lis.py data/fluka_results/I125_0.5mm.lis --seed-type I-125 --resolution 0.5
```

- FLUKA 数据单位为 **GeV/g/primary**，程序自动完成物理单位转换（1 GeV/g = 1.602e-4 mGy）
- `.lis` 文件为 FLUKA USRBIN 输出，支持 FORTRAN `(5x,1p,10(1x,e11.4))` 格式

## 启动程序

```bash
python -m dose_planner.main
```

或通过 setuptools 安装后：
```bash
dose-planner
```

## 使用流程

1. **加载 CT**：文件 → 打开CT图像（支持单文件 .dcm/.nii 或多文件 DICOM 目录）
2. **进入绘制模式**：点击工具栏"绘制模式"按钮（或切换为 Checked 状态）
3. **绘制籽源路径**：在 CT 图像上点击/拖拽绘制穿刺路径
4. **调整参数**：在左侧面板设置籽源活度（mCi）、间距、照射时间（或勾选永久植入）
5. **计算剂量**：点击"计算剂量"按钮（或 F5），后台异步计算
6. **查看结果**：剂量色图半透明叠加于 CT 切片，切换切片/视图可浏览各方向剂量分布
7. **位置剂量查询**：计算 → 位置剂量查询（F6）输入坐标查询，或剂量计算后右键点击 CT 图像直接查询

### 关键参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| 籽源类型 | I-125 / Pd-103 / Cs-131 | I-125 |
| 活度 | 籽源放射性活度 | 3.0 mCi |
| 间距 | 路径上籽源间隔 | 10 mm |
| 照射时间 | 有限照射天数；永久植入时 ∞ | 90 天 |
| 网格分辨率 | CT 模式下自动与 CT 一致 | CT spacing |
| 剂量单位 | 总积分剂量 / 剂量率 | mGy / μGy/h |
| 剂量查询 | F6 菜单或右键点击 CT | — |

## 项目结构

```
dosePlannerV1.0.0/
├── src/dose_planner/
│   ├── main.py              # 程序入口
│   ├── config/              # 配置常量
│   ├── core/                # 核心引擎
│   │   ├── dose_calculator.py   # R-Z 柱坐标剂量引擎
│   │   ├── seed_manager.py      # 籽源管理
│   │   ├── image_processor.py   # CT 图像处理
│   │   └── transform.py         # 坐标转换
│   ├── data/                # 数据层（SQLAlchemy ORM）
│   │   ├── models.py        # 数据库模型
│   │   ├── repositories.py  # 数据访问
│   │   └── database.py      # 初始化/会话管理
│   ├── gui/
│   │   ├── main_window.py          # 主窗口
│   │   └── widgets/
│   │       ├── enhanced_image_viewer.py  # CT 视图+剂量叠加
│   │       ├── dose_query_dialog.py      # 位置剂量查询
│   │       ├── seed_management_panel.py  # 参数面板
│   │       └── image_viewer.py           # 基础 CT 查看器
│   ├── utils/
│   │   ├── fluka_parser.py   # FLUKA .lis 解析
│   │   └── file_io.py        # 文件读写
│   └── tests/                # 单元测试
├── scripts/
│   ├── setup_database.py     # 数据库初始化
│   └── import_fluka_lis.py   # FLUKA 数据导入
├── data/
│   └── fluka_results/        # 蒙特卡洛预计算数据 (.npz)
└── pyproject.toml
```

## 运行测试

```bash
# Windows（避免 PySide6 DLL 错误）
PYTEST_QT_API=pyqt5 python -m pytest src/dose_planner/tests/ -v -p no:qt

# Linux/macOS
pytest src/dose_planner/tests/ -v
```

## 许可证

MIT License.
