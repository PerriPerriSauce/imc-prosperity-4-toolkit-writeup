# Data Directory & Provenance Policy

## 1. Directory Structure

This directory adheres to strict data immutability and provenance tracking standards:

```text
data/
├── raw/            # Immutable raw competition CSVs (read-only)
│   └── round_{0..5}/
│       ├── prices_round_N_day_D.csv
│       └── trades_round_N_day_D.csv
├── interim/        # Intermediate artifacts (e.g. parsed parquet before validation)
├── processed/      # Cleaned, schema-validated, binary Parquet datasets for fast backtest replay
└── README.md       # This provenance policy and catalog
```

## 2. Data Provenance & Integrity Rules

1. **Source Immutability**:
   - Files placed in `data/raw/` must never be edited, modified, or overwritten by any script or agent.
   - Any cleaning, normalization, or feature engineering must write to `data/interim/` or `data/processed/`.

2. **Provenance Catalog**:
   - For every dataset ingested, record:
     - **Source**: IMC Prosperity 4 Competition Portal (or official distribution).
     - **Retrieval Date**: ISO 8601 timestamp.
     - **Original Filename**: Exact filename at download.
     - **Data Format**: Delimiter (semicolon), encoding (UTF-8), columns.
     - **SHA-256 Checksum**: Cryptographic verification hash.

3. **Current Dataset Catalog**:
   - *Status*: Raw datasets have not yet been placed in the repository. Synthetic verification fixtures for smoke tests are located under `tests/fixtures/`.
   - When placing official CSVs in `data/raw/`, calculate and verify checksums using:
     ```powershell
     Get-FileHash -Algorithm SHA256 data/raw/round_1/*.csv
     ```
