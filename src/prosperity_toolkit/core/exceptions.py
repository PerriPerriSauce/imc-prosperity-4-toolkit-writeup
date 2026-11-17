"""Core custom exceptions for the toolkit."""

from __future__ import annotations


class ProsperityToolkitError(Exception):
    """Base exception for all errors raised within prosperity_toolkit."""


class DataValidationError(ProsperityToolkitError):
    """Raised when market data fails structural or consistency validation."""


class OrderValidationError(ProsperityToolkitError):
    """Raised when an order request violates basic syntax, signs, or specifications."""


class PositionLimitExceededError(ProsperityToolkitError):
    """Raised when an order or trade violates competition position limits."""


class StateDesynchronizationError(ProsperityToolkitError):
    """Raised when internal simulation state diverges from external data feeds."""
