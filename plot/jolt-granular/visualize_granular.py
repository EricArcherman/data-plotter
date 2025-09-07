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


VARIANT = "32-reg"
BENCH_TITLES = {
    "collatz": "Collatz",
    "fibonacci": "Fibonacci",
    "sha2_chain": "SHA2 Chain",
    "sha3_chain": "SHA3 Chain",
}


@dataclass
class Top:
    benchmark: str
    input_value: int
    phase: str
    lo: float
    mid: float
    hi: float


@dataclass
class Sub:
    benchmark: str
    input_value: int
    group: str
    name: str
    lo: float
    mid: float
    hi: float


@dataclass
class SizeRow:
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
            if row.get("variant") != VARIANT:
                continue
            out.append(
                Top(
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
            if row.get("variant") != VARIANT:
                continue
            out.append(
                Sub(
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
            if row.get("variant") != VARIANT:
                continue
            out.append(
                SizeRow(
                    benchmark=row["benchmark"],
                    input_value=int(row["input_value"]),
                    component=row["component"],
                    lo=float(row["size_lo_mb"]),
                    mid=float(row["size_mid_mb"]),
                    hi=float(row["size_hi_mb"]),
                )
            )
    return out


def group_top(rows: Iterable[Top]) -> Dict[str, Dict[int, Dict[str, Top]]]:
    # benchmark -> input_value -> phase -> row
    m: Dict[str, Dict[int, Dict[str, Top]]] = defaultdict(lambda: defaultdict(dict))
    for t in rows:
        m[t.benchmark][t.input_value][t.phase] = t
    return m


def group_sub(rows: Iterable[Sub]) -> Dict[str, Dict[int, Dict[str, List[Sub]]]]:
    # benchmark -> input_value -> group -> [Sub]
    m: Dict[str, Dict[int, Dict[str, List[Sub]]]] = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    for s in rows:
        m[s.benchmark][s.input_value][s.group].append(s)
    return m


def group_sizes(rows: Iterable[SizeRow]) -> Dict[str, Dict[int, List[SizeRow]]]:
    # benchmark -> input_value -> [SizeRow]
    m: Dict[str, Dict[int, List[SizeRow]]] = defaultdict(lambda: defaultdict(list))
    for r in rows:
        m[r.benchmark][r.input_value].append(r)
    return m


def plot_top_stacked(top_map: Dict[str, Dict[int, Dict[str, Top]]], out_dir: Path) -> None:
    # For each benchmark, plot stacked bars per input: decode, trace, preprocess, prove, verify
    phases = ["decode", "trace", "preprocess", "prove", "verify"]
    for bench, inputs in top_map.items():
        xs = sorted(inputs.keys())
        if not xs:
            continue
        fig, ax = plt.subplots(figsize=(10, 4.0))
        bottoms = [0.0] * len(xs)
        colors = {
            "decode": "#7f7f7f",
            "trace": "#8c564b",
            "preprocess": "#1f77b4",
            "prove": "#2ca02c",
            "verify": "#d62728",
        }
        for phase in phases:
            ys = [inputs[x].get(phase).mid if phase in inputs[x] else 0.0 for x in xs]
            ax.bar(range(len(xs)), ys, bottom=bottoms, color=colors.get(phase), label=phase, edgecolor="black", linewidth=0.5)
            bottoms = [b + y for b, y in zip(bottoms, ys)]

        ax.set_title(f"{BENCH_TITLES.get(bench, bench)} — Top-level time breakdown")
        ax.set_xlabel("Input")
        ax.set_ylabel("Time (s)")
        ax.set_xticks(range(len(xs)))
        ax.set_xticklabels([str(x) for x in xs], rotation=0)
        ax.legend(frameon=False, ncol=5)
        fig.tight_layout()
        base = out_dir / f"stacked_top_{bench}"
        fig.savefig(base.with_suffix(".png"))
        fig.savefig(base.with_suffix(".pdf"))
        fig.savefig(base.with_suffix(".svg"))
        plt.close(fig)


def plot_sub_breakdowns(sub_map: Dict[str, Dict[int, Dict[str, List[Sub]]]], out_dir: Path) -> None:
    # For each benchmark and each group (preprocess/prove/verify), draw grouped bars of subcomponents for selected inputs
    for bench, inputs in sub_map.items():
        xs = sorted(inputs.keys())
        if not xs:
            continue
        # choose a few representative inputs to avoid clutter
        selected = xs[:8]
        for group in ["preprocess", "prove", "verify"]:
            # collect all sub-name keys across selected inputs
            names: List[str] = []
            name_set = set()
            for inp in selected:
                for sub in inputs[inp].get(group, []):
                    if sub.name not in name_set:
                        name_set.add(sub.name)
                        names.append(sub.name)
            if not names:
                continue

            width = 0.75 / max(1, len(names))
            fig, ax = plt.subplots(figsize=(10, 4.0))
            ax.set_title(f"{BENCH_TITLES.get(bench, bench)} — {group} details")
            ax.set_xlabel("Input")
            ax.set_ylabel("Time (s)")

            for idx_n, name in enumerate(names):
                xs_pos = [i + (idx_n - (len(names) - 1)/2.0)*width for i in range(len(selected))]
                ys = []
                for inp in selected:
                    # find matching sub by name
                    value = 0.0
                    for sub in inputs[inp].get(group, []):
                        if sub.name == name:
                            value = sub.mid
                            break
                    ys.append(value)
                ax.bar(xs_pos, ys, width=width, label=name, edgecolor="black", linewidth=0.4)

            ax.set_xticks(range(len(selected)))
            ax.set_xticklabels([str(x) for x in selected])
            ax.legend(frameon=False, ncol=min(4, len(names)))
            fig.tight_layout()
            base = out_dir / f"bars_{bench}_{group}_details"
            fig.savefig(base.with_suffix(".png"))
            fig.savefig(base.with_suffix(".pdf"))
            fig.savefig(base.with_suffix(".svg"))
            plt.close(fig)


def plot_proof_sizes(size_map: Dict[str, Dict[int, List[SizeRow]]], out_dir: Path) -> None:
    # Plot total proof size and components as stacked bars
    for bench, inputs in size_map.items():
        xs = sorted(inputs.keys())
        if not xs:
            continue
        fig, ax = plt.subplots(figsize=(10, 4.0))

        components = ["commitments", "proof"]  # "total" is sum; we can also plot it as line
        bottoms = [0.0] * len(xs)
        colors = {
            "commitments": "#17becf",
            "proof": "#bcbd22",
        }
        for comp in components:
            ys = []
            for x in xs:
                # find component mid for this input
                mid = 0.0
                for row in inputs[x]:
                    if row.component == comp:
                        mid = row.mid
                        break
                ys.append(mid)
            ax.bar(range(len(xs)), ys, bottom=bottoms, color=colors.get(comp), label=comp, edgecolor="black", linewidth=0.5)
            bottoms = [b + y for b, y in zip(bottoms, ys)]

        # Overlay total as a line
        totals = []
        for x in xs:
            total = 0.0
            for row in inputs[x]:
                if row.component == "total":
                    total = row.mid
                    break
            totals.append(total)
        ax.plot(range(len(xs)), totals, color="#444444", linestyle="--", label="total")

        ax.set_title(f"{BENCH_TITLES.get(bench, bench)} — Proof size (MB)")
        ax.set_xlabel("Input")
        ax.set_ylabel("Size (MB)")
        ax.set_xticks(range(len(xs)))
        ax.set_xticklabels([str(x) for x in xs])
        ax.legend(frameon=False)
        fig.tight_layout()
        base = out_dir / f"proof_sizes_{bench}"
        fig.savefig(base.with_suffix(".png"))
        fig.savefig(base.with_suffix(".pdf"))
        fig.savefig(base.with_suffix(".svg"))
        plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Visualize granular 32-reg results")
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
    plot_top_stacked(top_map, args.out_dir)
    plot_sub_breakdowns(sub_map, args.out_dir)
    plot_proof_sizes(size_map, args.out_dir)

    print(f"Figures written to: {args.out_dir}")


if __name__ == "__main__":
    main()


