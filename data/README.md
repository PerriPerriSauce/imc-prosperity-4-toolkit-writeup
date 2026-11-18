# Data Directory & Provenance Policy

## 1. Directory Structure

This directory enforces strict separation between immutable raw competition CSVs, intermediate artifacts, and machine-readable integrity manifests:

```text
data/
├── raw/prosperity4/
│   ├── round0/         # Tutorial (2 price + 2 trade CSVs; immutable)
│   ├── round1/         # Round 1 (3 price + 3 trade CSVs; immutable)
│   ├── round2/         # Round 2 (3 price + 3 trade CSVs; immutable)
│   ├── round3/         # Round 3 (3 price + 3 trade CSVs; immutable)
│   ├── round4/         # Round 4 (3 price + 3 trade CSVs; immutable)
│   └── round5/         # Round 5 (3 price + 3 trade CSVs; immutable)
├── interim/            # Intermediate parsed frames
├── processed/          # Cleaned validated tables (never modifies raw/)
├── manifests/          # SHA-256 JSON manifest & validation audit policy
└── README.md           # This provenance policy & full 34-file catalog
```

---

## 2. Provenance & Source Attribution

- **Primary Historical Archive**: `https://github.com/kevin-fu1/imc-prosperity-4-backtester/tree/main/prosperity4bt/resources` (**MIT License**)
- **Verified Mirror**: `https://github.com/ADnocap/IMC_Prosperity4/tree/master/data/prosperity4` (byte-for-byte size & file parity verified across Rounds 0–5)
- **Retrieval Date**: `2026-11-18`
- **Format**: UTF-8, semicolon-delimited (`;`) CSV (`17` price columns, `7` trade columns; no separate `observations_round_*.csv` files were distributed in Prosperity 4)
- **Verification**: Audited end-to-end via [`scripts/audit_all_datasets.py`](../scripts/audit_all_datasets.py) and logged in [`data/manifests/prosperity4_manifest.json`](manifests/prosperity4_manifest.json). All **`34/34` files** pass schema, monotonicity, symbol-universe, and timestamp-continuity checks (`all_valid = true`).

---

## 3. Verified Dataset Inventory (Rounds 0–5)

### Round 0 (Tutorial) — `EMERALDS`, `TOMATOES`
| Filename | Rows | Dups | Warnings / Notes | SHA-256 Checksum |
| :--- | ---: | ---: | :--- | :--- |
| `prices_round_0_day_-2.csv` | 20,000 | 0 | Clean (100% two-sided) | `dfe36e0dde81a62ba94391a0c97796fad99b62be27ba174092f65865e261409a` |
| `prices_round_0_day_-1.csv` | 20,000 | 0 | Clean (100% two-sided) | `edf11761f38412c9b29c6338434a90f9a5e2fba7f5426dccb657da04383f1706` |
| `trades_round_0_day_-2.csv` | 588 | 0 | Empty counterparty IDs | `9f108698bb74ccdcd738e3de988846b58ee5ca58148271734bd8b612ff42ade8` |
| `trades_round_0_day_-1.csv` | 631 | 0 | Empty counterparty IDs | `7d106a6133851c10a97f73a79715dfb460c3c00d4e245147e00147bef1248827` |

### Round 1 — `ASH_COATED_OSMIUM`, `INTARIAN_PEPPER_ROOT`
| Filename | Rows | Dups | Warnings / Notes | SHA-256 Checksum |
| :--- | ---: | ---: | :--- | :--- |
| `prices_round_1_day_-2.csv` | 20,000 | 0 | 34 empty-book (`mid_price=0.0`), 1,563 one-sided | `85da1f389ef8a8f16c309d43d8c51b94c35065266f0eff7385cc876ef7762836` |
| `prices_round_1_day_-1.csv` | 20,000 | 0 | 34 empty-book (`mid_price=0.0`), 1,522 one-sided | `33017877198d24d73c4879aabd68d370cc6a53d892ce14903fd639ffd982d2df` |
| `prices_round_1_day_0.csv` | 20,000 | 0 | 35 empty-book (`mid_price=0.0`), 1,480 one-sided | `5c5faa905fa9430434860f0a241f2eeaa5d39c3856ce5615e8b236f774a733b4` |
| `trades_round_1_day_-2.csv` | 773 | 2 | 2 exact duplicate trade prints flagged | `82f07f00d315781ef4bff917c6392e2971332938c790faad217ad1b48d4f7efc` |
| `trades_round_1_day_-1.csv` | 760 | 0 | Valid | `6cf74efc5640fcc3836aa07a24c27f1a12a85ad5fe300f06319044a320cc85f4` |
| `trades_round_1_day_0.csv` | 743 | 0 | Valid | `61512945598ea079bd78033aab39682b6cf6f52326473163aea2f819b12e47ab` |

### Round 2 — `ASH_COATED_OSMIUM`, `INTARIAN_PEPPER_ROOT` (+ MAF Mechanics)
| Filename | Rows | Dups | Warnings / Notes | SHA-256 Checksum |
| :--- | ---: | ---: | :--- | :--- |
| `prices_round_2_day_-1.csv` | 20,000 | 0 | 28 empty-book (`mid_price=0.0`), 1,489 one-sided | `67d52edfa3727543777550cae0cedebf0119fb7d42cd81e7b6e83078c91b2081` |
| `prices_round_2_day_0.csv` | 20,000 | 0 | 34 empty-book (`mid_price=0.0`), 1,479 one-sided | `88c9d8fcbfcccdf125762686dc7667d43c3d6463f6b436e4daf13b53d1d6bcd9` |
| `prices_round_2_day_1.csv` | 20,000 | 0 | 38 empty-book (`mid_price=0.0`), 1,500 one-sided | `e7a36e1344cabee6a68a0d4cbc9d770abc51460a2d85554042121dfff2f84227` |
| `trades_round_2_day_-1.csv` | 790 | 0 | Valid | `6903eda25573f7509ee01db6af0dc18de394390dd13adcefee8a83d12d7ea7bd` |
| `trades_round_2_day_0.csv` | 803 | 0 | Valid | `a53b35ea4992ee817efa739d7966a95f60b8b831330591cb54ebec6e65299a60` |
| `trades_round_2_day_1.csv` | 798 | 0 | Valid | `8ce720389afda43160b6967e734c799ca47404dc3341361701f0ffef15de409b` |

### Round 3 — `HYDROGEL_PACK`, `VELVETFRUIT_EXTRACT`, `VEV_4000..6500` (`12` products)
| Filename | Rows | Dups | Warnings / Notes | SHA-256 Checksum |
| :--- | ---: | ---: | :--- | :--- |
| `prices_round_3_day_0.csv` | 120,000 | 0 | Valid (`VEV_6000`/`6500` `bid_price_1 == 0`) | `fd647c453f2caa268b07b69f112b371fe93aca71dcbb740d32cc058969f54bb2` |
| `prices_round_3_day_1.csv` | 120,000 | 0 | Valid (`VEV_6000`/`6500` `bid_price_1 == 0`) | `90e673b99e3eb9b5a0bb92456bf221471ef2dee2d253e25a648e8772de6b3bc1` |
| `prices_round_3_day_2.csv` | 120,000 | 0 | Valid (`VEV_6000`/`6500` `bid_price_1 == 0`) | `5ff44e653772eb0b63085999be42ec8f6b07bfa722536621f086a90b6eaacff6` |
| `trades_round_3_day_0.csv` | 1,308 | 0 | 182 zero-price prints on `VEV_6000`/`6500`; `9` syms | `c8ba14ccfeb149e6a628cf8d3b9cb39aac262df68c6ee45e524a1c4b3a42a4a8` |
| `trades_round_3_day_1.csv` | 1,407 | 0 | 196 zero-price prints on `VEV_6000`/`6500`; `12` syms | `16c0650eed9c577d0d78b3f5c0a03efa86270aad420e58494337a1745ff7745a` |
| `trades_round_3_day_2.csv` | 1,333 | 0 | 190 zero-price prints on `VEV_6000`/`6500`; `9` syms | `1feef273e1eb7d0f751df4f6e00a21046a4d5cae8432fc62760fa20a76967d03` |

### Round 4 — Counterparty-Identified Options & Spot (`12` products, `Mark 01..67`)
| Filename | Rows | Dups | Warnings / Notes | SHA-256 Checksum |
| :--- | ---: | ---: | :--- | :--- |
| `prices_round_4_day_1.csv` | 120,000 | 0 | Identical book snapshot SHA to R3 Day 1 | `90e673b99e3eb9b5a0bb92456bf221471ef2dee2d253e25a648e8772de6b3bc1` |
| `prices_round_4_day_2.csv` | 120,000 | 0 | Identical book snapshot SHA to R3 Day 2 | `5ff44e653772eb0b63085999be42ec8f6b07bfa722536621f086a90b6eaacff6` |
| `prices_round_4_day_3.csv` | 120,000 | 0 | New Day 3 snapshots (`12` symbols) | `f42a2a716d8f0e1fbcd01425b80e16a949e56d81a4b376adb764d006b6a556c4` |
| `trades_round_4_day_1.csv` | 1,407 | 0 | 196 zero-price prints; `7` buyer / `6` seller IDs | `38e3ec0e68786592e137e60271659782af899f256766ea94368f2fefe8d3a2cb` |
| `trades_round_4_day_2.csv` | 1,333 | 0 | 190 zero-price prints; `7` buyer / `6` seller IDs | `106351fe4a458cfcdb70de0ff7b1d7433e75948ee1485481399b81c57dbea829` |
| `trades_round_4_day_3.csv` | 1,541 | 0 | 253 zero-price prints; `7` buyer / `6` seller IDs | `6c7829ff5c6652757f34c5a4b32aedbc08b5cdd234f8e7899ce7fc99d6e1f905` |

### Round 5 ("The Final Stretch") — `50` Products Across `10` Categories
| Filename | Rows | Dups | Warnings / Notes | SHA-256 Checksum |
| :--- | ---: | ---: | :--- | :--- |
| `prices_round_5_day_2.csv` | 500,000 | 0 | 100% two-sided (`50` symbols $\times$ `10,000` ticks) | `301088d6ad51d1d25a0198782aa09e64e4b42d7eac65b2ee1bda5636514578f4` |
| `prices_round_5_day_3.csv` | 500,000 | 0 | 100% two-sided (`50` symbols $\times$ `10,000` ticks) | `cf829d81df6163640c935cc297591a6200fec14e23fe80fd1ca02c0f7c559d3a` |
| `prices_round_5_day_4.csv` | 500,000 | 0 | 100% two-sided (`50` symbols $\times$ `10,000` ticks) | `aae5c4b7b840c1e52a4dd07d2e33fdc9759d40fa4b2354f6a9274e6bf4baf7bc` |
| `trades_round_5_day_2.csv` | 11,090 | 0 | All `50` symbols; counterparty IDs removed | `5546f9248b5d0f2c5e885a277a1682f940bb1a983f543cb144b1f13cc0d52e88` |
| `trades_round_5_day_3.csv` | 12,320 | 0 | All `50` symbols; counterparty IDs removed | `b94c8ac3b9297a571c228de3f2b7e857927837ed6a28134ccfa0e72d6c7965b0` |
| `trades_round_5_day_4.csv` | 11,975 | 0 | All `50` symbols; counterparty IDs removed | `f7f9109f0bd26091c3cf4c7a9fdc5ba6e1a4adf777e08a2a0894a1ba2d4c7fb9` |
