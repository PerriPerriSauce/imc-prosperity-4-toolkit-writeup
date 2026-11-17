# IMC Prosperity 4 — Competition Specification

**Verification Policy**: Only details directly verified against attributable public resources (`datamodel.py`, raw competition CSV datasets, and public IMC Prosperity 4 documentation) are marked as **Verified**. Any parameter or runtime limit not directly confirmed in official documentation or local data is explicitly marked **UNVERIFIED** along with the evidence required to confirm it.

---

## 1. Competition Round Structure

| Round | Name / Phase | Status | Evidence Source |
| :--- | :--- | :--- | :--- |
| **Round 0** | Tutorial Round | **Verified** | Raw CSVs (`prices_round_0_day_{-2,-1}.csv`), public competition overview. |
| **Round 1** | Round 1 | **Verified** | Raw CSVs (`prices_round_1_day_{-2,-1,0}.csv`). |
| **Round 2** | Round 2 | **Partially Verified** | Publicly documented as introducing MAF auction mechanics; raw CSVs not yet ingested locally. |
| **Round 3** | Round 3 | **Partially Verified** | Publicly documented as resetting prior products (`HYDROGEL_PACK`, `VELVETFRUIT_EXTRACT`, `VEV_*`); raw CSVs not yet ingested locally. |
| **Round 4** | Round 4 | **Partially Verified** | Publicly documented as continuing Round 3 products with `buyer`/`seller` fields populated; raw CSVs not yet ingested locally. |
| **Round 5** | Round 5 ("The Final Stretch") | **Partially Verified** | Publicly documented as resetting prior products and introducing 50 new products across 10 categories; raw CSVs not yet ingested locally. |

- **Tick Granularity**: **Verified** in Round 0 & Round 1 CSVs (`timestamp` increments in discrete steps of `100` from `0` to `999,900`, i.e., `10,000` ticks per trading day).
- **Base Currency**: **Verified** in Round 0 & Round 1 trades CSVs (`currency = XIRECS`).

---

## 2. Products, Instruments, and Position Limits by Round

| Round | Product / Symbol | Position Limit | Verification Status & Evidence Required |
| :--- | :--- | :--- | :--- |
| **Round 0** | `EMERALDS`, `TOMATOES` | **UNVERIFIED** | Symbols **Verified** in `prices_round_0_day_{-2,-1}.csv`. Exact per-product position limits require official Prosperity 4 Round 0 wiki/rules table. |
| **Round 1** | `ASH_COATED_OSMIUM`, `INTARIAN_PEPPER_ROOT` | **UNVERIFIED** | Symbols **Verified** in `prices_round_1_day_{-2,-1,0}.csv`. Exact per-product position limits require official Prosperity 4 Round 1 wiki/rules table (or portal rejection logs). |
| **Round 2** | `ASH_COATED_OSMIUM`, `INTARIAN_PEPPER_ROOT`, MAF auction | **UNVERIFIED** | Requires official Round 2 wiki/rules and local Round 2 CSV ingestion. |
| **Round 3** | `HYDROGEL_PACK`, `VELVETFRUIT_EXTRACT`, `VEV_*` | **UNVERIFIED** | Requires official Round 3 wiki/rules and local Round 3 CSV ingestion. |
| **Round 4** | Round 3 products (with counterparty IDs) | **UNVERIFIED** | Requires official Round 4 wiki/rules and local Round 4 CSV ingestion. |
| **Round 5** | 50 products across 10 categories (5 each) | `10` (reported in public reference docs; **UNVERIFIED** against official wiki) | Requires official Round 5 wiki/rules and local Round 5 CSV ingestion. |

---

## 3. Authoritative Data Model (`datamodel.py`)

Verified against the public Prosperity 4 `datamodel.py` (see [`traders/datamodel.py`](../../traders/datamodel.py)):

### Type Aliases
- `Time = int`
- `Symbol = str`
- `Product = str`
- `Position = int`
- `UserId = str`
- `ObservationValue = int`

### Core Classes

1. **`Listing(symbol: Symbol, product: Product, denomination: int)`**
   - Metadata describing each tradable instrument.
2. **`Order(symbol: Symbol, price: int, quantity: int)`**
   - `price`: Integer limit price.
   - `quantity`: Signed integer (`> 0` for buy, `< 0` for sell).
3. **`OrderDepth()`**
   - `buy_orders: Dict[int, int]`: Maps bid price $\to$ **positive** volume.
   - `sell_orders: Dict[int, int]`: Maps ask price $\to$ **negative** volume.
4. **`Trade(symbol: Symbol, price: int, quantity: int, buyer: UserId = None, seller: UserId = None, timestamp: int = 0)`**
   - Represents an executed trade print. Note: in Round 0 & Round 1 public trade CSVs, `buyer` and `seller` are empty (`NaN`).
5. **`ConversionObservation(bidPrice: float, askPrice: float, transportFees: float, exportTariff: float, importTariff: float, sugarPrice: float, sunlightIndex: float)`**
   - Environmental and cross-exchange conversion quote parameters.
6. **`Observation(plainValueObservations: Dict[Product, ObservationValue], conversionObservations: Dict[Product, ConversionObservation])`**
   - Container delivered via `state.observations`.
7. **`TradingState(traderData: str, timestamp: Time, listings: Dict[Symbol, Listing], order_depths: Dict[Symbol, OrderDepth], own_trades: Dict[Symbol, List[Trade]], market_trades: Dict[Symbol, List[Trade]], position: Dict[Product, Position], observations: Observation)`**
   - Includes `toJSON()` helper using `json.dumps(self, default=lambda o: o.__dict__, sort_keys=True)`.
8. **`ProsperityEncoder(JSONEncoder)`**
   - JSON serializer returning `o.__dict__`.

---

## 4. `Trader.run` Interface & State Semantics

- **Entrypoint**:
  ```python
  class Trader:
      def run(self, state: TradingState) -> tuple[dict[Symbol, list[Order]], int, str]:
          ...
  ```
- **Return Values**:
  1. `result: dict[Symbol, list[Order]]` — Orders to submit for each symbol on the current tick.
  2. `conversions: int` — Requested conversion quantity (or `0` when no conversion is requested).
  3. `traderData: str` — Serialized string passed back into `state.traderData` on the subsequent tick.
- **Persistent `traderData` Semantics**: **Verified** in `TradingState` signature (`traderData: str` input, `str` output). Exact maximum byte/character length limit on `traderData` is **UNVERIFIED** (requires official Prosperity 4 submission documentation).

---

## 5. Submission Runtime Restrictions

| Restriction | Status | Details / Evidence Required |
| :--- | :--- | :--- |
| **Single-File Upload** | **Verified** | Submissions are uploaded as a single standalone `.py` file containing `class Trader`. |
| **Available Libraries** | **Partially Verified** | `datamodel.py` uses `json`, `typing`, `jsonpickle`. Standard library and `numpy` are documented in community guides; exact `pandas`/`scipy` availability and versions on the Prosperity 4 evaluation container are **UNVERIFIED** without official sandbox docs or portal test logs. |
| **Per-Tick / Total Time Limit** | **UNVERIFIED** | Community guides report strict millisecond per-tick budgets and total run timeouts; exact numerical timeout thresholds require official Prosperity 4 documentation or portal run logs. |
| **Memory & Log Size Limits** | **UNVERIFIED** | Exact RAM limit and stdout character truncation threshold require official Prosperity 4 documentation. |

---

## 6. Available Historical Data Formats

Verified directly from ingested Round 0 and Round 1 CSV files:

1. **Prices & Order Book CSV (`prices_round_<R>_day_<D>.csv`)**:
   - Delimiter: `;` (semicolon)
   - Columns (17): `day;timestamp;product;bid_price_1;bid_volume_1;bid_price_2;bid_volume_2;bid_price_3;bid_volume_3;ask_price_1;ask_volume_1;ask_price_2;ask_volume_2;ask_price_3;ask_volume_3;mid_price;profit_and_loss`
   - Observed nuances:
     - `ask_volume_{1,2,3}` are **positive** in the CSV, whereas `OrderDepth.sell_orders` uses **negative** quantities.
     - One-sided books (missing `bid_price_1` or `ask_price_1`) occur naturally.
     - Empty books (both sides missing) occur in Round 1 (`ASH_COATED_OSMIUM`), recorded with `mid_price = 0.0`.
2. **Public Trades CSV (`trades_round_<R>_day_<D>.csv`)**:
   - Delimiter: `;` (semicolon)
   - Columns (7): `timestamp;buyer;seller;symbol;currency;price;quantity`
   - Observed nuances:
     - `price` is formatted as float (`9992.0`), `quantity` as integer.
     - `buyer` and `seller` are empty in Round 0 and Round 1.
     - Exact duplicate trade rows can occur (e.g., 2 duplicate rows observed in `trades_round_1_day_-2.csv`).
