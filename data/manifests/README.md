# Data Manifests & Validation Reports

This directory stores machine-readable dataset manifests and integrity audit logs generated across all immutable source files in `data/raw/prosperity4/`.

## Generated Artifacts
- [`prosperity4_manifest.json`](prosperity4_manifest.json): Full per-file SHA-256 registry, row counts, null audits, symbol checks, timestamp continuity results, and ingestion warnings for all `34` raw CSV files (`round0`–`round5`).
- CSV summary table: [`reports/tables/data_inventory_summary.csv`](../../reports/tables/data_inventory_summary.csv).

## Regenerating & Verifying Checksums

```bash
uv run python scripts/audit_all_datasets.py
```

Every ingested file is checked against `DataIntegrityValidator` (schema column whitelist/required fields, L1–L3 monotonicity, non-crossing spreads, empty-book & deep-OTM zero-price audit warnings, duplicate detection, and `100`-step timestamp continuity) without touching raw files on disk.
