"""
文件读写工具
"""

import numpy as np
from pathlib import Path
from typing import Optional, Dict, Any, Union


def load_npy_data(filepath: Union[str, Path], mmap_mode: Optional[str] = None) -> np.ndarray:
    """
    加载NPY格式数据

    Args:
        filepath: 文件路径
        mmap_mode: 内存映射模式 ('r', 'r+', 'c')

    Returns:
        NumPy数组
    """
    filepath = Path(filepath)

    if not filepath.exists():
        raise FileNotFoundError(f"文件未找到: {filepath}")

    return np.load(str(filepath), mmap_mode=mmap_mode)


def save_dose_npz(
    filepath: Union[str, Path],
    dose_table: np.ndarray,
    r_values: np.ndarray,
    z_values: np.ndarray,
    error_table: Optional[np.ndarray] = None,
):
    """
    保存R-Z剂量数据为npz格式（自描述）

    Args:
        filepath: 输出文件路径
        dose_table: 剂量表 (Nr, Nz)
        r_values: R坐标轴 (Nr,)
        z_values: Z坐标轴 (Nz,)
        error_table: 误差表 (Nr, Nz)，可选
    """
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "dose_table": dose_table,
        "r_values": r_values,
        "z_values": z_values,
    }
    if error_table is not None:
        data["error_table"] = error_table

    np.savez_compressed(str(filepath), **data)


def load_dose_npz(filepath: Union[str, Path]) -> Dict[str, np.ndarray]:
    """
    加载R-Z剂量npz文件

    Args:
        filepath: npz文件路径

    Returns:
        字典，包含 dose_table, r_values, z_values （+ 可选 error_table）
    """
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"文件未找到: {filepath}")
    return dict(np.load(str(filepath)))


def save_npy_data(filepath: Union[str, Path], data: np.ndarray):
    """
    保存数据为NPY格式

    Args:
        filepath: 文件路径
        data: NumPy数组
    """
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    np.save(str(filepath), data)


def load_dicom_series(directory: Union[str, Path]) -> Dict[str, Any]:
    """
    加载DICOM系列

    Args:
        directory: DICOM文件目录

    Returns:
        图像数据字典
    """
    import SimpleITK as sitk

    directory = Path(directory)

    if not directory.exists():
        raise FileNotFoundError(f"DICOM目录未找到: {directory}")

    # 读取DICOM系列
    reader = sitk.ImageSeriesReader()
    dicom_names = reader.GetGDCMSeriesFileNames(str(directory))

    if not dicom_names:
        raise ValueError(f"未找到DICOM文件: {directory}")

    reader.SetFileNames(dicom_names)
    image = reader.Execute()

    # 转换为NumPy数组
    array = sitk.GetArrayFromImage(image)

    return {
        "array": array,
        "spacing": image.GetSpacing(),
        "origin": image.GetOrigin(),
        "direction": np.array(image.GetDirection()).reshape(3, 3),
        "size": image.GetSize(),
        "files": list(dicom_names),
    }


def save_dose_result(
    filepath: Union[str, Path],
    dose_grid: np.ndarray,
    grid_origin: tuple,
    grid_resolution: float,
    metadata: Optional[Dict[str, Any]] = None,
):
    """
    保存剂量计算结果

    Args:
        filepath: 文件路径（支持.npy和.h5）
        dose_grid: 剂量网格
        grid_origin: 网格原点
        grid_resolution: 网格分辨率
        metadata: 元数据
    """
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "dose_grid": dose_grid,
        "grid_origin": np.array(grid_origin),
        "grid_resolution": grid_resolution,
    }

    if metadata:
        data["metadata"] = metadata

    if filepath.suffix == ".npy":
        # 保存为NPZ（多个数组）
        save_dict = {
            "dose_grid": dose_grid,
            "grid_origin": np.array(grid_origin),
            "grid_resolution": np.array([grid_resolution]),
        }
        np.savez_compressed(str(filepath), **save_dict)
    elif filepath.suffix in (".h5", ".hdf5"):
        try:
            import h5py

            with h5py.File(filepath, "w") as f:
                f.create_dataset("dose_grid", data=dose_grid, compression="gzip")
                f.create_dataset("grid_origin", data=grid_origin)
                f.create_dataset("grid_resolution", data=grid_resolution)

                if metadata:
                    for key, value in metadata.items():
                        f.attrs[key] = str(value)
        except ImportError:
            raise ImportError("h5py is required to save HDF5 files")
    else:
        raise ValueError(f"不支持的文件格式: {filepath.suffix}")


def load_dose_result(filepath: Union[str, Path]) -> Dict[str, Any]:
    """
    加载剂量计算结果

    Args:
        filepath: 文件路径

    Returns:
        剂量结果字典
    """
    filepath = Path(filepath)

    if not filepath.exists():
        raise FileNotFoundError(f"文件未找到: {filepath}")

    if filepath.suffix == ".npz":
        data = np.load(filepath)
        return {
            "dose_grid": data["dose_grid"],
            "grid_origin": tuple(data["grid_origin"]),
            "grid_resolution": float(data["grid_resolution"][0]),
        }
    elif filepath.suffix in (".h5", ".hdf5"):
        try:
            import h5py

            with h5py.File(filepath, "r") as f:
                return {
                    "dose_grid": np.array(f["dose_grid"]),
                    "grid_origin": tuple(np.array(f["grid_origin"])),
                    "grid_resolution": float(np.array(f["grid_resolution"])),
                }
        except ImportError:
            raise ImportError("h5py is required to load HDF5 files")
    else:
        raise ValueError(f"不支持的文件格式: {filepath.suffix}")


def load_ct_image(filepath: Union[str, Path]) -> Dict[str, Any]:
    """
    加载CT图像（自动检测格式）

    Args:
        filepath: 文件路径或目录

    Returns:
        图像数据字典
    """
    from core.image_processor import ImageProcessor

    processor = ImageProcessor()
    return processor.load_image(filepath)