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

    # Sell 5 units at 103 -> cash = -500 + 515 = +15, pos = 0, realized = 15, unrealized = 0
    portfolio.apply_fill(
        FillEvent(timestamp=100, symbol="OSMIUM", price=103, quantity=-5, fill_type=FillType.MAKER),
    )
    assert portfolio.cash == 15.0
    assert portfolio.get_position("OSMIUM") == 0
    assert portfolio.realized_pnl == 15.0
    assert portfolio.unrealized_pnl({"OSMIUM": 103.0}) == 0.0
    assert portfolio.total_valuation({"OSMIUM": 103.0}) == 15.0


def test_portfolio_flip_and_initial_cash_reconciliation() -> None:
    """Average-cost realized + unrealized PnL reconciles exactly across flips and fees."""
    portfolio = PortfolioTracker(initial_cash=1000.0)
    portfolio.apply_fill(
        FillEvent(timestamp=0, symbol="OSMIUM", price=100, quantity=5, fill_type=FillType.TAKER),
    )
    # Flip long +5 @ 100 to short -3 @ 104 with fee 1.0 -> closed 5 @ +4 = +20 - 1 = +19
    portfolio.apply_fill(
        FillEvent(
            timestamp=100,
            symbol="OSMIUM",
            price=104,
            quantity=-8,
            fill_type=FillType.MAKER,
            fee=1.0,
        ),
    )
    assert portfolio.get_position("OSMIUM") == -3
    assert portfolio.realized_pnl == 19.0
    marks = {"OSMIUM": 102.0}
    # Short -3 opened at 104 marked at 102 -> +6 unrealized
    assert portfolio.unrealized_pnl(marks) == 6.0
    assert portfolio.realized_pnl + portfolio.unrealized_pnl(marks) == (
        portfolio.total_valuation(marks) - 1000.0
    )
