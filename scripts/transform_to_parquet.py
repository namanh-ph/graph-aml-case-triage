"""Transform bronze-layer CSV deliverables into silver-layer Parquet.

Reads CSV files from ``data/bronze/`` (immutable, as-received) and writes
columnar Parquet copies to ``data/silver/`` (analytical layer). The bronze
layer is never mutated by downstream code; the silver layer is regenerated
by this script and consumed by the rest of the pipeline.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import polars as pl

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BRONZE_DIR = PROJECT_ROOT / "data" / "bronze"
DEFAULT_SILVER_DIR = PROJECT_ROOT / "data" / "silver"

TABLES: tuple[str, ...] = (
    "accounts",
    "counterparties",
    "countries",
    "customers",
    "devices",
    "scenario_manifest",
    "transactions",
)


def transform(bronze_dir: Path, silver_dir: Path) -> int:
    """Read each known table from ``bronze_dir`` and write Parquet to ``silver_dir``."""

    if not bronze_dir.is_dir():
        print(f"Bronze directory not found: {bronze_dir}")
        return 1
    silver_dir.mkdir(parents=True, exist_ok=True)

    print(f"Bronze: {bronze_dir}")
    print(f"Silver: {silver_dir}")
    print()

    converted = 0
    total_csv_bytes = 0
    total_parquet_bytes = 0
    for table in TABLES:
        csv_path = bronze_dir / f"{table}.csv"
        parquet_path = silver_dir / f"{table}.parquet"
        if not csv_path.is_file():
            print(f"  SKIP {table}: source CSV missing")
            continue
        df = pl.read_csv(csv_path, try_parse_dates=True)
        df.write_parquet(parquet_path, compression="snappy")
        csv_bytes = csv_path.stat().st_size
        parquet_bytes = parquet_path.stat().st_size
        total_csv_bytes += csv_bytes
        total_parquet_bytes += parquet_bytes
        converted += 1
        print(
            f"  {table:20s} {df.height:>9,} rows   "
            f"CSV {csv_bytes / 1024:>9.1f} KB -> Parquet {parquet_bytes / 1024:>9.1f} KB"
        )

    if converted == 0:
        print("No tables converted.")
        return 1

    print()
    print(
        f"  TOTAL              CSV {total_csv_bytes / 1024 / 1024:>6.2f} MB -> "
        f"Parquet {total_parquet_bytes / 1024 / 1024:>6.2f} MB "
        f"({total_parquet_bytes / total_csv_bytes:.1%})"
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the transform CLI parser."""

    parser = argparse.ArgumentParser(
        description="Transform bronze-layer CSV deliverables into silver-layer Parquet."
    )
    parser.add_argument(
        "--bronze-dir",
        type=Path,
        default=DEFAULT_BRONZE_DIR,
        help="Bronze layer directory containing raw CSV files (default: data/bronze).",
    )
    parser.add_argument(
        "--silver-dir",
        type=Path,
        default=DEFAULT_SILVER_DIR,
        help="Silver layer directory to write Parquet files (default: data/silver).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the transform CLI."""

    args = build_parser().parse_args(argv)
    return transform(args.bronze_dir, args.silver_dir)


if __name__ == "__main__":
    raise SystemExit(main())
