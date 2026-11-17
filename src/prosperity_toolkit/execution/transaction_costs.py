"""Transaction cost and conversion fee calculations."""

from __future__ import annotations


class TransactionCostModel:
    """Computes exchange fees, transport fees, and import/export tariffs."""

    @staticmethod
    def calculate_conversion_cost(
        quantity: int,
        transport_fee: float = 0.0,
        tariff: float = 0.0,
    ) -> float:
        """Calculate total friction fees for product conversion."""
        return abs(quantity) * (transport_fee + tariff)
