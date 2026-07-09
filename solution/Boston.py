#!/usr/bin/env python3
"""Compute per-band statistics for the Boston GeoTIFF under a 1 GB memory limit.

Default input:
  Boston.tif

The script reads the image by row stripes and reports each band's mean,
standard deviation, maximum and minimum values.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import rasterio
from rasterio.windows import Window


def merge_block_stats(
    count_old: int,
    mean_old: float,
    m2_old: float,
    block_values: np.ndarray,
) -> tuple[int, float, float]:
    """Merge one block into running mean and M2 using Chan's formula."""
    n_b = int(block_values.size)
    if n_b == 0:
        return count_old, mean_old, m2_old

    mean_b = float(block_values.mean(dtype=np.float64))
    var_b = float(block_values.var(dtype=np.float64))

    if count_old == 0:
        return n_b, mean_b, var_b * n_b

    n_new = count_old + n_b
    delta = mean_b - mean_old
    mean_new = (count_old * mean_old + n_b * mean_b) / n_new
    m2_new = m2_old + var_b * n_b + delta * delta * count_old * n_b / n_new
    return n_new, mean_new, m2_new


def valid_pixels(arr: np.ndarray, nodata: float | int | None) -> np.ndarray:
    if nodata is None:
        return arr.reshape(-1)
    return arr[arr != nodata]


def compute_stats(path: Path, chunk_rows: int) -> list[dict[str, float | int]]:
    with rasterio.open(path) as src:
        width = src.width
        height = src.height
        band_count = src.count
        nodata = src.nodata

        counts = np.zeros(band_count, dtype=np.int64)
        means = np.zeros(band_count, dtype=np.float64)
        m2_values = np.zeros(band_count, dtype=np.float64)
        mins = np.full(band_count, np.inf, dtype=np.float64)
        maxs = np.full(band_count, -np.inf, dtype=np.float64)

        print(f"Image size: width={width}, height={height}, bands={band_count}")
        print(f"Data type: {src.dtypes}; nodata={nodata}")
        print(f"Chunk rows: {chunk_rows}")

        for row_off in range(0, height, chunk_rows):
            actual_rows = min(chunk_rows, height - row_off)
            window = Window(0, row_off, width, actual_rows)
            chunk = src.read(window=window)

            for band_idx in range(band_count):
                values = valid_pixels(chunk[band_idx], nodata)
                if values.size == 0:
                    continue

                values64 = values.astype(np.float64, copy=False)
                counts[band_idx], means[band_idx], m2_values[band_idx] = merge_block_stats(
                    int(counts[band_idx]),
                    float(means[band_idx]),
                    float(m2_values[band_idx]),
                    values64,
                )
                mins[band_idx] = min(mins[band_idx], float(values64.min()))
                maxs[band_idx] = max(maxs[band_idx], float(values64.max()))

    results = []
    for band_idx in range(band_count):
        count = int(counts[band_idx])
        std = float(np.sqrt(m2_values[band_idx] / count)) if count else float("nan")
        results.append(
            {
                "band": band_idx + 1,
                "count": count,
                "mean": float(means[band_idx]) if count else float("nan"),
                "std": std,
                "max": float(maxs[band_idx]) if count else float("nan"),
                "min": float(mins[band_idx]) if count else float("nan"),
            }
        )
    return results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("Boston.tif"))
    parser.add_argument("--chunk-rows", type=int, default=128)
    parser.add_argument("--precision", type=int, default=3)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    results = compute_stats(args.input, args.chunk_rows)

    for item in results:
        band = item["band"]
        print(f"\n===== Band {band} =====")
        print(f"Mean:   {item['mean']:.{args.precision}f}")
        print(f"Std:    {item['std']:.{args.precision}f}")
        print(f"Max:    {item['max']:.{args.precision}f}")
        print(f"Min:    {item['min']:.{args.precision}f}")


if __name__ == "__main__":
    main()
