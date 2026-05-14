"""
项目文件读写

每个剂量计算会话保存为一个独立的时间戳命名文件夹:
  projects/YYYY-MM-DD_HH-MM-SS/
    ct_array.npy           # CT 3D 数组
    ct_metadata.json       # spacing, origin, direction, shape, source_filepath
    dose_grid.npz          # {"dose_grid": (mGy), "dose_rate": (μGy/h)}
    dose_metadata.json     # origin, spacing
    seeds.json             # [{position, orientation, seed_type_id, activity}, ...]
    parameters.json        # 计算参数字典
    viewer_state.json      # current_axis, current_slice, window_width, window_level
"""

import json
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List


def create_project_name() -> str:
    """返回当前时间戳字符串 YYYY-MM-DD_HH-MM-SS"""
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def save_project(
    project_dir: str,
    ct_array: np.ndarray,
    ct_metadata: dict,
    dose_grid: Optional[np.ndarray],
    dose_rate: Optional[np.ndarray],
    dose_origin: Optional[tuple],
    dose_spacing: Optional[tuple],
    seeds: list,
    params: dict,
    viewer_state: dict,
    ct_source_path: Optional[str] = None,
):
    """
    保存完整项目到指定目录

    Args:
        project_dir: 项目目录路径
        ct_array: CT 3D 数组
        ct_metadata: CT 元数据 (spacing, origin, direction, shape)
        dose_grid: 总积分剂量 3D 网格 (mGy)，可选
        dose_rate: T0 剂量率 3D 网格 (μGy/h)，可选
        dose_origin: 剂量网格原点 (mm)
        dose_spacing: 剂量网格间距 (mm)
        seeds: 籽源字典列表
        params: 计算参数
        viewer_state: 查看状态
        ct_source_path: 原始 CT 文件路径
    """
    project_path = Path(project_dir)
    project_path.mkdir(parents=True, exist_ok=True)

    # CT 数组
    np.save(str(project_path / "ct_array.npy"), ct_array)

    # CT 元数据
    ct_meta = {
        "spacing": list(ct_metadata["spacing"]),
        "origin": list(ct_metadata["origin"]),
        "direction": ct_metadata["direction"].tolist() if hasattr(ct_metadata["direction"], "tolist") else list(ct_metadata["direction"]),
        "shape": list(ct_metadata["shape"] if "shape" in ct_metadata else ct_array.shape),
    }
    if ct_source_path:
        ct_meta["source_filepath"] = ct_source_path
    with open(project_path / "ct_metadata.json", "w", encoding="utf-8") as f:
        json.dump(ct_meta, f, indent=2, ensure_ascii=False)

    # 剂量网格
    if dose_grid is not None:
        _data = {"dose_grid": dose_grid}
        if dose_rate is not None:
            _data["dose_rate"] = dose_rate
        np.savez_compressed(str(project_path / "dose_grid.npz"), **_data)

    # 剂量元数据
    if dose_origin is not None and dose_spacing is not None:
        dose_meta = {
            "origin": list(dose_origin),
            "spacing": list(dose_spacing),
        }
        with open(project_path / "dose_metadata.json", "w", encoding="utf-8") as f:
            json.dump(dose_meta, f, indent=2, ensure_ascii=False)

    # 籽源
    seeds_serializable = []
    for s in seeds:
        entry = {
            "position": list(s["position"]),
            "orientation": list(s["orientation"]),
            "seed_type_id": s.get("seed_type_id", 1),
            "activity": s.get("activity", 3.0),
        }
        seeds_serializable.append(entry)
    with open(project_path / "seeds.json", "w", encoding="utf-8") as f:
        json.dump(seeds_serializable, f, indent=2, ensure_ascii=False)

    # 参数
    params_copy = dict(params)
    with open(project_path / "parameters.json", "w", encoding="utf-8") as f:
        json.dump(params_copy, f, indent=2, ensure_ascii=False)

    # 查看状态
    vs = {
        "axis": viewer_state.get("axis", "axial"),
        "slice_index": viewer_state.get("slice_index", 0),
        "window_width": viewer_state.get("window_width", 400),
        "window_level": viewer_state.get("window_level", 40),
    }
    with open(project_path / "viewer_state.json", "w", encoding="utf-8") as f:
        json.dump(vs, f, indent=2, ensure_ascii=False)


def load_project(project_dir: str) -> Dict[str, Any]:
    """
    加载完整项目

    Args:
        project_dir: 项目目录路径

    Returns:
        包含所有项目数据的字典，缺失文件的键对应 None
    """
    project_path = Path(project_dir)
    result: Dict[str, Any] = {}

    # CT 数组
    ct_npy = project_path / "ct_array.npy"
    if ct_npy.exists():
        result["ct_array"] = np.load(str(ct_npy))
    else:
        result["ct_array"] = None

    # CT 元数据
    ct_json = project_path / "ct_metadata.json"
    if ct_json.exists():
        with open(ct_json, "r", encoding="utf-8") as f:
            meta = json.load(f)
        result["ct_metadata"] = {
            "spacing": tuple(meta["spacing"]),
            "origin": tuple(meta["origin"]),
            "direction": np.array(meta["direction"]),
            "shape": list(meta["shape"]),
            "source_filepath": meta.get("source_filepath", ""),
        }
    else:
        result["ct_metadata"] = None

    # 剂量网格
    dose_npz = project_path / "dose_grid.npz"
    if dose_npz.exists():
        data = np.load(str(dose_npz))
        result["dose_grid"] = data["dose_grid"]
        result["dose_rate"] = data.get("dose_rate", None)
    else:
        result["dose_grid"] = None
        result["dose_rate"] = None

    # 剂量元数据
    dmeta_json = project_path / "dose_metadata.json"
    if dmeta_json.exists():
        with open(dmeta_json, "r", encoding="utf-8") as f:
            dmeta = json.load(f)
        result["dose_origin"] = tuple(dmeta["origin"])
        result["dose_spacing"] = tuple(dmeta["spacing"])
    else:
        result["dose_origin"] = None
        result["dose_spacing"] = None

    # 籽源
    seeds_json = project_path / "seeds.json"
    if seeds_json.exists():
        with open(seeds_json, "r", encoding="utf-8") as f:
            result["seeds"] = json.load(f)
    else:
        result["seeds"] = []

    # 参数
    params_json = project_path / "parameters.json"
    if params_json.exists():
        with open(params_json, "r", encoding="utf-8") as f:
            result["params"] = json.load(f)
    else:
        result["params"] = {}

    # 查看状态
    vs_json = project_path / "viewer_state.json"
    if vs_json.exists():
        with open(vs_json, "r", encoding="utf-8") as f:
            result["viewer_state"] = json.load(f)
    else:
        result["viewer_state"] = {}

    return result


def list_projects(projects_root: str = "projects") -> List[str]:
    """
    列出所有有效项目文件夹，按名称排序（即按时间排序）

    Args:
        projects_root: 项目根目录

    Returns:
        项目目录路径列表
    """
    root = Path(projects_root)
    if not root.exists():
        return []
    projects = []
    for d in sorted(root.iterdir()):
        if d.is_dir() and (d / "parameters.json").exists():
            projects.append(str(d))
    return projects
