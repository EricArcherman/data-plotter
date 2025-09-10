#!/usr/bin/env python3

"""
Parse granular Jolt benchmark outputs and produce tidy CSV/JSON suitable for plotting.

Input format: lines like
  Benchmarking 2th collatz number
  Benchmarking 2th collatz number: Warming up for 5.0000 s
  [preprocess] shapes=0.000s il_pp=0.009s ... setup=2.585s
  [prove] preamble=0.000s il_wit=0.003s ... openings=0.183s
  [timing] decode=0.233s trace=0.065s preprocess=2.594s prove=0.617s
  [proof-size] commitments=0.015MB proof=0.108MB total=0.123MB
  [verify] bytecode=0.001s
  [verify] instruction_lookups=0.014s
  ...
  [bench] decode=0.233s trace=0.065s preprocess=2.594s prove=0.617s verify=0.054s

We aggregate per-input samples during the "Collecting ... samples" window and
emit summary CSVs with lo/median/hi per phase/component.

Outputs (in the same directory by default):
  - granular_top_level.csv
  - granular_subphases.csv
  - granular_proof_sizes.csv
  - granular_summary.json
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any


# Regexes for input boundaries
RE_BENCH_FIB_COL = re.compile(
    r"^Benchmarking\s+(?P<ordinal>\d+)(?:th|st|nd|rd)\s+"
    r"(?P<num_name>(?:fibonacci|collatz))\s+number"
)

RE_BENCH_SHA = re.compile(
    r"^Benchmarking\s+(?P<count>\d+)\s+(?P<sha>sha2|sha3)\s+chain\s+cycles"
)

RE_COLLECTING = re.compile(r"^Benchmarking .+: Collecting\s+(?P<n>\d+) samples")
RE_ANALYZING = re.compile(r"^.+: Analyzing$")

# Regexes for lines with data
RE_SECTION_KVS_S = re.compile(r"^\[(?P<section>preprocess|prove)\]\s+(?P<kvs>.+)$")
RE_TIMING = re.compile(
    r"^\[timing\]\s+decode=(?P<decode>[0-9.]+)s\s+"
    r"trace=(?P<trace>[0-9.]+)s\s+preprocess=(?P<preprocess>[0-9.]+)s\s+"
    r"prove=(?P<prove>[0-9.]+)s$"
)
RE_PROOF_SIZE = re.compile(
    r"^\[proof-size\]\s+commitments=(?P<commit>[0-9.]+)MB\s+"
    r"proof=(?P<proof>[0-9.]+)MB\s+total=(?P<total>[0-9.]+)MB$"
)
RE_VERIFY_SUB = re.compile(r"^\[verify\]\s+(?P<key>[a-zA-Z_]+)=(?P<val>[0-9.]+)s$")
RE_BENCH = re.compile(
    r"^\[bench\]\s+decode=(?P<decode>[0-9.]+)s\s+"
    r"trace=(?P<trace>[0-9.]+)s\s+preprocess=(?P<preprocess>[0-9.]+)s\s+"
    r"prove=(?P<prove>[0-9.]+)s\s+verify=(?P<verify>[0-9.]+)s$"
)


def parse_kvs_seconds(s: str) -> Dict[str, float]:
    """Parse 'k=v' pairs where v ends with 's' into a dict of floats in seconds."""
    out: Dict[str, float] = {}
    for tok in s.split():
        if "=" not in tok:
            continue
        k, v = tok.split("=", 1)
        if v.endswith("s"):
            v = v[:-1]
        try:
            out[k] = float(v)
        except ValueError:
            continue
    return out


@dataclass
class Key:
    variant: str
    benchmark: str
    input_value: int
    input_metric: str  # "n" or "cycles"


def median(vals: List[float]) -> float:
    if not vals:
        return 0.0
    s = sorted(vals)
    n = len(s)
    mid = n // 2
    if n % 2 == 1:
        return s[mid]
    return 0.5 * (s[mid - 1] + s[mid])


def summarize(vals: List[float]) -> Tuple[float, float, float]:
    if not vals:
        return (0.0, 0.0, 0.0)
    return (min(vals), median(vals), max(vals))


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse granular results (supports multiple variants)")
    parser.add_argument(
        "--root",
        type=Path,
        action="append",
        help="Directory containing granular result .txt files. Can be provided multiple times.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path(__file__).parent,
        help="Directory to write CSV/JSON outputs",
    )
    args = parser.parse_args()

    # Default roots if none provided
    if not args.root:
        base = Path(__file__).parent
        default_32 = base / "32-reg-results"
        default_mem = base / "mem-batch-results"
        # Support both old and new vanilla layouts
        vanilla_new = base / "vanilla-results"
        vanilla_old = base / "vanilla-results" / "untouched-results"
        # Prefer new layout when present
        vanilla_default = vanilla_new if vanilla_new.exists() else vanilla_old
        args.root = [default_32, default_mem, vanilla_default]

    def guess_variant(root: Path) -> str:
        name_chain = [p.name.lower() for p in [root] + list(root.parents)[:2]]
        if any("32-reg" in n for n in name_chain) or any("32_reg" in n for n in name_chain):
            return "32-reg"
        if any("mem-batch" in n for n in name_chain) or any("mem_batch" in n for n in name_chain):
            return "mem-batch"
        if any("vanilla" in n for n in name_chain):
            return "vanilla"
        # fallback to directory name
        return root.name

    # Accumulators
    # (variant, benchmark, input) -> phase -> samples of seconds
    top_level: Dict[Tuple[str, str, int], Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))
    # (variant, benchmark, input) -> group -> name -> samples (seconds)
    subphases: Dict[Tuple[str, str, int], Dict[str, Dict[str, List[float]]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(list))
    )
    # (variant, benchmark, input) -> component -> samples (MB)
    proof_sizes: Dict[Tuple[str, str, int], Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))

    # Map key tuple to metadata (metric)
    key_to_metric: Dict[Tuple[str, str, int], str] = {}
    parsed_files = 0

    # Scan all roots
    for root in args.root:
        files = list(sorted(p for p in root.glob("*.txt") if p.is_file()))
        if not files:
            print(f"No .txt files in {root}")
            continue

        variant = guess_variant(root)
        parsed_files += len(files)

        # State variables while scanning a file
        for path in files:
            benchmark = path.stem  # e.g., collatz, fibonacci, sha2_chain, sha3_chain
            # We'll discover precise names from the header lines as well
            current_bench: Optional[str] = None
            current_input_val: Optional[int] = None
            current_metric: Optional[str] = None
            collecting = False

            # Scratch per-sample (reset after each [bench])
            scratch_prove: Dict[str, float] = {}
            scratch_preprocess: Dict[str, float] = {}
            scratch_verify: Dict[str, float] = {}
            scratch_sizes: Dict[str, float] = {}

            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            for raw in text.splitlines():
                line = raw.rstrip("\n")

                # First, detect start/stop of sample collection windows
                m = RE_COLLECTING.match(line)
                if m:
                    # Ensure current benchmark context exists; if not, infer from the same line
                    if current_bench is None or current_input_val is None:
                        mf = RE_BENCH_FIB_COL.match(line)
                        ms = mf if mf else RE_BENCH_SHA.match(line)
                        if ms:
                            if mf:
                                bname = mf.group("num_name")
                                current_bench = "fibonacci" if "fibonacci" in bname else "collatz"
                                current_input_val = int(mf.group("ordinal"))
                                current_metric = "n"
                            else:
                                sha = ms.group("sha")
                                current_bench = f"{sha}_chain"
                                current_input_val = int(ms.group("count"))
                                current_metric = "cycles"
                    collecting = True
                    # new collection window; clear scratch for the upcoming sample
                    scratch_prove.clear(); scratch_preprocess.clear(); scratch_verify.clear(); scratch_sizes.clear()
                    continue

                if RE_ANALYZING.match(line):
                    collecting = False
                    continue

                # Input group identification
                m = RE_BENCH_FIB_COL.match(line)
                if m:
                    current_bench = m.group("num_name")
                    # normalize to benchmark id
                    bname = m.group("num_name")
                    if "fibonacci" in bname:
                        current_bench = "fibonacci"
                    else:
                        current_bench = "collatz"
                    current_input_val = int(m.group("ordinal"))
                    current_metric = "n"
                    collecting = False
                    # reset scratch on new input
                    scratch_prove.clear(); scratch_preprocess.clear(); scratch_verify.clear(); scratch_sizes.clear()
                    continue

                m = RE_BENCH_SHA.match(line)
                if m:
                    sha = m.group("sha")
                    current_bench = f"{sha}_chain"
                    current_input_val = int(m.group("count"))
                    current_metric = "cycles"
                    collecting = False
                    scratch_prove.clear(); scratch_preprocess.clear(); scratch_verify.clear(); scratch_sizes.clear()
                    continue

                if current_bench is None or current_input_val is None:
                    # not inside a benchmark block yet
                    continue

                # Capture lines only when actively collecting samples
                if not collecting:
                    continue

                m = RE_SECTION_KVS_S.match(line)
                if m:
                    sec = m.group("section")
                    kvs = parse_kvs_seconds(m.group("kvs"))
                    if sec == "prove":
                        scratch_prove = kvs
                    else:
                        scratch_preprocess = kvs
                    continue

                m = RE_TIMING.match(line)
                if m:
                    # Optional: could be used, but we prefer [bench] as ground truth
                    # Still, ignore here since [bench] includes verify
                    continue

                m = RE_PROOF_SIZE.match(line)
                if m:
                    scratch_sizes = {
                        "commitments": float(m.group("commit")),
                        "proof": float(m.group("proof")),
                        "total": float(m.group("total")),
                    }
                    continue

                m = RE_VERIFY_SUB.match(line)
                if m:
                    scratch_verify[m.group("key")] = float(m.group("val"))
                    continue

                m = RE_BENCH.match(line)
                if m:
                    # finalize one sample
                    k = (variant, current_bench, current_input_val)
                    key_to_metric[k] = current_metric or "n"

                    # top-level phases from [bench]
                    top_level[k]["decode"].append(float(m.group("decode")))
                    top_level[k]["trace"].append(float(m.group("trace")))
                    top_level[k]["preprocess"].append(float(m.group("preprocess")))
                    top_level[k]["prove"].append(float(m.group("prove")))
                    top_level[k]["verify"].append(float(m.group("verify")))

                    # subphases from scratch accumulators
                    for name, val in scratch_preprocess.items():
                        subphases[k]["preprocess"][name].append(val)
                    for name, val in scratch_prove.items():
                        subphases[k]["prove"][name].append(val)
                    for name, val in scratch_verify.items():
                        subphases[k]["verify"][name].append(val)
                    for comp, mb in scratch_sizes.items():
                        proof_sizes[k][comp].append(mb)

                    # reset scratch for next sample
                    scratch_prove.clear(); scratch_preprocess.clear(); scratch_verify.clear(); scratch_sizes.clear()
                    continue

            # end for lines (per file)
    # end for files

    out_dir: Path = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    # Write top-level CSV (long format)
    top_csv = out_dir / "granular_top_level.csv"
    with top_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "variant",
                "benchmark",
                "input_value",
                "input_metric",
                "phase",
                "time_lo_s",
                "time_mid_s",
                "time_hi_s",
                "units",
            ],
        )
        writer.writeheader()
        for (variant, bench, inp), phases in sorted(top_level.items(), key=lambda x: (x[0][0], x[0][1], x[0][2])):
            metric = key_to_metric.get((variant, bench, inp), "n")
            for phase, samples in phases.items():
                lo, mid, hi = summarize(samples)
                writer.writerow(
                    {
                        "variant": variant,
                        "benchmark": bench,
                        "input_value": inp,
                        "input_metric": metric,
                        "phase": phase,
                        "time_lo_s": f"{lo:.6f}",
                        "time_mid_s": f"{mid:.6f}",
                        "time_hi_s": f"{hi:.6f}",
                        "units": "s",
                    }
                )

    # Write subphases CSV (long format)
    sub_csv = out_dir / "granular_subphases.csv"
    with sub_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "variant",
                "benchmark",
                "input_value",
                "input_metric",
                "group",
                "name",
                "time_lo_s",
                "time_mid_s",
                "time_hi_s",
                "units",
            ],
        )
        writer.writeheader()
        for (variant, bench, inp), groups in sorted(subphases.items(), key=lambda x: (x[0][0], x[0][1], x[0][2])):
            metric = key_to_metric.get((variant, bench, inp), "n")
            for group, parts in groups.items():
                for name, samples in parts.items():
                    lo, mid, hi = summarize(samples)
                    writer.writerow(
                        {
                            "variant": variant,
                            "benchmark": bench,
                            "input_value": inp,
                            "input_metric": metric,
                            "group": group,
                            "name": name,
                            "time_lo_s": f"{lo:.6f}",
                            "time_mid_s": f"{mid:.6f}",
                            "time_hi_s": f"{hi:.6f}",
                            "units": "s",
                        }
                    )

    # Write proof sizes CSV (long format)
    size_csv = out_dir / "granular_proof_sizes.csv"
    with size_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "variant",
                "benchmark",
                "input_value",
                "input_metric",
                "component",
                "size_lo_mb",
                "size_mid_mb",
                "size_hi_mb",
                "units",
            ],
        )
        writer.writeheader()
        for (variant, bench, inp), comps in sorted(proof_sizes.items(), key=lambda x: (x[0][0], x[0][1], x[0][2])):
            metric = key_to_metric.get((variant, bench, inp), "n")
            for comp, samples in comps.items():
                lo, mid, hi = summarize(samples)
                writer.writerow(
                    {
                        "variant": variant,
                        "benchmark": bench,
                        "input_value": inp,
                        "input_metric": metric,
                        "component": comp,
                        "size_lo_mb": f"{lo:.6f}",
                        "size_mid_mb": f"{mid:.6f}",
                        "size_hi_mb": f"{hi:.6f}",
                        "units": "MB",
                    }
                )

    # Write a compact JSON summary for convenience
    summary = {
        "top_level": {
            f"{variant}:{bench}:{inp}": {phase: {"lo": min(vals), "mid": median(vals), "hi": max(vals)} for phase, vals in phases.items()}
            for (variant, bench, inp), phases in top_level.items()
        },
        "subphases": {
            f"{variant}:{bench}:{inp}": {grp: {name: {"lo": min(vals), "mid": median(vals), "hi": max(vals)} for name, vals in parts.items()} for grp, parts in groups.items()}
            for (variant, bench, inp), groups in subphases.items()
        },
        "proof_sizes": {
            f"{variant}:{bench}:{inp}": {comp: {"lo": min(vals), "mid": median(vals), "hi": max(vals)} for comp, vals in comps.items()}
            for (variant, bench, inp), comps in proof_sizes.items()
        },
    }
    with (out_dir / "granular_summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"Parsed granular results from {parsed_files} files.")
    print(f"Top-level CSV:   {top_csv}")
    print(f"Subphases CSV:   {sub_csv}")
    print(f"Proof sizes CSV: {size_csv}")


if __name__ == "__main__":
    main()


