#!/usr/bin/env python3
"""
FLUKA lis文件导入脚本

将 FLUKA USRBIN 输出的 .lis 文件（GeV/g/primary）解析并导入为 .npz 格式，注册到数据库。

剂量转换（GeV/g/primary → mGy/primary）由剂量计算引擎自动完成（1 GeV/g = 1.602e-4 mGy），
无需人工输入转换系数。

用法:
    python data/fluka_results/import_fluka_lis.py data/fluka_results/I125_0.5mm.lis --seed-type I-125 --resolution 0.5
"""

import sys
import argparse
from pathlib import Path
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from data.database import get_engine, get_session
from data.models import SeedType, MonteCarloResult
from utils.fluka_parser import parse_fluka_lis


def main():
    parser = argparse.ArgumentParser(
        description="导入FLUKA lis文件（GeV/g/primary）到剂量规划系统"
    )
    parser.add_argument("lis_file", type=str, help="FLUKA .lis 文件路径")
    parser.add_argument(
        "--seed-type", "-s", type=str, required=True,
        help="籽源类型名称 (如 I-125, Pd-103, Cs-131)"
    )
    parser.add_argument(
        "--resolution", "-r", type=float, required=True,
        help="空间分辨率 (mm)，即MC网格bin宽度"
    )
    parser.add_argument(
        "--description", "-d", type=str, default="",
        help="数据描述（可选）"
    )
    parser.add_argument(
        "--output-dir", "-o", type=str, default="data/seeds",
        help="输出目录 (默认: data/seeds)"
    )

    args = parser.parse_args()

    lis_path = Path(args.lis_file)
    if not lis_path.exists():
        print(f"错误: 文件未找到: {lis_path}")
        return 1

    # 1. 解析 lis 文件（原始 FLUKA 单位：GeV/g/primary）
    print(f"解析 FLUKA lis 文件: {lis_path}")
    result = parse_fluka_lis(str(lis_path))

    dose_table = result["dose_table"]
    error_table = result["error_table"]
    r_values = result["r_values"]
    z_values = result["z_values"]
    metadata = result["metadata"]

    print(f"  剂量矩阵: {dose_table.shape} (Nr={dose_table.shape[0]}, Nz={dose_table.shape[1]})")
    print(f"  R 范围: [{r_values[0]:.1f}, {r_values[-1]:.1f}] mm")
    print(f"  Z 范围: [{z_values[0]:.1f}, {z_values[-1]:.1f}] mm")
    print(f"  原始剂量范围 (GeV/g/primary): [{dose_table.min():.4e}, {dose_table.max():.4e}]")

    # 2. 保存为 .npz（保持原始单位 GeV/g/primary，不转换）
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    seed_name = args.seed_type.replace("-", "").replace(" ", "_")
    output_path = output_dir / f"{seed_name}_{args.resolution}mm.npz"

    save_data = {
        "dose_table": dose_table.astype(np.float32),
        "r_values": r_values.astype(np.float32),
        "z_values": z_values.astype(np.float32),
    }
    if error_table is not None:
        save_data["error_table"] = error_table.astype(np.float32)

    np.savez_compressed(str(output_path), **save_data)
    print(f"\n数据已保存: {output_path}")
    print(f"  文件大小: {output_path.stat().st_size / 1024:.1f} KB")
    print(f"  注意: 剂量单位为 GeV/g/primary，计算时自动转换 → mGy")

    # 3. 注册到数据库
    print("\n注册到数据库...")
    engine = get_engine()
    session = get_session(engine)

    # 查找籽源类型
    seed_type = session.query(SeedType).filter(SeedType.name == args.seed_type).first()
    if not seed_type:
        print(f"错误: 数据库中未找到籽源类型 '{args.seed_type}'，请先运行 setup_database.py")
        session.close()
        return 1

    # 检查是否已存在相同路径的记录
    existing = session.query(MonteCarloResult).filter(
        MonteCarloResult.data_path == str(output_path)
    ).first()
    if existing:
        print(f"  该文件已注册 (ID={existing.id})，跳过")
    else:
        description = args.description or f"FLUKA模拟: {args.seed_type}, {args.resolution}mm, 来自 {lis_path.name}"

        record = MonteCarloResult(
            seed_type_id=seed_type.id,
            resolution_mm=args.resolution,
            grid_size_r=dose_table.shape[0],
            grid_size_z=dose_table.shape[1],
            r_max=float(r_values[-1]),
            z_min=float(z_values[0]),
            z_max=float(z_values[-1]),
            data_format="npz",
            data_path=str(output_path),
            dose_unit="GeV/g/primary",
            dose_per_decay=1.0,
            description=description,
            is_verified=True,
        )
        session.add(record)
        session.commit()
        print(f"  注册成功 (ID={record.id})")

    session.close()
    print("\n导入完成！")
    return 0


if __name__ == "__main__":
    sys.exit(main())
