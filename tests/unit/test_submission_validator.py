"""Unit tests for standalone competition submission AST validator."""

from __future__ import annotations

from pathlib import Path

from prosperity_toolkit.competition.submission import SubmissionValidator


def test_valid_submission_passes(tmp_path: Path) -> None:
    """Valid standalone Trader class passes validation."""
    sub_file = tmp_path / "valid_submission.py"
    sub_file.write_text(
        "class Trader:\n    def run(self, state):\n        return {}, 0, ''\n",
        encoding="utf-8",
    )
    assert SubmissionValidator.validate_file(sub_file) == []


def test_forbidden_internal_import_rejected(tmp_path: Path) -> None:
    """Importing prosperity_toolkit in a submission file must be flagged."""
    sub_file = tmp_path / "bad_import.py"
    sub_file.write_text(
        "from prosperity_toolkit.core.models import Symbol\n"
        "class Trader:\n"
        "    def run(self, state):\n"
        "        return {}, 0, ''\n",
        encoding="utf-8",
    )
    errors = SubmissionValidator.validate_file(sub_file)
    assert any("Forbidden internal import" in err for err in errors)


def test_missing_trader_class_rejected(tmp_path: Path) -> None:
    """Submission missing Trader class must be flagged."""
    sub_file = tmp_path / "no_trader.py"
    sub_file.write_text("def run(state):\n    return {}, 0, ''\n", encoding="utf-8")
    errors = SubmissionValidator.validate_file(sub_file)
    assert any("Trader" in err for err in errors)
