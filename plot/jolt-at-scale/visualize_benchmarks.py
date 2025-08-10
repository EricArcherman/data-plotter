#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import math
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import matplotlib
import matplotlib.pyplot as plt


# Publication-like defaults
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


BASELINE_VARIANT = "untouched"
VARIANT_ORDER = ["untouched", "32-reg", "v-reg", "no-reg", "mem-batch"]
VARIANT_COLORS = {
    "untouched": "#7A7A7A",
    "32-reg": "#1f77b4",
    "v-reg": "#ff7f0e",
    "no-reg": "#d62728",
    "mem-batch": "#9467bd",
}

# Benchmarks to visualize (exclude variant names like "mem-batch")
BENCHMARKS = ["collatz", "fibonacci", "sha2_chain", "sha3_chain"]
BENCHMARK_TITLES = {
    "collatz": "Collatz",
    "fibonacci": "Fibonacci",
    "sha2_chain": "SHA2 Chain",
    "sha3_chain": "SHA3 Chain"
}

# Selected (focused) inputs for grouped bar charts and tables
FOCUSED_INPUTS = {
    "collatz": [1, 10, 20, 25],
    "fibonacci": [100, 1000, 10000, 20000, 40000],
    "sha2_chain": [1, 5, 10, 20, 25],
    "sha3_chain": [1, 5, 10, 20, 25],
}


@dataclass
class Record:
    variant: str
    benchmark: str
    input_value: int
    time_lo_s: float
    time_mid_s: float
    time_hi_s: float


def read_records(csv_path: Path) -> List[Record]:
    records: List[Record] = []
    skipped_rows = 0
    with csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                # Require minimal fields
                variant = row.get("variant", "").strip()
                benchmark = row.get("benchmark", "").strip()
                if not variant or not benchmark:
                    raise ValueError("missing variant/benchmark")

                input_value = int(row["input_value"])  # may raise
                time_lo_s = float(row["time_lo_s"])    # may raise
                time_mid_s = float(row["time_mid_s"])  # may raise
                time_hi_s = float(row["time_hi_s"])    # may raise

                records.append(
                    Record(
                        variant=variant,
                        benchmark=benchmark,
                        input_value=input_value,
                        time_lo_s=time_lo_s,
                        time_mid_s=time_mid_s,
                        time_hi_s=time_hi_s,
                    )
                )
            except Exception:
                skipped_rows += 1
                continue

    if skipped_rows:
        print(f"Warning: skipped {skipped_rows} invalid row(s) from {csv_path.name}")
    return records


def group_by(records: Iterable[Record]) -> Dict[str, Dict[str, Dict[int, Record]]]:
    # benchmark -> variant -> input_value -> record
    data: Dict[str, Dict[str, Dict[int, Record]]] = defaultdict(lambda: defaultdict(dict))
    for r in records:
        data[r.benchmark][r.variant][r.input_value] = r
    return data


def ensure_output_dirs(out_dir: Path) -> Tuple[Path, Path]:
    fig_dir = out_dir / "figures"
    tbl_dir = out_dir / "tables"
    fig_dir.mkdir(parents=True, exist_ok=True)
    tbl_dir.mkdir(parents=True, exist_ok=True)
    return fig_dir, tbl_dir


def plot_scaling_curves(data: Dict[str, Dict[str, Dict[int, Record]]], fig_dir: Path) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(10, 7), constrained_layout=True)
    axes = axes.ravel()
    for idx, bench in enumerate(BENCHMARKS):
        ax = axes[idx]
        ax.set_title(BENCHMARK_TITLES[bench])
        ax.set_xlabel("Cycles" if bench.startswith("sha") else "Input")
        ax.set_ylabel("Time (s)")

        if bench not in data:
            ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
            continue

        for variant in VARIANT_ORDER:
            records_map = data[bench].get(variant, {})
            if not records_map:
                continue
            xs = sorted(records_map.keys())
            ys = [records_map[x].time_mid_s for x in xs]
            y_lo = [records_map[x].time_lo_s for x in xs]
            y_hi = [records_map[x].time_hi_s for x in xs]
            color = VARIANT_COLORS.get(variant, None)

            ax.plot(xs, ys, label=variant, color=color)
            ax.fill_between(xs, y_lo, y_hi, color=color, alpha=0.15, linewidth=0)

        ax.legend(frameon=False)

    out_base = fig_dir / "scaling_curves"
    fig.savefig(out_base.with_suffix(".png"))
    fig.savefig(out_base.with_suffix(".pdf"))
    fig.savefig(out_base.with_suffix(".svg"))
    plt.close(fig)


def plot_speedup_curves(data: Dict[str, Dict[str, Dict[int, Record]]], fig_dir: Path) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(10, 7), constrained_layout=True)
    axes = axes.ravel()
    for idx, bench in enumerate(BENCHMARKS):
        ax = axes[idx]
        ax.set_title(BENCHMARK_TITLES[bench])
        ax.set_xlabel("Cycles" if bench.startswith("sha") else "Input")
        ax.set_ylabel(f"Speedup vs {BASELINE_VARIANT}")

        if bench not in data:
            ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
            continue

        baseline_map = data[bench].get(BASELINE_VARIANT, {})
        for variant in VARIANT_ORDER:
            if variant == BASELINE_VARIANT:
                continue
            variant_map = data[bench].get(variant, {})
            if not variant_map or not baseline_map:
                continue
            common_inputs = sorted(set(variant_map.keys()) & set(baseline_map.keys()))
            if not common_inputs:
                continue
            xs = common_inputs
            ys = []
            for x in xs:
                base_t = baseline_map[x].time_mid_s
                var_t = variant_map[x].time_mid_s
                if var_t <= 0:
                    continue
                ys.append(base_t / var_t)
            color = VARIANT_COLORS.get(variant, None)
            ax.plot(xs[: len(ys)], ys, label=variant, color=color)

        ax.axhline(1.0, color="#777777", linewidth=1.0, linestyle="--")
        ax.legend(frameon=False)

    out_base = fig_dir / "speedup_curves"
    fig.savefig(out_base.with_suffix(".png"))
    fig.savefig(out_base.with_suffix(".pdf"))
    fig.savefig(out_base.with_suffix(".svg"))
    plt.close(fig)


def plot_grouped_bars(data: Dict[str, Dict[str, Dict[int, Record]]], fig_dir: Path) -> None:
    for bench in BENCHMARKS:
        if bench not in data:
            continue
        focused = FOCUSED_INPUTS.get(bench, [])
        available_inputs = [x for x in focused if any(x in data[bench].get(v, {}) for v in VARIANT_ORDER)]
        if not available_inputs:
            continue

        # Consider only variants that actually have data for this benchmark
        present_variants = [v for v in VARIANT_ORDER if data[bench].get(v, {})]
        num_variants = max(1, len(present_variants))
        width = 0.75 / num_variants
        x_positions = list(range(len(available_inputs)))

        fig, ax = plt.subplots(figsize=(10, 4.0))
        ax.set_title(f"{BENCHMARK_TITLES[bench]} — Selected Inputs")
        ax.set_xlabel("Cycles" if bench.startswith("sha") else "Input")
        ax.set_ylabel("Time (s)")

        for idx_v, variant in enumerate(present_variants):
            records_map = data[bench].get(variant, {})
            # Center the group of bars around each x position
            offset = (idx_v - (num_variants - 1) / 2.0) * width
            xs = [x + offset for x in x_positions]
            ys = []
            yerr_low = []
            yerr_high = []
            labels = []
            for inp in available_inputs:
                rec = records_map.get(inp)
                if rec is None:
                    ys.append(float("nan"))
                    yerr_low.append(0.0)
                    yerr_high.append(0.0)
                else:
                    ys.append(rec.time_mid_s)
                    yerr_low.append(max(0.0, rec.time_mid_s - rec.time_lo_s))
                    yerr_high.append(max(0.0, rec.time_hi_s - rec.time_mid_s))
                labels.append(str(inp))

            color = VARIANT_COLORS.get(variant, None)
            ax.bar(
                xs,
                ys,
                width=width,
                label=variant,
                color=color,
                edgecolor="black",
                linewidth=0.5,
                yerr=[yerr_low, yerr_high],
                capsize=3,
            )

        ax.set_xticks(x_positions)
        ax.set_xticklabels([str(inp) for inp in available_inputs])
        ax.legend(frameon=False)
        fig.tight_layout()

        out_base = fig_dir / f"bars_{bench}"
        fig.savefig(out_base.with_suffix(".png"))
        fig.savefig(out_base.with_suffix(".pdf"))
        fig.savefig(out_base.with_suffix(".svg"))
        plt.close(fig)


def write_summary_tables(data: Dict[str, Dict[str, Dict[int, Record]]], tbl_dir: Path) -> None:
    # One CSV per benchmark summarizing selected inputs
    for bench in BENCHMARKS:
        if bench not in data:
            continue
        focused = FOCUSED_INPUTS.get(bench, [])
        out_csv = tbl_dir / f"summary_{bench}.csv"
        fieldnames = [
            "benchmark",
            "input",
            "variant",
            "median_s",
            "lo_s",
            "hi_s",
            "improvement_pct_vs_baseline",
        ]
        with out_csv.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            baseline_map = data[bench].get(BASELINE_VARIANT, {})
            for inp in focused:
                for variant in VARIANT_ORDER:
                    rec = data[bench].get(variant, {}).get(inp)
                    if rec is None:
                        continue
                    base = baseline_map.get(inp)
                    improvement = None
                    if base is not None and rec.time_mid_s > 0:
                        improvement = (base.time_mid_s - rec.time_mid_s) / base.time_mid_s * 100.0
                    writer.writerow(
                        {
                            "benchmark": bench,
                            "input": inp,
                            "variant": variant,
                            "median_s": f"{rec.time_mid_s:.4f}",
                            "lo_s": f"{rec.time_lo_s:.4f}",
                            "hi_s": f"{rec.time_hi_s:.4f}",
                            "improvement_pct_vs_baseline": (f"{improvement:.2f}" if improvement is not None else ""),
                        }
                    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Visualize Jolt benchmark data")
    parser.add_argument(
        "--csv",
        type=Path,
        default=Path(__file__).parent / "parsed_benchmarks.csv",
        help="Path to parsed_benchmarks.csv",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path(__file__).parent,
        help="Directory where figures/ and tables/ will be created",
    )
    args = parser.parse_args()

    records = read_records(args.csv)
    data = group_by(records)
    fig_dir, tbl_dir = ensure_output_dirs(args.out_dir)

    plot_scaling_curves(data, fig_dir)
    plot_speedup_curves(data, fig_dir)
    plot_grouped_bars(data, fig_dir)
    write_summary_tables(data, tbl_dir)

    print(f"Figures written to: {fig_dir}")
    print(f"Tables written to:  {tbl_dir}")


if __name__ == "__main__":
    main()

