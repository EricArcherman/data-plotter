#!/usr/bin/env python3

"""
Parse Jolt benchmark outputs from text files and produce tidy CSV/JSON.

Inputs: benchmark .txt files produced by Criterion.rs-like output, e.g.:
  - 32-reg/collatz.txt
  - 32-reg/fibonacci.txt
  - 32-reg/sha2_chain.txt
  - 32-reg/sha3_chain.txt
  - untouched/{collatz,fibonacci,sha2_chain,sha3_chain}.txt
  - v-reg/{collatz,fibonacci,sha2_chain,sha3_chain}.txt

Outputs (by default in the same directory as this script):
  - parsed_benchmarks.csv
  - parsed_benchmarks.json

Each record includes: variant, benchmark, input_label, input_value, input_metric,
time_lo_s, time_mid_s, time_hi_s, units, and source_file.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable, List, Optional, Tuple


# Regexes to match benchmark result lines.
# 1) Combined label+time on one line (common for collatz and sha*_chain):
COMBINED_TIME_LINE = re.compile(
    r"^\s*"
    r"(?P<label>"
    r"(?:(?P<ordinal>\d+)(?:th|st|nd|rd)\s+(?P<num_name>(?:fibonacci|collatz)\s+number))"
    r"|(?:(?P<count>\d+)\s+(?P<sha>sha2|sha3)\s+chain\s+cycles)"
    r")\s+time:\s+\["
    r"(?P<lo>[0-9]+\.[0-9]+)\s*s\s+"
    r"(?P<mid>[0-9]+\.[0-9]+)\s*s\s+"
    r"(?P<hi>[0-9]+\.[0-9]+)\s*s\]"
)

# 2) Label-only line followed by a separate indented "time: [...]" line (seen in fibonacci):
LABEL_ONLY_LINE = re.compile(
    r"^\s*(?P<ordinal>\d+)(?:th|st|nd|rd)\s+(?P<num_name>(?:fibonacci|collatz)\s+number)\s*$"
)

TIME_ONLY_LINE = re.compile(
    r"^\s*time:\s+\["
    r"(?P<lo>[0-9]+\.[0-9]+)\s*s\s+"
    r"(?P<mid>[0-9]+\.[0-9]+)\s*s\s+"
    r"(?P<hi>[0-9]+\.[0-9]+)\s*s\]"
)


@dataclass
class BenchmarkRecord:
    variant: str
    benchmark: str
    input_label: str
    input_value: int
    input_metric: str  # "n" for fibonacci/collatz; "cycles" for sha2/sha3
    time_lo_s: float
    time_mid_s: float
    time_hi_s: float
    units: str
    source_file: str


def parse_benchmark_file(path: Path) -> List[BenchmarkRecord]:
    variant = path.parent.name  # e.g., "32-reg", "untouched", "v-reg"
    benchmark = path.stem       # e.g., "fibonacci", "collatz", "sha2_chain", "sha3_chain"
    input_metric = "cycles" if benchmark in {"sha2_chain", "sha3_chain"} else "n"

    records: List[BenchmarkRecord] = []
    pending_label: Optional[Tuple[int, str]] = None  # (input_value, input_label)

    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return records

    for raw_line in text.splitlines():
        line = raw_line.rstrip("\n")

        # Try combined label + time line
        m = COMBINED_TIME_LINE.match(line)
        if m:
            lo = float(m.group("lo"))
            mid = float(m.group("mid"))
            hi = float(m.group("hi"))

            if m.group("ordinal") and m.group("num_name"):
                # Fibonacci or Collatz format
                input_value = int(m.group("ordinal"))
                input_label = f"{input_value}th {m.group('num_name')}"
            elif m.group("count") and m.group("sha"):
                # sha2/sha3 chain cycles
                input_value = int(m.group("count"))
                input_label = f"{input_value} {m.group('sha')} chain cycles"
            else:
                # Shouldn't happen; skip defensively
                continue

            records.append(
                BenchmarkRecord(
                    variant=variant,
                    benchmark=benchmark,
                    input_label=input_label,
                    input_value=input_value,
                    input_metric=input_metric,
                    time_lo_s=lo,
                    time_mid_s=mid,
                    time_hi_s=hi,
                    units="s",
                    source_file=str(path),
                )
            )
            pending_label = None
            continue

        # Track a label-only line; expect a following TIME_ONLY_LINE
        m = LABEL_ONLY_LINE.match(line)
        if m:
            input_value = int(m.group("ordinal"))
            input_label = f"{input_value}th {m.group('num_name')}"
            pending_label = (input_value, input_label)
            continue

        # If we have a pending label, see if this line has only the time
        if pending_label is not None:
            m = TIME_ONLY_LINE.match(line)
            if m:
                lo = float(m.group("lo"))
                mid = float(m.group("mid"))
                hi = float(m.group("hi"))
                input_value, input_label = pending_label
                records.append(
                    BenchmarkRecord(
                        variant=variant,
                        benchmark=benchmark,
                        input_label=input_label,
                        input_value=input_value,
                        input_metric=input_metric,
                        time_lo_s=lo,
                        time_mid_s=mid,
                        time_hi_s=hi,
                        units="s",
                        source_file=str(path),
                    )
                )
                pending_label = None
                continue

    return records


def discover_default_inputs(root: Path) -> List[Path]:
    candidates: List[Path] = []
    variants = ["32-reg", "untouched", "v-reg", "no-reg"]
    benchmarks = ["collatz", "fibonacci", "sha2_chain", "sha3_chain"]
    for variant in variants:
        for bench in benchmarks:
            p = root / variant / f"{bench}.txt"
            if p.exists():
                candidates.append(p)
    return candidates


def write_csv(records: Iterable[BenchmarkRecord], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "variant",
        "benchmark",
        "input_label",
        "input_value",
        "input_metric",
        "time_lo_s",
        "time_mid_s",
        "time_hi_s",
        "units",
        "source_file",
    ]
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for rec in records:
            writer.writerow(asdict(rec))


def write_json(records: Iterable[BenchmarkRecord], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump([asdict(r) for r in records], f, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse Jolt benchmark outputs into CSV/JSON")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).parent,
        help="Root directory containing variant subfolders (default: this script's directory)",
    )
    parser.add_argument(
        "--inputs",
        type=Path,
        nargs="*",
        help="Explicit list of .txt files to parse (overrides --root discovery)",
    )
    parser.add_argument(
        "--out-csv",
        type=Path,
        default=Path(__file__).parent / "parsed_benchmarks.csv",
        help="Output CSV path",
    )
    parser.add_argument(
        "--out-json",
        type=Path,
        default=Path(__file__).parent / "parsed_benchmarks.json",
        help="Output JSON path",
    )
    args = parser.parse_args()

    if args.inputs:
        inputs = [p for p in args.inputs if p.exists()]
    else:
        inputs = discover_default_inputs(args.root)

    all_records: List[BenchmarkRecord] = []
    for path in inputs:
        all_records.extend(parse_benchmark_file(path))

    # Sort for stable output: benchmark, input_value, variant
    all_records.sort(key=lambda r: (r.benchmark, r.input_value, r.variant))

    write_csv(all_records, args.out_csv)
    write_json(all_records, args.out_json)

    print(f"Parsed {len(all_records)} records from {len(inputs)} files.")
    print(f"CSV:  {args.out_csv}")
    print(f"JSON: {args.out_json}")


if __name__ == "__main__":
    main()

