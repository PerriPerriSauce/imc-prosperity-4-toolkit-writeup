"""Unit tests for portfolio cash, inventory, and PnL accounting."""

from __future__ import annotations

from prosperity_toolkit.backtesting.portfolio import PortfolioTracker
from prosperity_toolkit.execution.fills import FillEvent, FillType


def test_portfolio_round_trip_pnl() -> None:
    """Verify cash and inventory conservation on a buy-then-sell round trip."""
    portfolio = PortfolioTracker(initial_cash=0.0)

    # Buy 5 units at 100 -> cash = -500, pos = +5
    portfolio.apply_fill(
        FillEvent(timestamp=0, symbol="OSMIUM", price=100, quantity=5, fill_type=FillType.TAKER),
    )
    assert portfolio.cash == -500.0
    assert portfolio.get_position("OSMIUM") == 5
    # Mark-to-market at 102 -> -500 + 5 * 102 = +10.0
    assert portfolio.total_valuation({"OSMIUM": 102.0}) == 10.0

    # Sell 5 units at 103 -> cash = -500 + 515 = +15, pos = 0
    portfolio.apply_fill(
        FillEvent(timestamp=100, symbol="OSMIUM", price=103, quantity=-5, fill_type=FillType.MAKER),
    )
    assert portfolio.cash == 15.0
    assert portfolio.get_position("OSMIUM") == 0
    assert portfolio.total_valuation({"OSMIUM": 103.0}) == 15.0
