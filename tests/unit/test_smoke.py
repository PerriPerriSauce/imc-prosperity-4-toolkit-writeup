"""Repository smoke test verifying core imports and basic toolkit health."""

from __future__ import annotations

import prosperity_toolkit
from prosperity_toolkit.core.models import OrderRequest
from prosperity_toolkit.execution.simulator import ExecutionSimulator


def test_package_metadata() -> None:
    """Verify package version is defined."""
    assert prosperity_toolkit.__version__ == "0.1.0"


def test_order_request_validation() -> None:
    """Verify order request sign validation and immutability."""
    order = OrderRequest(symbol="TEST", price=100, quantity=5)
    assert order.symbol == "TEST"
    assert order.price == 100
    assert order.quantity == 5


def test_execution_simulator_init() -> None:
    """Verify simulator initialization."""
    sim = ExecutionSimulator(position_limits={"TEST": 20})
    assert sim.position_limits["TEST"] == 20
