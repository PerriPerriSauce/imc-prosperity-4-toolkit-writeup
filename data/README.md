# Data Directory & Provenance Policy

## 1. Directory Structure

This directory enforces strict separation between immutable source data, intermediate tables, and validated datasets:

```text
data/
├── raw/
│   └── prosperity4/
│       ├── round0/     # Tutorial round raw CSVs (read-only)
│       └── round1/     # Round 1 raw CSVs (read-only)
├── interim/            # Intermediate parsed artifacts
├── processed/          # Cleaned, schema-validated binary Parquet datasets
├── manifests/          # Checksum manifests and validation reports
│   └── README.md
└── README.md           # This provenance policy and dataset catalog
```

## 2. Data Provenance & Integrity Rules

1. **Source Immutability**:
   - Files placed in `data/raw/` must never be edited, modified, or overwritten.
   - Any normalization or feature engineering writes exclusively to `data/interim/` or `data/processed/`.
2. **Attribution & Checksums**:
   - Every external dataset records its source URL, retrieval date, original filename, format, usage restrictions, and SHA-256 checksum.

---

## 3. Verified Local Dataset Inventory

- **Source**: Public IMC Prosperity 4 data archive (`https://github.com/ADnocap/IMC_Prosperity4/tree/master/data/prosperity4`)
- **Retrieval Date**: `2026-11-18`
- **Format**: UTF-8, semicolon-delimited (`;`) CSV
- **Verification Status**: Verified locally via `prosperity_toolkit.data.loader.DataLoader.ingest_csv`

### Round 0 (Tutorial) — `EMERALDS`, `TOMATOES`
| Filename | Rows | Duplicates | Validation Status | SHA-256 Checksum |
| :--- | :--- | :--- | :--- | :--- |
| `prices_round_0_day_-1.csv` | 20,000 | 0 | Valid | `edf11761f38412c9b29c6338434a90f9a5e2fba7f5426dccb657da04383f1706` |
| `prices_round_0_day_-2.csv` | 20,000 | 0 | Valid | `dfe36e0dde81a62ba94391a0c97796fad99b62be27ba174092f65865e261409a` |
| `trades_round_0_day_-1.csv` | 631 | 0 | Valid | `7d106a6133851c10a97f73a79715dfb460c3c00d4e245147e00147bef1248827` |
| `trades_round_0_day_-2.csv` | 588 | 0 | Valid | `9f108698bb74ccdcd738e3de988846b58ee5ca58148271734bd8b612ff42ade8` |

### Round 1 — `ASH_COATED_OSMIUM`, `INTARIAN_PEPPER_ROOT`
| Filename | Rows | Duplicates | Validation Status & Notes | SHA-256 Checksum |
| :--- | :--- | :--- | :--- | :--- |
| `prices_round_1_day_-2.csv` | 20,000 | 0 | Valid (34 empty-book rows with `mid_price == 0.0`) | `85da1f389ef8a8f16c309d43d8c51b94c35065266f0eff7385cc876ef7762836` |
| `prices_round_1_day_-1.csv` | 20,000 | 0 | Valid (34 empty-book rows with `mid_price == 0.0`) | `33017877198d24d73c4879aabd68d370cc6a53d892ce14903fd639ffd982d2df` |
| `prices_round_1_day_0.csv` | 20,000 | 0 | Valid (35 empty-book rows with `mid_price == 0.0`) | `5c5faa905fa9430434860f0a241f2eeaa5d39c3856ce5615e8b236f774a733b4` |
| `trades_round_1_day_-2.csv` | 773 | 2 | Valid (2 exact duplicate trade records flagged) | `82f07f00d315781ef4bff917c6392e2971332938c790faad217ad1b48d4f7efc` |
| `trades_round_1_day_-1.csv` | 760 | 0 | Valid | `6cf74efc5640fcc3836aa07a24c27f1a12a85ad5fe300f06319044a320cc85f4` |
| `trades_round_1_day_0.csv` | 743 | 0 | Valid | `61512945598ea079bd78033aab39682b6cf6f52326473163aea2f819b12e47ab` |

### Rounds 2–5
- **Status**: **Not yet ingested locally**. Requires retrieval and SHA-256 verification before use.
