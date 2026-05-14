"""
FLUKA lis文件解析器

解析FLUKA USRBIN R-Z柱坐标输出文件，提取剂量矩阵、误差矩阵和坐标轴。
数据布局：FORTRAN矩阵A(ir,iz)，内层循环为ir(R)，外层循环为iz(Z)。
"""

import re
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional


def parse_fluka_lis(filepath: str) -> Dict[str, Any]:
    """
    解析FLUKA lis文件，提取R-Z剂量矩阵。

    Args:
        filepath: FLUKA .lis 文件路径

    Returns:
        {
            "dose_table": np.ndarray (Nr, Nz),     # 原始剂量值
            "error_table": np.ndarray (Nr, Nz),     # 百分比误差
            "r_values": np.ndarray (Nr,),           # R坐标 (mm)
            "z_values": np.ndarray (Nz,),           # Z坐标 (mm)
            "metadata": {
                "r_min_cm": float, "r_max_cm": float,
                "z_min_cm": float, "z_max_cm": float,
                "nr": int, "nz": int,
                "particle_id": int,
                "source_file": str,
            }
        }
    """
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"文件未找到: {filepath}")

    with open(filepath, "r") as f:
        lines = f.readlines()

    # 解析头部提取R/Z参数
    nr, nz = None, None
    r_min_cm, r_max_cm = None, None
    z_min_cm, z_max_cm = None, None
    particle_id = None
    dose_start_line = None
    error_start_line = None

    for i, line in enumerate(lines):
        # 匹配 "R - Z binning n. X , generalized particle n. Y"
        m = re.search(r"generalized particle n\.\s*(\d+)", line)
        if m:
            particle_id = int(m.group(1))

        # 匹配 "R coordinate: from X to Y cm, N bins"
        m = re.search(
            r"R coordinate:\s*from\s+([\d\.\+\-E]+)\s+to\s+([\d\.\+\-E]+)\s+cm,\s*(\d+)\s+bins",
            line,
        )
        if m:
            r_min_cm = float(m.group(1))
            r_max_cm = float(m.group(2))
            nr = int(m.group(3))

        # 匹配 "Z coordinate: from X to Y cm, N bins"
        m = re.search(
            r"Z coordinate:\s*from\s+([\d\.\+\-E]+)\s+to\s+([\d\.\+\-E]+)\s+cm,\s*(\d+)\s+bins",
            line,
        )
        if m:
            z_min_cm = float(m.group(1))
            z_max_cm = float(m.group(2))
            nz = int(m.group(3))

        # 数据起始行（"Data follow..." 后有空行+两行描述→数据从+4行开始）
        if "Data follow in a matrix" in line:
            dose_start_line = i + 4  # 跳过空行 + "accurate deposition..." + "this is a track-length binning"

        # 误差起始行（"Percentage errors..." 后有空行→数据从+2行开始）
        if "Percentage errors follow" in line:
            error_start_line = i + 2  # 跳过空行

    if nr is None or nz is None:
        raise ValueError(f"无法解析R-Z参数: nr={nr}, nz={nz}")
    if dose_start_line is None:
        raise ValueError("未找到剂量数据标记 'Data follow in a matrix'")

    total_values = nr * nz
    lines_per_block = int(np.ceil(nr / 10))  # 每组Z的R值需要多少行
    dose_total_lines = lines_per_block * nz  # 剂量数据总行数

    # 解析剂量数据
    dose_values = _parse_data_block(
        lines, dose_start_line, dose_total_lines, total_values
    )
    dose_table = dose_values.reshape(nr, nz, order="F")  # Fortran order: ir varies fastest

    # 解析误差数据（如果有）
    error_table = None
    if error_start_line is not None:
        error_total_lines = lines_per_block * nz
        error_values = _parse_data_block(
            lines, error_start_line, error_total_lines, total_values
        )
        error_table = error_values.reshape(nr, nz, order="F")

    # 构建坐标轴（转换为mm）
    r_values = np.linspace(r_min_cm * 10, r_max_cm * 10, nr)
    z_values = np.linspace(z_min_cm * 10, z_max_cm * 10, nz)

    return {
        "dose_table": dose_table.astype(np.float64),
        "error_table": error_table.astype(np.float64) if error_table is not None else None,
        "r_values": r_values.astype(np.float64),
        "z_values": z_values.astype(np.float64),
        "metadata": {
            "r_min_cm": r_min_cm,
            "r_max_cm": r_max_cm,
            "z_min_cm": z_min_cm,
            "z_max_cm": z_max_cm,
            "nr": nr,
            "nz": nz,
            "particle_id": particle_id,
            "source_file": str(filepath),
        },
    }


def _parse_data_block(
    lines: list, start_line: int, num_data_lines: int, expected_values: int
) -> np.ndarray:
    """
    解析FORTRAN格式数据块。

    FLUKA格式: (5x,1p,10(1x,e11.4))
    每行: 5空格 + 10个值，每个值占12字符（1空格+e11.4）

    Args:
        lines: 所有行
        start_line: 数据起始行号(0-indexed)
        num_data_lines: 数据行数
        expected_values: 期望的总值数

    Returns:
        一维数值数组
    """
    values = []
    end_line = min(start_line + num_data_lines, len(lines))

    for i in range(start_line, end_line):
        line = lines[i]
        # 跳过空行
        if not line.strip():
            continue
        # FLUKA格式 (5x,1p,10(1x,e11.4)):
        # 跳过前5个空格，然后每12个字符（1空格 + e11.4）一个值
        line_data = line.rstrip("\n")
        if len(line_data) < 5:
            continue
        data_part = line_data[5:]  # 跳过5x
        for j in range(0, min(120, len(data_part)), 12):
            chunk = data_part[j : j + 12].strip()
            if chunk:
                try:
                    values.append(float(chunk))
                except ValueError:
                    # 个别行末尾可能截断，用正则提取
                    pass

    result = np.array(values[:expected_values], dtype=np.float64)
    if len(result) < expected_values:
        raise ValueError(
            f"数据不足: 期望 {expected_values} 个值，实际解析到 {len(result)} 个"
        )
    return result
