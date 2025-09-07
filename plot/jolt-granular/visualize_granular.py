#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import matplotlib
import matplotlib.pyplot as plt


# Consistent style with existing plots
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


VARIANT_COLORS = {
    "32-reg": "#1f77b4",
    "vanilla": "#ff7f0e",
}
BENCH_TITLES = {
    "collatz": "Collatz",
    "fibonacci": "Fibonacci",
    "sha2_chain": "SHA2 Chain",
    "sha3_chain": "SHA3 Chain",
}


@dataclass
class Top:
    variant: str
    benchmark: str
    input_value: int
    phase: str
    lo: float
    mid: float
    hi: float


@dataclass
class Sub:
    variant: str
    benchmark: str
    input_value: int
    group: str
    name: str
    lo: float
    mid: float
    hi: float


@dataclass
class SizeRow:
    variant: str
    benchmark: str
    input_value: int
    component: str
    lo: float
    mid: float
    hi: float


def read_top(csv_path: Path) -> List[Top]:
    out: List[Top] = []
    with csv_path.open("r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            out.append(
                Top(
                    variant=row.get("variant", "unknown"),
                    benchmark=row["benchmark"],
                    input_value=int(row["input_value"]),
                    phase=row["phase"],
                    lo=float(row["time_lo_s"]),
                    mid=float(row["time_mid_s"]),
                    hi=float(row["time_hi_s"]),
                )
            )
    return out


def read_sub(csv_path: Path) -> List[Sub]:
    out: List[Sub] = []
    with csv_path.open("r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            out.append(
                Sub(
                    variant=row.get("variant", "unknown"),
                    benchmark=row["benchmark"],
                    input_value=int(row["input_value"]),
                    group=row["group"],
                    name=row["name"],
                    lo=float(row["time_lo_s"]),
                    mid=float(row["time_mid_s"]),
                    hi=float(row["time_hi_s"]),
                )
            )
    return out


def read_sizes(csv_path: Path) -> List[SizeRow]:
    out: List[SizeRow] = []
    with csv_path.open("r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            out.append(
                SizeRow(
                    variant=row.get("variant", "unknown"),
                    benchmark=row["benchmark"],
                    input_value=int(row["input_value"]),
                    component=row["component"],
                    lo=float(row["size_lo_mb"]),
                    mid=float(row["size_mid_mb"]),
                    hi=float(row["size_hi_mb"]),
                )
            )
    return out


def group_top(rows: Iterable[Top]) -> Dict[str, Dict[str, Dict[int, Dict[str, Top]]]]:
    # benchmark -> variant -> input_value -> phase -> row
    m: Dict[str, Dict[str, Dict[int, Dict[str, Top]]]] = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))
    for t in rows:
        m[t.benchmark][t.variant][t.input_value][t.phase] = t
    return m


def group_sub(rows: Iterable[Sub]) -> Dict[str, Dict[str, Dict[int, Dict[str, List[Sub]]]]]:
    # benchmark -> variant -> input_value -> group -> [Sub]
    m: Dict[str, Dict[str, Dict[int, Dict[str, List[Sub]]]]] = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(list))))
    for s in rows:
        m[s.benchmark][s.variant][s.input_value][s.group].append(s)
    return m


def group_sizes(rows: Iterable[SizeRow]) -> Dict[str, Dict[str, Dict[int, List[SizeRow]]]]:
    # benchmark -> variant -> input_value -> [SizeRow]
    m: Dict[str, Dict[str, Dict[int, List[SizeRow]]]] = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    for r in rows:
        m[r.benchmark][r.variant][r.input_value].append(r)
    return m


def plot_top_compare_lines(top_map: Dict[str, Dict[str, Dict[int, Dict[str, Top]]]], out_dir: Path) -> None:
    # For each benchmark, draw per-phase lines across full range for each variant, with lo/hi ribbons
    phases = ["decode", "trace", "preprocess", "prove", "verify"]
    for bench, variants in top_map.items():
        if not variants:
            continue
        fig, axes = plt.subplots(2, 3, figsize=(12, 6.0))
        axes = axes.ravel()
        for idx, phase in enumerate(phases):
            ax = axes[idx]
            for variant, inputs in variants.items():
                xs = sorted(inputs.keys())
                if not xs:
                    continue
                mids = [inputs[x][phase].mid if phase in inputs[x] else 0.0 for x in xs]
                los = [inputs[x][phase].lo if phase in inputs[x] else 0.0 for x in xs]
                his = [inputs[x][phase].hi if phase in inputs[x] else 0.0 for x in xs]
                color = VARIANT_COLORS.get(variant, None)
                ax.plot(xs, mids, label=variant, color=color)
                ax.fill_between(xs, los, his, alpha=0.2, color=color)
            ax.set_title(phase)
            ax.set_xlabel("Input")
            ax.set_ylabel("Time (s)")
        # Hide unused subplot if any
        if len(phases) < len(axes):
            axes[-1].axis('off')
        fig.suptitle(f"{BENCH_TITLES.get(bench, bench)} — Phase scaling (full range)")
        handles, labels = axes[0].get_legend_handles_labels()
        fig.legend(handles, labels, frameon=False, ncol=len(labels), loc='lower center')
        fig.tight_layout(rect=[0, 0.08, 1, 0.96])
        base = out_dir / f"compare_lines_phases_{bench}"
        fig.savefig(base.with_suffix(".png"))
        fig.savefig(base.with_suffix(".pdf"))
        fig.savefig(base.with_suffix(".svg"))
        plt.close(fig)

        # Total time comparison
        fig, ax = plt.subplots(figsize=(10, 4.0))
        for variant, inputs in variants.items():
            xs = sorted(inputs.keys())
            totals_mid = []
            totals_lo = []
            totals_hi = []
            for x in xs:
                phases_present = inputs[x]
                mids = [ph.mid for ph in phases_present.values() if ph]
                los = [ph.lo for ph in phases_present.values() if ph]
                his = [ph.hi for ph in phases_present.values() if ph]
                totals_mid.append(sum(mids))
                totals_lo.append(sum(los))
                totals_hi.append(sum(his))
            color = VARIANT_COLORS.get(variant, None)
            ax.plot(xs, totals_mid, label=variant, color=color)
            ax.fill_between(xs, totals_lo, totals_hi, alpha=0.2, color=color)
        ax.set_title(f"{BENCH_TITLES.get(bench, bench)} — Total time (full range)")
        ax.set_xlabel("Input")
        ax.set_ylabel("Time (s)")
        ax.legend(frameon=False)
        fig.tight_layout()
        base = out_dir / f"compare_lines_total_{bench}"
        fig.savefig(base.with_suffix(".png"))
        fig.savefig(base.with_suffix(".pdf"))
        fig.savefig(base.with_suffix(".svg"))
        plt.close(fig)


def plot_sub_stacked_area(sub_map: Dict[str, Dict[str, Dict[int, Dict[str, List[Sub]]]]], out_dir: Path) -> None:
    # For each benchmark and group, draw stacked area across full range per variant
    for bench, variants in sub_map.items():
        for group in ["preprocess", "prove", "verify"]:
            for variant, inputs in variants.items():
                xs = sorted(inputs.keys())
                if not xs:
                    continue
                # collect all sub-names across full range
                name_set = set()
                for inp in xs:
                    for sub in inputs[inp].get(group, []):
                        name_set.add(sub.name)
                names = sorted(name_set)
                if not names:
                    continue
                # build matrix: name -> list over xs of mid time
                series: Dict[str, List[float]] = {n: [] for n in names}
                for inp in xs:
                    parts = {s.name: s.mid for s in inputs[inp].get(group, [])}
                    for n in names:
                        series[n].append(parts.get(n, 0.0))

                fig, ax = plt.subplots(figsize=(12, 4.0))
                bottom = [0.0] * len(xs)
                for n in names:
                    ys = series[n]
                    ax.fill_between(xs, bottom, [b + y for b, y in zip(bottom, ys)], step=None, alpha=0.7, label=n)
                    bottom = [b + y for b, y in zip(bottom, ys)]

                ax.set_title(f"{BENCH_TITLES.get(bench, bench)} — {group} subphases ({variant})")
                ax.set_xlabel("Input")
                ax.set_ylabel("Time (s)")
                ax.legend(frameon=False, ncol=4)
                fig.tight_layout()
                base = out_dir / f"stacked_area_{bench}_{group}_{variant}"
                fig.savefig(base.with_suffix(".png"))
                fig.savefig(base.with_suffix(".pdf"))
                fig.savefig(base.with_suffix(".svg"))
                plt.close(fig)


def plot_proof_sizes_compare(size_map: Dict[str, Dict[str, Dict[int, List[SizeRow]]]], out_dir: Path) -> None:
    # For each benchmark, plot component and total lines across full range for both variants
    for bench, variants in size_map.items():
        if not variants:
            continue
        # Components
        for comp in ["commitments", "proof", "total"]:
            fig, ax = plt.subplots(figsize=(10, 4.0))
            for variant, inputs in variants.items():
                xs = sorted(inputs.keys())
                ys = []
                for x in xs:
                    val = 0.0
                    for row in inputs[x]:
                        if (comp == "total" and row.component == "total") or row.component == comp:
                            val = row.mid
                            break
                    ys.append(val)
                color = VARIANT_COLORS.get(variant, None)
                ax.plot(xs, ys, label=f"{variant}", color=color)
            title_comp = comp.capitalize()
            ax.set_title(f"{BENCH_TITLES.get(bench, bench)} — Proof size: {title_comp} (MB)")
            ax.set_xlabel("Input")
            ax.set_ylabel("Size (MB)")
            ax.legend(frameon=False)
            fig.tight_layout()
            base = out_dir / f"compare_sizes_{bench}_{comp}"
            fig.savefig(base.with_suffix(".png"))
            fig.savefig(base.with_suffix(".pdf"))
            fig.savefig(base.with_suffix(".svg"))
            plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Visualize granular results and compare variants")
    parser.add_argument(
        "--top-csv",
        type=Path,
        default=Path(__file__).parent / "granular_top_level.csv",
    )
    parser.add_argument(
        "--sub-csv",
        type=Path,
        default=Path(__file__).parent / "granular_subphases.csv",
    )
    parser.add_argument(
        "--size-csv",
        type=Path,
        default=Path(__file__).parent / "granular_proof_sizes.csv",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path(__file__).parent / "figures",
    )
    args = parser.parse_args()

    tops = read_top(args.top_csv)
    subs = read_sub(args.sub_csv)
    sizes = read_sizes(args.size_csv)

    top_map = group_top(tops)
    sub_map = group_sub(subs)
    size_map = group_sizes(sizes)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    plot_top_compare_lines(top_map, args.out_dir)
    plot_sub_stacked_area(sub_map, args.out_dir)
    plot_proof_sizes_compare(size_map, args.out_dir)

    print(f"Figures written to: {args.out_dir}")


if __name__ == "__main__":
    main()


