#!/usr/bin/env python3
"""Plot representative spectral curves from the Salinas hyperspectral scene.

Default inputs:
  data/Salinas_corrected.mat
  data/Salinas_gt.mat

Default output:
  T2/2.png
"""

from __future__ import annotations

import argparse
import os
import time
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", str(Path(".matplotlib").resolve()))

import matplotlib.pyplot as plt
import numpy as np

try:
    import cupy as cp
    _cuda_available = cp.cuda.is_available()
except ImportError:
    cp = None
    _cuda_available = False

from hsi_utils import infer_dataset_key, label_for_class, load_cube, load_ground_truth, parse_classes, spectral_axis


def compute_mean_spectra(
    cube: np.ndarray,
    gt: np.ndarray,
    class_ids: list[int],
) -> tuple[np.ndarray, list[int]]:
    MAX_MEMORY_BYTES = 1024 * 1024 * 1024  # 1GB

    gt_flat = gt.ravel()
    valid_mask = gt_flat != 0

    if np.sum(valid_mask) == 0:
        raise ValueError("No valid pixels (non-zero) in ground-truth image")

    class_to_idx = {cls: i for i, cls in enumerate(class_ids)}
    filtered_mask = np.isin(gt_flat, class_ids)
    N = np.sum(filtered_mask)

    if N == 0:
        raise ValueError("No pixels found for the specified classes")

    K = len(class_ids)
    B = cube.shape[2]

    # 安全检查：防止极大影像导致内存溢出
    required_memory = N * (B + K) * 4
    if required_memory > MAX_MEMORY_BYTES:
        raise MemoryError(
            f"Estimated memory requirement ({required_memory / (1024**3):.2f} GB) "
            f"exceeds 1GB limit. Consider reducing the number of classes or using a smaller subset."
        )

    cube_valid = cube.reshape(-1, B)[filtered_mask].astype(np.float32)
    gt_valid = gt_flat[filtered_mask]

    # 优化：使用纯 NumPy 向量化构造 One-Hot 矩阵，消灭 for 循环
    one_hot = np.zeros((N, K), dtype=np.float32)
    # 将真实的类别 ID 映射到 0~K-1 的列索引上
    mapped_indices = np.array([class_to_idx[c] for c in gt_valid])
    one_hot[np.arange(N), mapped_indices] = 1.0

    # 开始计时
    start_time = time.perf_counter()

    if _cuda_available:
        one_hot_gpu = cp.array(one_hot)
        cube_valid_gpu = cp.array(cube_valid)
        sums_gpu = cp.dot(one_hot_gpu.T, cube_valid_gpu)
        counts_gpu = cp.sum(one_hot_gpu, axis=0, keepdims=True).T
        # 同步 GPU 并将数据搬回 CPU
        cp.cuda.Stream.null.synchronize()
        sums = cp.asnumpy(sums_gpu)
        counts = cp.asnumpy(counts_gpu)
    else:
        sums = np.dot(one_hot.T, cube_valid)
        counts = np.sum(one_hot, axis=0, keepdims=True).T

    # 结束计时
    elapsed_time = time.perf_counter() - start_time

    counts[counts == 0] = 1
    mean_spectra = sums / counts

    # 统计各主要数组的内存占用
    mem_cube_valid = cube_valid.nbytes
    mem_one_hot = one_hot.nbytes
    mem_sums = sums.nbytes
    mem_counts = counts.nbytes
    mem_mean = mean_spectra.nbytes
    total_mem = mem_cube_valid + mem_one_hot + mem_sums + mem_counts + mem_mean

    return mean_spectra, class_ids, elapsed_time, total_mem, {
        "cube_valid": mem_cube_valid,
        "one_hot": mem_one_hot,
        "sums": mem_sums,
        "counts": mem_counts,
        "mean_spectra": mem_mean,
    }


def normalize_spectrum(spectrum: np.ndarray, method: str) -> np.ndarray:
    arr = spectrum.astype(np.float32, copy=True)
    if method == "minmax":
        lo, hi = float(arr.min()), float(arr.max())
        if hi > lo:
            return (arr - lo) / (hi - lo)
        return np.zeros_like(arr)
    if method == "l2":
        norm = float(np.linalg.norm(arr))
        if norm > 0:
            return arr / norm
        return arr
    return arr


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cube", type=Path, default=Path("data/Salinas_corrected.mat"))
    parser.add_argument("--gt", type=Path, default=Path("data/Salinas_gt.mat"))
    parser.add_argument("--output", type=Path, default=Path("T2/2.png"))
    parser.add_argument("--cube-variable", help="Name of the 3-D image variable inside the .mat file.")
    parser.add_argument("--gt-variable", help="Name of the 2-D ground-truth variable inside the .mat file.")
    parser.add_argument(
        "--classes",
        default=None,
        help="Comma-separated class ids to plot. If omitted, all non-zero classes are used.",
    )
    parser.add_argument(
        "--x-axis",
        choices=("wavelength", "band"),
        default="wavelength",
        help="Use approximate wavelength or band number on the spectral curve x-axis.",
    )
    parser.add_argument(
        "--normalize",
        choices=("none", "minmax", "l2"),
        default="none",
        help="Optional normalization for each plotted mean spectrum.",
    )
    parser.add_argument("--seed", type=int, default=2025, help="Random seed (not used in current implementation)")
    return parser.parse_args()


def main() -> None:
    import tracemalloc
    import time

    tracemalloc.start()
    start_time = time.time()

    args = parse_args()
    cube, cube_variable = load_cube(args.cube, args.cube_variable)
    gt, gt_variable = load_ground_truth(args.gt, cube.shape[:2], args.gt_variable)
    
    # 修改逻辑：如果不传 --classes，默认获取全地物（所有非零类别）
    if args.classes:
        class_ids = parse_classes(args.classes, gt)
    else:
        # 自动提取 GT 中所有大于 0 的类别，并按 ID 排序
        class_ids = sorted([int(c) for c in np.unique(gt) if c != 0])

    dataset_key = infer_dataset_key(str(args.cube), cube_variable, str(args.gt), gt_variable)

    # 接收计算结果和运行时间
    mean_spectra, class_ids, elapsed_time, total_mem, mem_breakdown = compute_mean_spectra(cube, gt, class_ids)

    x, xlabel = spectral_axis(dataset_key, cube.shape[2], prefer_wavelength=args.x_axis == "wavelength")
    ylabel = "Mean at-sensor radiance value (a.u.)"
    if args.normalize == "minmax":
        ylabel = "Min-max normalized mean spectrum"
    elif args.normalize == "l2":
        ylabel = "L2-normalized mean spectrum"

    plt.figure(figsize=(10, 6), dpi=160)
    for i, class_id in enumerate(class_ids):
        spectrum = mean_spectra[i]
        spectrum = normalize_spectrum(spectrum, args.normalize)
        label = label_for_class(dataset_key, class_id)
        plt.plot(x, spectrum, linewidth=1.6, label=f"{class_id}: {label}")

    plt.title("Representative spectral profiles in Salinas scene (All Classes)")
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.grid(True, alpha=0.3)
    plt.legend(fontsize=8, ncol=2) # 类别较多，分两列显示图例
    plt.tight_layout()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(args.output)
    plt.close()

    end_time = time.time()
    total_time = end_time - start_time

    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    gpu_status = "GPU (CuPy)" if _cuda_available else "CPU (NumPy)"
    print(f"Saved spectral-curve plot to {args.output}")
    print(f"Total elapsed time (main function): {total_time:.4f} seconds")
    print(f"Cube variable: {cube_variable}; GT variable: {gt_variable}; shape: {cube.shape}")
    print(f"Total Classes count: {len(class_ids)}")
    print(f"Classes: {class_ids}")
    print(f"X-axis: {args.x_axis}; normalization: {args.normalize}")
    print(f"Computation device: {gpu_status}; Matrix multiplication time: {elapsed_time:.4f} seconds")
    print(f"--- Memory usage ---")
    print(f"  cube_valid  ({'N':>7} x {'B':>3} float32): {mem_breakdown['cube_valid'] / (1024**2):>8.2f} MB")
    print(f"  one_hot     ({'N':>7} x {'K':>3} float32): {mem_breakdown['one_hot'] / (1024**2):>8.2f} MB")
    print(f"  sums        ({'K':>7} x {'B':>3} float32): {mem_breakdown['sums'] / (1024**2):>8.2f} MB")
    print(f"  counts      ({'K':>7} x {'1':>3} float32): {mem_breakdown['counts'] / (1024**2):>8.2f} MB")
    print(f"  mean_spectra({'K':>7} x {'B':>3} float32): {mem_breakdown['mean_spectra'] / (1024**2):>8.2f} MB")
    print(f"  Total compute arrays:                {total_mem / (1024**2):>8.2f} MB")
    print(f"  Peak memory (tracemalloc):           {peak / (1024**2):>8.2f} MB")


if __name__ == "__main__":
    main()
