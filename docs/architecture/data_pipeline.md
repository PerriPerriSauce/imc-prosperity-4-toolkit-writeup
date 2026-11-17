# Architecture: Data Pipeline & Integrity

## 1. Raw Market Data Ingestion

The IMC Prosperity 4 exchange produces two primary historical market feeds:
1. **Prices & Order Book Depths (`prices_round_N_day_D.csv`)**: Semicolon-delimited records containing 3 levels of bid/ask prices and volumes, mid-price, and exchange profit-and-loss benchmark.
2. **Executed Market Trades (`trades_round_N_day_D.csv`)**: Semicolon-delimited records reporting timestamp, buyer, seller, symbol, execution price, and executed quantity.

## 2. Ingestion & Validation Lifecycle

```
[Raw CSVs] 
    |
    v (SemicolonCSVParser)
[Raw DataFrame] 
    |
    v (DataNormalizer)
[Standardized DataFrame] 
    |
    v (DataIntegrityValidator: Spread, Monotonicity, Continuity)
[Validated Clean Parquet]
```

### Mathematical & Microstructural Invariants Enforced

1. **Spread Positivity**:
   $$\text{Spread}_t = P_{\text{ask}, 1}(t) - P_{\text{bid}, 1}(t) > 0$$
   Crossed books ($\text{Spread}_t \le 0$) indicate corrupt records or market halt conditions.

2. **Order Book Monotonicity**:
   $$P_{\text{bid}, 1} > P_{\text{bid}, 2} > P_{\text{bid}, 3}$$
   $$P_{\text{ask}, 1} < P_{\text{ask}, 2} < P_{\text{ask}, 3}$$

3. **Discrete Timestamp Regularity**:
   $$t_{k} - t_{k-1} = 100 \quad \forall k$$
   Missing timestamps represent missing state that must be explicitly interpolated or flagged as auction halts.
