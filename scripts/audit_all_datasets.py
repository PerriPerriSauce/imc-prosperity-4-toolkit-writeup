"""Audit all ingested Prosperity 4 CSVs and emit or verify SHA-256 manifest + inventory table."""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict
from datetime import date
from pathlib import Path

from prosperity_toolkit.competition import get_round_products
from prosperity_toolkit.core.exceptions import DataValidationError
from prosperity_toolkit.data.loader import DataLoader
from prosperity_toolkit.data.validation import DataIntegrityValidator

RAW_ROOT = Path("data/raw/prosperity4")
MANIFEST_PATH = Path("data/manifests/prosperity4_manifest.json")
INVENTORY_CSV = Path("reports/tables/data_inventory_summary.csv")

SOURCE_URLS = (
    "https://github.com/kevin-fu1/imc-prosperity-4-backtester/tree/main/"
    "prosperity4bt/resources (MIT License)",
    "https://github.com/ADnocap/IMC_Prosperity4/tree/master/data/prosperity4 "
    "(verified mirror)",
)


def _audit_file(path: Path) -> tuple[dict[str, object], bool]:
    rel_path = path.relative_to(Path(".")).as_posix()
    df, report = DataLoader.ingest_csv(path)
    rec: dict[str, object] = asdict(report)
    rec["filepath"] = rel_path
    rec["file_size_bytes"] = path.stat().st_size

    extra_errors = list(report.errors)
    continuity_ok = True
    one_sided_ticks = 0
    empty_ticks = 0
    zero_price_trades = 0
    buyer_ids = 0
    seller_ids = 0

    if report.round_num is not None:
        expected_prods = set(get_round_products(report.round_num))
        obs_syms = set(report.symbols)
        if report.dataset_type == "prices" and obs_syms != expected_prods:
            extra_errors.append(
                f"Symbol mismatch: expected {sorted(expected_prods)}, got {sorted(obs_syms)}",
            )
        elif report.dataset_type == "trades" and not obs_syms <= expected_prods:
            extra_errors.append(
                f"Unexpected trade symbols: {sorted(obs_syms - expected_prods)}",
            )

    if report.dataset_type == "prices":
        one_sided_ticks = int(
            (df["bid_price_1"].isna() ^ df["ask_price_1"].isna()).sum(),
        )
        empty_ticks = int(
            (df["bid_price_1"].isna() & df["ask_price_1"].isna()).sum(),
        )
        try:
            DataIntegrityValidator.validate_timestamp_continuity(df)
        except DataValidationError as err:
            continuity_ok = False
            extra_errors.append(str(err))
    elif report.dataset_type == "trades":
        zero_price_trades = int((df["price"] == 0).sum()) if not df.empty else 0
        buyer_ids = int(df["buyer"].dropna().astype(str).nunique())
        seller_ids = int(df["seller"].dropna().astype(str).nunique())

    is_valid = len(extra_errors) == 0
    rec["errors"] = extra_errors
    rec["is_valid"] = is_valid
    rec["continuity_ok"] = continuity_ok
    rec["one_sided_ticks"] = one_sided_ticks
    rec["empty_book_ticks"] = empty_ticks
    rec["zero_price_trades"] = zero_price_trades
    rec["unique_buyer_ids"] = buyer_ids
    rec["unique_seller_ids"] = seller_ids
    return rec, is_valid


def _verify_against_manifest(csv_paths: list[Path]) -> int:
    if not MANIFEST_PATH.exists():
        print(f"Manifest not found for verification: {MANIFEST_PATH}")
        return 1
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    manifest_files = manifest.get("files", [])
    expected_map = {str(entry["filepath"]): entry for entry in manifest_files}
    actual_rel = [path.relative_to(Path(".")).as_posix() for path in csv_paths]

    if set(actual_rel) != set(expected_map):
        missing = sorted(set(expected_map) - set(actual_rel))
        extra = sorted(set(actual_rel) - set(expected_map))
        print(f"Manifest file set mismatch: missing={missing}, extra={extra}")
        return 1

    mismatches = 0
    for path in csv_paths:
        rec, is_valid = _audit_file(path)
        rel = str(rec["filepath"])
        exp = expected_map[rel]
        if not is_valid:
            print(f"VALIDATION FAILED for {rel}: {rec['errors']}")
            mismatches += 1
        elif (
            rec["sha256"] != exp.get("sha256")
            or rec["row_count"] != exp.get("row_count")
            or rec["duplicate_count"] != exp.get("duplicate_count")
        ):
            print(
                f"MANIFEST MISMATCH for {rel}: "
                f"sha256=({rec['sha256']} vs {exp.get('sha256')}), "
                f"rows=({rec['row_count']} vs {exp.get('row_count')})",
            )
            mismatches += 1

    print(
        f"Verified {len(csv_paths)} raw CSV files against {MANIFEST_PATH} "
        f"(mismatches={mismatches})",
    )
    return 1 if mismatches > 0 else 0


def main(argv: list[str] | None = None) -> int:
    """Validate all raw CSVs under data/raw/prosperity4 and emit or verify manifest."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Verify raw CSV schemas, continuity, and SHA-256 digests without writing files.",
    )
    args = parser.parse_args(argv)

    if not RAW_ROOT.exists():
        print(f"Raw directory not found: {RAW_ROOT}")
        return 1

    csv_paths = sorted(RAW_ROOT.rglob("*.csv"))
    if args.verify_only:
        return _verify_against_manifest(csv_paths)

    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    INVENTORY_CSV.parent.mkdir(parents=True, exist_ok=True)

    records: list[dict[str, object]] = []
    any_error = False

    for path in csv_paths:
        rec, is_valid = _audit_file(path)
        if not is_valid:
            any_error = True
        records.append(rec)
        print(
            f"{rec['filepath']}: rows={rec['row_count']} syms={len(rec['symbols'])} "  # type: ignore[arg-type]
            f"dups={rec['duplicate_count']} valid={is_valid} "
            f"warnings={len(rec['warnings'])}",  # type: ignore[arg-type]
        )

    manifest = {
        "competition": "IMC Prosperity 4 (April 2026)",
        "generated_on": str(date.today()),
        "sources": list(SOURCE_URLS),
        "format": "UTF-8 semicolon-delimited (;) CSV",
        "total_files": len(records),
        "all_valid": not any_error,
        "files": records,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    csv_fields = [
        "filepath",
        "dataset_type",
        "round_num",
        "day_num",
        "file_size_bytes",
        "row_count",
        "duplicate_count",
        "one_sided_ticks",
        "empty_book_ticks",
        "zero_price_trades",
        "unique_buyer_ids",
        "unique_seller_ids",
        "continuity_ok",
        "is_valid",
        "sha256",
        "warnings",
    ]
    with INVENTORY_CSV.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=csv_fields)
        writer.writeheader()
        for rec in records:
            row = {k: rec[k] for k in csv_fields}
            row["warnings"] = "; ".join(rec["warnings"])  # type: ignore[arg-type]
            writer.writerow(row)

    print(
        f"\nManifest saved to {MANIFEST_PATH} "
        f"(total_files={len(records)}, all_valid={not any_error})",
    )
    return 1 if any_error else 0


if __name__ == "__main__":
    raise SystemExit(main())
