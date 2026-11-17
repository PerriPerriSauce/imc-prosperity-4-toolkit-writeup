"""Validate standalone competition submission script before submission."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from prosperity_toolkit.competition.submission import SubmissionValidator


def main() -> int:
    """CLI to validate submission."""
    parser = argparse.ArgumentParser(description="Validate competition submission script.")
    parser.add_argument("filepath", type=Path, help="Path to submission.py script")
    args = parser.parse_args()

    errors = SubmissionValidator.validate_file(args.filepath)
    if errors:
        print("Submission validation FAILED with errors:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    print(f"SUCCESS: Submission file {args.filepath} passed all syntax and boundary checks.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
