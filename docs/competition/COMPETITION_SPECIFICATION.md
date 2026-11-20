# IMC Prosperity 4 — Competition Specification

**Verification Policy**: Details verified across multiple public Prosperity 4 sources—the raw historical CSV archives (`data/raw/prosperity4/round0`–`round5`), [`traders/datamodel.py`](../../traders/datamodel.py), the MIT-licensed `kevin-fu1/imc-prosperity-4-backtester` (`prosperity4bt/constants.py`), and `ADnocap/IMC_Prosperity4`—are marked with their exact provenance. Exchange container internals not exposed in public documentation or local execution logs are flagged as undisclosed container bounds.

---

## 1. Competition Timeline & Round Structure

| Round | Phase & Dates (2026) | Historical CSV Days | Product Transition | Special Mechanics |
| :--- | :--- | :--- | :--- | :--- |
| **Round 0** | Tutorial (Mar 16 – Apr 13) | `Day -2, -1` | `EMERALDS`, `TOMATOES` | Onboarding & stationary/RW baseline |
| **Round 1** | Phase 1 (Apr 14 – Apr 17) | `Day -2, -1, 0` | Reset $\to$ `ASH_COATED_OSMIUM`, `INTARIAN_PEPPER_ROOT` | Quote-jitter bot walls; manual "An Intarian Welcome" |
| **Round 2** | Phase 1 (Apr 17 – Apr 20) | `Day -1, 0, 1` | Retains Round 1 products | **Market Access Fee (MAF)** top-50% auction unlocks `+25%` book flow; manual "Invest & Expand" |
| **Round 3** | Phase 2 (Apr 24 – Apr 26) | `Day 0, 1, 2` | Slate Reset $\to$ `HYDROGEL_PACK`, `VELVETFRUIT_EXTRACT`, `VEV_4000..6500` | Leaderboard reset; 10 European call vouchers (`VEV_*`); manual "Celestial Gardeners' Guild" |
| **Round 4** | Phase 2 (Apr 26 – Apr 28) | `Day 1, 2, 3` | Continues all 12 Round 3 products | `buyer`/`seller` counterparty IDs populated (`Mark 01..67`); manual Aether Crystal exotic options |
| **Round 5** | Finals ("The Final Stretch", Apr 28 – Apr 30) | `Day 2, 3, 4` | Full Slate Reset $\to$ `50` new assets (`10` categories $\times$ `5`) | Uniform `±10` limit; joint category pulse clusters & discrete `MICROCHIP_CIRCLE` lag; manual "Extra! Extra!" |

- **Tick Granularity**: Verified in all `17` historical `prices` CSVs across Rounds 0–5 (`timestamp` advances uniformly in steps of `100` from `0` to `999,900` = `10,000` ticks/day).
- **Base Currency**: Verified across all `17` historical `trades` CSVs (`currency = XIRECS`).

---

## 2. Products, Instruments, and Position Limits by Round

Position limits below are **verified across raw logs and independent Prosperity 4 backtester constants** (`kevin-fu1/imc-prosperity-4-backtester` [MIT], `ADnocap/IMC_Prosperity4`), enforced identically across evaluation scripts and submissions via [`specifications.py`](../../src/prosperity_toolkit/competition/specifications.py):

### Rounds 0–2 (`80`-Unit Official Cap)
| Round | Product Symbol | Position Limit | Asset Class / Behavior | Provenance |
| :--- | :--- | :---: | :--- | :--- |
| **R0** | `EMERALDS` | `±80` | Constant fair value (`10,000`) | Tutorial CSV + `prosperity4bt` |
| **R0** | `TOMATOES` | `±80` | Non-stationary random walk | Tutorial CSV + `prosperity4bt` |
| **R1–R2** | `ASH_COATED_OSMIUM` | `±80` | Stationary OU ($\mu \approx 10{,}000$, empty/one-sided ticks) | R1–R2 CSVs + `prosperity4bt` + `ADnocap` |
| **R1–R2** | `INTARIAN_PEPPER_ROOT` | `±80` | Deterministic upward drift (`+0.10000`/tick) | R1–R2 CSVs + `prosperity4bt` + `ADnocap` |

### Rounds 3–4 (`200` / `300`-Unit Options & Spot Universe)
| Round | Product Symbol(s) | Position Limit | Instrument Role & Settlement | Provenance |
| :--- | :--- | :---: | :--- | :--- |
| **R3–R4** | `HYDROGEL_PACK` | `±200` | Standalone spot (~`9,991` mean, wide `~16`-tick spread) | R3–R4 CSVs + `prosperity4bt` + `ADnocap` |
| **R3–R4** | `VELVETFRUIT_EXTRACT` | `±200` | Underlying spot for `VEV_*` calls (~`5,250` mean, stationary; Round 4 exposes causal `Mark 14`/`Mark 55` vs. `Mark 67` 1-tick bounce) | R3–R4 CSVs + `prosperity4bt` + `ADnocap` |
| **R3–R4** | `VEV_4000`, `VEV_4500`, `VEV_5000`, `VEV_5100`, `VEV_5200`, `VEV_5300`, `VEV_5400`, `VEV_5500`, `VEV_6000`, `VEV_6500` | `±300` *(each strike)* | European call vouchers on `VELVETFRUIT_EXTRACT`; deep-OTM `6000/6500` trade as `0/1` noise | R3–R4 CSVs + `prosperity4bt` + `ADnocap` |

### Round 5 (`50` Products in `10` Categories, Uniform `±10` Cap)
All `50` symbols verified directly in `prices_round_5_day_{2,3,4}.csv`, with uniform `±10` limit per symbol:
- **Galaxy Sounds**: `GALAXY_SOUNDS_DARK_MATTER`, `GALAXY_SOUNDS_BLACK_HOLES`, `GALAXY_SOUNDS_PLANETARY_RINGS`, `GALAXY_SOUNDS_SOLAR_WINDS`, `GALAXY_SOUNDS_SOLAR_FLAMES`
- **Sleep Pods**: `SLEEP_POD_SUEDE`, `SLEEP_POD_LAMB_WOOL`, `SLEEP_POD_POLYESTER`, `SLEEP_POD_NYLON`, `SLEEP_POD_COTTON`
- **Microchips**: `MICROCHIP_CIRCLE` (leader), `MICROCHIP_OVAL` (lag 50), `MICROCHIP_SQUARE` (lag 100), `MICROCHIP_RECTANGLE` (lag 150), `MICROCHIP_TRIANGLE` (lag 200)
- **Pebbles** *(constant sum `= 50,000 ± 2.82`, sits inside 12–14 tick touch spread)*: `PEBBLES_XS`, `PEBBLES_S`, `PEBBLES_M`, `PEBBLES_L`, `PEBBLES_XL`
- **Robots**: `ROBOT_VACUUMING`, `ROBOT_MOPPING`, `ROBOT_DISHES`, `ROBOT_LAUNDRY`, `ROBOT_IRONING`
- **UV-Visors**: `UV_VISOR_YELLOW`, `UV_VISOR_AMBER`, `UV_VISOR_ORANGE`, `UV_VISOR_RED`, `UV_VISOR_MAGENTA`
- **Translators**: `TRANSLATOR_SPACE_GRAY`, `TRANSLATOR_ASTRO_BLACK`, `TRANSLATOR_ECLIPSE_CHARCOAL`, `TRANSLATOR_GRAPHITE_MIST`, `TRANSLATOR_VOID_BLUE`
- **Panels**: `PANEL_1X2`, `PANEL_2X2`, `PANEL_1X4`, `PANEL_2X4`, `PANEL_4X4`
- **Oxygen Shakes**: `OXYGEN_SHAKE_MORNING_BREATH`, `OXYGEN_SHAKE_EVENING_BREATH`, `OXYGEN_SHAKE_MINT`, `OXYGEN_SHAKE_CHOCOLATE`, `OXYGEN_SHAKE_GARLIC`
- **Snackpacks**: `SNACKPACK_CHOCOLATE`, `SNACKPACK_VANILLA`, `SNACKPACK_PISTACHIO`, `SNACKPACK_STRAWBERRY`, `SNACKPACK_RASPBERRY`

---

## 3. Authoritative Data Model & Matching Semantics

Verified directly against [`traders/datamodel.py`](../../traders/datamodel.py):
- **Type Aliases**: `Time = int`, `Symbol = str`, `Product = str`, `Position = int`, `UserId = str`, `ObservationValue = int`.
- **`Order(symbol, price, quantity)`**: Integer limit orders (`quantity > 0` buy, `< 0` sell). Unfilled orders expire at tick end.
- **`OrderDepth()`**: `buy_orders: Dict[int, int]` (positive quantities) and `sell_orders: Dict[int, int]` (negative quantities).
- **`Trade(symbol, price, quantity, buyer, seller, timestamp)`**: Public/own trade prints (`Mark 01..67` populated solely in Round 4).
- **`TradingState` & `Trader.run(self, state: TradingState) -> tuple[dict[Symbol, list[Order]], int, str]`**: Returns `(orders_by_symbol, conversions, traderData)`.
- **Position Limit Check Rule**: Worst-case buy or sell sum across submitted orders for a symbol is evaluated against starting position $q_{\text{start}}$; exceeding `±L` cancels that symbol's entire order batch for the tick.

---

## 4. Submission Runtime Restrictions & Container Notes

| Restriction | Verification Status | Details / Scope |
| :--- | :--- | :--- |
| **Single-File Upload (`class Trader`)** | **Verified** | Standalone `.py` file depending only on `datamodel.py` (`scripts/validate_submission.py`). |
| **Execution Environment Libraries** | **Strictly Sandboxed** | All five toolkit submissions restrict imports solely to `datamodel` and Python stdlib (`json`, `math`, `statistics`, `typing`). |
| **Per-Tick Latency & Lambda Memory Cap** | **Undisclosed Upstream** | Official AWS Lambda hard RAM/timeout limits are not exposed publicly; all toolkit submissions average `<= 0.552 ms/tick` (sub-1ms safe margin even across 50 R5 assets). |
| **`traderData` String Max Size** | **Compact JSON** | Official char limit is undisclosed publicly; our submissions serialize small fixed-size JSON payloads (`<= ~1–2 KB`). |

---

## 5. Historical CSV Formats & Schema Nuances

Verified across all **`34` raw CSV files** (`round0`–`round5`) via [`audit_all_datasets.py`](../../scripts/audit_all_datasets.py):
1. **Prices & Book CSVs (`prices_round_<R>_day_<D>.csv`)**: Exact `17`-column `;`-delimited schema across all rounds (`17` files, `20k`–`500k` rows/file). Round 3 `Day 1–2` and Round 4 `Day 1–2` price files are byte-identical rolling windows.
2. **Public Trades CSVs (`trades_round_<R>_day_<D>.csv`)**: Exact `7`-column `;`-delimited schema (`17` files); Round 1 `Day -2` has `2` duplicate prints, and Round 3–4 deep-OTM `VEV_6000`/`VEV_6500` emit `182–253` zero-price prints/day.
