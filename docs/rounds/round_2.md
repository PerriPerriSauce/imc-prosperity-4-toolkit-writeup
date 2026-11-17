# Round 2: Inter-Exchange Arbitrage & Conversion Mechanics

## 1. Tradable Instruments
- Retains Round 1 assets (**ASH_COATED_OSMIUM**, **INTARIAN_PEPPER_ROOT**).
- Introduces foreign market conversion mechanics and MAF auction dynamics.

## 2. Microstructure & Conversion Rationale
- Environmental observations: transport fees $c_{\text{trans}}$, export tariffs $\tau_{\text{exp}}$, import tariffs $\tau_{\text{imp}}$.
- Spatial arbitrage condition:
  $$\Pi_{\text{arb}} = P_{\text{domestic}} - (P_{\text{foreign}} + c_{\text{trans}} + \tau_{\text{imp}})$$
  Conversion is optimal when $\Pi_{\text{arb}} > 0$ after accounting for order execution risk.
