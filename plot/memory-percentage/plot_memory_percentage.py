#!/usr/bin/env python3

from __future__ import annotations

import csv
import math
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib
import matplotlib.pyplot as plt


# Publication-like defaults (match jolt-at-scale vibe)
matplotlib.rcParams.update({
    "figure.dpi": 150,
    "savefig.dpi": 300,
    "font.size": 11,
    "axes.titlesize": 12,
    "axes.labelsize": 11,
    "legend.fontsize": 10,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "axes.grid": True,
    "grid.alpha": 0.25,
    "lines.linewidth": 1.8,
})


THIS_DIR = Path(__file__).parent
DATA_FILE = THIS_DIR / "data.txt"


def read_memory_percentage(path: Path) -> Dict[str, Dict[int, float]]:
    """Parse data.txt: name,input,....,percentage

    Returns mapping: bench_id -> { input_value -> percentage }
    Skips lines like "GUEST PANIC" and malformed rows.
    Bench id is normalized from the prefix before "-guest".
    """
    mapping: Dict[str, Dict[int, float]] = defaultdict(dict)
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line.upper().startswith("GUEST PANIC"):
                continue
            parts = [p.strip() for p in line.split(",")]
            if len(parts) < 3:
                continue
            name = parts[0]
            try:
                x_val = int(float(parts[1]))
                pct = float(parts[-1])
            except Exception:
                continue

            # Normalize bench id (e.g., "sha2-chain-guest" -> "sha2_chain")
            bench_id = name
            if bench_id.endswith("-guest"):
                bench_id = bench_id[: -len("-guest")]
            bench_id = bench_id.replace("-", "_")

            mapping[bench_id][x_val] = pct
    return mapping


TITLES = {
    "collatz": "Collatz",
    "fibonacci": "Fibonacci",
    "muldiv": "MulDiv",
    "sha2_chain": "SHA2 Chain",
    "sha3_chain": "SHA3 Chain",
    "sha3": "SHA3",
}


def xlabel_for(bench_id: str) -> str:
    return "Cycles" if bench_id.startswith("sha") else "Input"


def plot_scaling(data: Dict[str, Dict[int, float]], out_base: Path) -> None:
    benches = sorted(data.keys(), key=lambda b: [
        {"collatz": 0, "fibonacci": 1}.get(b, 2),
        b,
    ])
    if not benches:
        print("No data to plot.")
        return

    n = len(benches)
    ncols = 2
    nrows = math.ceil(n / ncols)
    fig, axes = plt.subplots(nrows, ncols, figsize=(10, 3.5 * nrows), constrained_layout=True)
    # Flatten to a simple list of Axes regardless of shape
    if isinstance(axes, matplotlib.axes.Axes):
        axes_flat: List[matplotlib.axes.Axes] = [axes]
    else:
        axes_flat = list(axes.flat)  # type: ignore[attr-defined]

    for idx, bench in enumerate(benches):
        ax = axes_flat[idx]
        records = data[bench]
        xs = sorted(records.keys())
        ys = [records[x] for x in xs]

        ax.plot(xs, ys, marker="o", label=TITLES.get(bench, bench))
        ax.set_title(TITLES.get(bench, bench))
        ax.set_xlabel(xlabel_for(bench))
        ax.set_ylabel("Memory Proof (%)")

    # Hide any unused subplots
    for j in range(len(axes_flat)):
        if j >= n:
            axes_flat[j].set_visible(False)

    fig.savefig(out_base.with_suffix(".png"))
    fig.savefig(out_base.with_suffix(".pdf"))
    fig.savefig(out_base.with_suffix(".svg"))
    plt.close(fig)


def main() -> None:
    data = read_memory_percentage(DATA_FILE)
    # If both sha3 and sha3_chain exist, prefer sha3_chain and drop sha3 (avoid duplication)
    if "sha3_chain" in data and "sha3" in data:
        data.pop("sha3", None)
    out_base = THIS_DIR / "percentage_scaling"
    plot_scaling(data, out_base)
    print(f"Wrote figures: {out_base.with_suffix('.png')} (and .pdf/.svg)")


if __name__ == "__main__":
    main()


