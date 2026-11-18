# IMC Prosperity 4 — Competition Specification

**Verification Policy**: Details verified across multiple independent public Prosperity 4 sources—the raw historical CSV archives (`data/raw/prosperity4/round0`–`round5`), [`traders/datamodel.py`](../../traders/datamodel.py), the MIT-licensed `kevin-fu1/imc-prosperity-4-backtester` (`prosperity4bt/constants.py`), `ADnocap/IMC_Prosperity4`, and `PROSPERITY_4_WIKI_COMPLETE.md`—are marked with their exact provenance. Container internals not exposed in public documentation or local execution logs remain explicitly marked **UNVERIFIED** along with the evidence needed to confirm them.

---

## 1. Competition Timeline & Round Structure

| Round | Phase & Dates (2026) | Historical CSV Days | Product Transition | Special Mechanics |
| :--- | :--- | :--- | :--- | :--- |
| **Round 0** | Tutorial (Mar 16 – Apr 13) | `Day -2, -1` | `EMERALDS`, `TOMATOES` | Onboarding & stationary/RW baseline |
| **Round 1** | Qualifier (Apr 14 – Apr 17) | `Day -2, -1, 0` | Reset $\to$ `ASH_COATED_OSMIUM`, `INTARIAN_PEPPER_ROOT` | Quote-jitter bot walls; manual "An Intarian Welcome" |
| **Round 2** | Qualifier (Apr 17 – Apr 20) | `Day -1, 0, 1` | Retains Round 1 products | **Market Access Fee (MAF)** top-50% auction unlocks `+25%` book flow; manual "Invest & Expand" |
| **Round 3** | Phase 2 (Apr 24 – Apr 26) | `Day 0, 1, 2` | Slate Reset $\to$ `HYDROGEL_PACK`, `VELVETFRUIT_EXTRACT`, `VEV_4000..6500` | Leaderboard reset; 10 European call vouchers (`VEV_*`); manual "Celestial Gardeners' Guild" |
| **Round 4** | Phase 2 (Apr 26 – Apr 28) | `Day 1, 2, 3` | Continues all 12 Round 3 products | `buyer`/`seller` counterparty IDs populated (`Mark 01..67`); manual Aether Crystal exotic options |
| **Round 5** | Finals ("The Final Stretch", Apr 28 – Apr 30) | `Day 2, 3, 4` | Full Slate Reset $\to$ `50` new assets (`10` categories $\times$ `5`) | Uniform `±10` limit; joint Pebble/Snackpack constraints & 3 synchronized pulse processes; counterfactual IDs removed; manual "Extra! Extra!" |

- **Tick Granularity**: **Verified** in all `17` historical `prices` CSVs across Rounds 0–5 (`timestamp` advances uniformly in steps of `100` from `0` to `999,900` = `10,000` ticks/day; note participant docs report `1,000` ticks/day in live web UI test runs vs. `10,000` ticks/day in round-close evaluations).
- **Base Currency**: **Verified** across all `17` historical `trades` CSVs (`currency = XIRECS`).

---

## 2. Products, Instruments, and Position Limits by Round

Position limits below are **corroborated across multiple independent public Prosperity 4 backtesters and team archives** (`kevin-fu1/imc-prosperity-4-backtester` [MIT], `ADnocap/IMC_Prosperity4`, `PROSPERITY_4_WIKI_COMPLETE.md`), implemented cleanly in [`specifications.py`](../../src/prosperity_toolkit/competition/specifications.py). *(Note: Official IMC Notion wiki pages require interactive JS/login and could not be scraped directly; Round 1 research conservatively stressed $Q_{\max} = 20$ prior to unlocking full `±80` Round 1–2 scaling in Round 2.)*

### Rounds 0–2 (`80`-Unit Cap Tier)
| Round | Product Symbol | Position Limit | Asset Class / Behavior | Provenance |
| :--- | :--- | :--- | :--- | :--- |
| **R0** | `EMERALDS` | `80` | Constant fair value (`10,000`) | Tutorial CSV + Wiki + `prosperity4bt` |
| **R0** | `TOMATOES` | `80` | Non-stationary random walk | Tutorial CSV + Wiki + `prosperity4bt` |
| **R1–R2** | `ASH_COATED_OSMIUM` | `80` | Stationary OU ($\mu \approx 10{,}000$, empty/one-sided ticks) | R1–R2 CSVs + `prosperity4bt` + `ADnocap` |
| **R1–R2** | `INTARIAN_PEPPER_ROOT` | `80` | Deterministic upward drift ($\approx +0.10$/step) | R1–R2 CSVs + `prosperity4bt` + `ADnocap` |

### Rounds 3–4 (`200` / `300`-Unit Options & Spot Universe)
| Round | Product Symbol(s) | Position Limit | Instrument Role & Settlement | Provenance |
| :--- | :--- | :--- | :--- | :--- |
| **R3–R4** | `HYDROGEL_PACK` | `200` | Standalone spot (~`9,990` mean, wide `~15.7`-tick spread) | R3–R4 CSVs + `prosperity4bt` + `ADnocap` |
| **R3–R4** | `VELVETFRUIT_EXTRACT` | `200` | Underlying spot for `VEV_*` calls (~`5,250` mean, stationary) | R3–R4 CSVs + `prosperity4bt` + `ADnocap` |
| **R3–R4** | `VEV_4000`, `VEV_4500`, `VEV_5000`, `VEV_5100`, `VEV_5200`, `VEV_5300`, `VEV_5400`, `VEV_5500`, `VEV_6000`, `VEV_6500` | `300` *(each strike)* | European call vouchers on `VELVETFRUIT_EXTRACT` (`TTE = 5` days at R3 `Day 0`) | R3–R4 CSVs + `prosperity4bt` + `ADnocap` |

### Round 5 (`50` Products in `10` Categories, Uniform `10`-Unit Cap)
All `50` symbols validated directly in `prices_round_5_day_{2,3,4}.csv`, with `±10` limit per symbol:
- **Galaxy Sounds**: `GALAXY_SOUNDS_DARK_MATTER`, `GALAXY_SOUNDS_BLACK_HOLES`, `GALAXY_SOUNDS_PLANETARY_RINGS`, `GALAXY_SOUNDS_SOLAR_WINDS`, `GALAXY_SOUNDS_SOLAR_FLAMES`
- **Sleep Pods**: `SLEEP_POD_SUEDE`, `SLEEP_POD_LAMB_WOOL`, `SLEEP_POD_POLYESTER`, `SLEEP_POD_NYLON`, `SLEEP_POD_COTTON`
- **Microchips**: `MICROCHIP_CIRCLE`, `MICROCHIP_OVAL`, `MICROCHIP_SQUARE`, `MICROCHIP_RECTANGLE`, `MICROCHIP_TRIANGLE`
- **Pebbles** *(constant sum `= 50,000`)*: `PEBBLES_XS`, `PEBBLES_S`, `PEBBLES_M`, `PEBBLES_L`, `PEBBLES_XL`
- **Robots**: `ROBOT_VACUUMING`, `ROBOT_MOPPING`, `ROBOT_DISHES`, `ROBOT_LAUNDRY`, `ROBOT_IRONING`
- **UV-Visors**: `UV_VISOR_YELLOW`, `UV_VISOR_AMBER`, `UV_VISOR_ORANGE`, `UV_VISOR_RED`, `UV_VISOR_MAGENTA`
- **Translators**: `TRANSLATOR_SPACE_GRAY`, `TRANSLATOR_ASTRO_BLACK`, `TRANSLATOR_ECLIPSE_CHARCOAL`, `TRANSLATOR_GRAPHITE_MIST`, `TRANSLATOR_VOID_BLUE`
- **Panels**: `PANEL_1X2`, `PANEL_2X2`, `PANEL_1X4`, `PANEL_2X4`, `PANEL_4X4`
- **Oxygen Shakes**: `OXYGEN_SHAKE_MORNING_BREATH`, `OXYGEN_SHAKE_EVENING_BREATH`, `OXYGEN_SHAKE_MINT`, `OXYGEN_SHAKE_CHOCOLATE`, `OXYGEN_SHAKE_GARLIC`
- **Snackpacks** *(`CHOC + VAN = K_day` + triplet factor)*: `SNACKPACK_CHOCOLATE`, `SNACKPACK_VANILLA`, `SNACKPACK_PISTACHIO`, `SNACKPACK_STRAWBERRY`, `SNACKPACK_RASPBERRY`

---

## 3. Authoritative Data Model & Matching Semantics

Verified directly against [`traders/datamodel.py`](../../traders/datamodel.py) and identical upstream copies in `ADnocap/IMC_Prosperity4` and `kevin-fu1/imc-prosperity-4-backtester/prosperity4bt/datamodel.py`:

- **Type Aliases**: `Time = int`, `Symbol = str`, `Product = str`, `Position = int`, `UserId = str`, `ObservationValue = int`.
- **`Order(symbol: Symbol, price: int, quantity: int)`**: Integer limit orders (`quantity > 0` buy, `< 0` sell). All unfilled orders expire at the end of the tick (no GTC resting book for competitors).
- **`OrderDepth()`**: `buy_orders: Dict[int, int]` (positive quantities) and `sell_orders: Dict[int, int]` (negative quantities).
- **`Trade(symbol, price, quantity, buyer, seller, timestamp)`**: Public/own trade prints. Counterparty IDs (`Mark 01`, `Mark 14`, `Mark 22`, `Mark 38`, `Mark 49`, `Mark 55`, `Mark 67`) are populated **only in Round 4**.
- **`ConversionObservation(bidPrice, askPrice, transportFees, exportTariff, importTariff, sugarPrice, sunlightIndex)`** & **`Observation`**: Defined in `datamodel.py`, though **no Prosperity 4 round (`0`–`5`) emits `observations_round_*.csv` feeds** in the published historical datasets.
- **`TradingState` & `Trader.run(self, state: TradingState) -> tuple[dict[Symbol, list[Order]], int, str]`**: Returns `(orders_by_symbol, conversions, traderData)`.
- **Position Limit Check Rule**: **Verified** in `PROSPERITY_4_WIKI_COMPLETE.md` and `prosperity4bt/test_runner.py`. Worst-case fill across ALL submitted orders on a symbol is checked against the tick's **starting position** $q_{\text{start}}$:
  $$q_{\text{start}} + \sum_{Q_o > 0} Q_o > L \quad \text{or} \quad q_{\text{start}} + \sum_{Q_o < 0} Q_o < -L \implies \text{entire symbol batch canceled}$$

---

## 4. Submission Runtime Restrictions & Unverified Bounds

| Restriction | Verification Status | Details / Evidence Required |
| :--- | :--- | :--- |
| **Single-File Upload (`class Trader`)** | **Verified** | Standalone `.py` file depending only on `datamodel.py` (`scripts/validate_submission.py`). |
| **Execution Environment Libraries** | **Partially Verified** | `datamodel.py` imports `json`, `typing`, `jsonpickle`. Team logs confirm stdlib, `numpy`, `jsonpickle`, and `statistics`; exact pinned `scipy`/`pandas` availability remains **UNVERIFIED** without official container pip freeze. |
| **Per-Tick Latency & Lambda Memory Cap** | **UNVERIFIED** | Community logs cite `~100 MB` RAM and strict per-tick timeout (`~2–5 ms` safe budget for 50-asset R5); exact AWS Lambda hard cutoff values require official IMC container documentation. |
| **`traderData` String Max Size** | **UNVERIFIED** | Verified as arbitrary JSON string input/output; exact serialization character cap requires official runtime documentation. |

---

## 5. Historical CSV Formats & Schema Nuances

Verified across all **`34` raw CSV files** (`round0`–`round5`) via [`audit_all_datasets.py`](../../scripts/audit_all_datasets.py):
1. **Prices & Book CSVs (`prices_round_<R>_day_<D>.csv`)**: Exact `17`-column `;`-delimited schema across all rounds (`17` files, `20k`–`500k` rows/file).
   - CSV `ask_volume_{1,2,3}` are positive; `OrderDepth.sell_orders` expects negative values.
   - Round 1 & Round 2 `ASH_COATED_OSMIUM` and `INTARIAN_PEPPER_ROOT` exhibit `~7.5%` one-sided books and `28–38` empty books/day (`mid_price == 0.0`).
   - Round 3 & Round 4 deep-OTM vouchers (`VEV_6000`, `VEV_6500`) quote `bid_price_1 == 0`, `ask_price_1 == 1` (`mid_price == 0.5`).
2. **Public Trades CSVs (`trades_round_<R>_day_<D>.csv`)**: Exact `7`-column `;`-delimited schema across all rounds (`17` files).
   - Round 1 `trades_round_1_day_-2.csv` contains `2` exact duplicate rows (bot identical prints).
   - Round 3 & Round 4 contain `182–253` zero-price prints/day strictly on `VEV_6000` & `VEV_6500` where bots sell into `0`-price bids.
   - Counterparty IDs (`buyer`/`seller`) are populated strictly in Round 4; Round 0, 1, 2, 3, and 5 leave them null.
