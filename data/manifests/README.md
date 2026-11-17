# Data Manifests & Validation Reports

This directory stores structured dataset manifests, SHA-256 checksum registries, and ingestion validation reports produced by `prosperity_toolkit.data.validation.DataIntegrityValidator`.

## Manifest Fields

Every ingested dataset manifest records:
- **Source**: Origin repository or official competition portal URL.
- **Retrieval Date**: ISO 8601 date of acquisition (`YYYY-MM-DD`).
- **Original Filename**: Exact filename at retrieval (`prices_round_<R>_day_<D>.csv` or `trades_round_<R>_day_<D>.csv`).
- **File Format**: UTF-8, semicolon-delimited (`;`) CSV.
- **Schema**: Verified column names and types (`PRICE_CSV_COLUMNS` / `TRADE_CSV_COLUMNS`).
- **SHA-256 Checksum**: Computed via `prosperity_toolkit.data.validation.compute_sha256`.
- **Known Limitations**: E.g., empty-book ticks (`mid_price == 0.0`), empty `buyer`/`seller` columns in Round 0–1, or duplicate trade prints.
- **Verification Status**: `Valid` (0 structural errors) or `Invalid` with explicit error diagnostics.

## Generating a Manifest Report

```bash
uv run python -c "
from pathlib import Path
from prosperity_toolkit.data.loader import DataLoader
for p in sorted(Path('data/raw/prosperity4').rglob('*.csv')):
    _, rep = DataLoader.ingest_csv(p)
    print(rep.filepath, rep.is_valid, rep.sha256)
"
```
