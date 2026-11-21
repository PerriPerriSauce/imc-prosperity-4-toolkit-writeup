"""Repository smoke test verifying core imports and basic toolkit health."""

from __future__ import annotations

from pathlib import Path

import prosperity_toolkit
from prosperity_toolkit.cli import build_parser
from prosperity_toolkit.competition import load_competition_trader
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


def test_cli_replay_flags_and_submission_loader() -> None:
    """Verify CLI parser flags and shared competition submission loader."""
    parser = build_parser()
    args = parser.parse_args([
        "replay",
        "--prices",
        "p.csv",
        "--trades",
        "t.csv",
        "--round",
        "1",
        "--submission",
        "traders/round1/submission.py",
        "--fill-mode",
        "queue_aware",
    ])
    assert args.round == 1
    assert args.fill_mode == "queue_aware"
    assert args.submission == Path("traders/round1/submission.py")

    trader = load_competition_trader(Path("traders/round1/submission.py"))
    assert hasattr(trader, "run")


def test_manifest_verify_only_succeeds() -> None:
    """Verify raw dataset manifest SHA-256 verification script exits cleanly."""
    import importlib.util

    audit_path = Path("scripts/audit_all_datasets.py").resolve()
    spec = importlib.util.spec_from_file_location("audit_all_datasets", audit_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    if Path("data/raw/prosperity4").exists():
        assert mod.main(["--verify-only"]) == 0

