"""Submission template and standalone packaging verification."""

from __future__ import annotations

import ast
from pathlib import Path

ALLOWED_SUBMISSION_MODULES: frozenset[str] = frozenset({
    "__future__",
    "bisect",
    "collections",
    "dataclasses",
    "datamodel",
    "enum",
    "functools",
    "heapq",
    "itertools",
    "json",
    "math",
    "operator",
    "statistics",
    "typing",
})


class SubmissionValidator:
    """Checks standalone submission script for competition compliance."""

    @staticmethod
    def validate_file(filepath: Path | str) -> list[str]:
        """Validate Trader class contract and strict stdlib + datamodel allowlist."""
        path = Path(filepath)
        if not path.is_file():
            return [f"File does not exist: {path}"]

        errors: list[str] = []
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError as err:
            return [f"Syntax error parsing submission file: {err}"]

        has_trader_class = False
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "Trader":
                has_trader_class = True
                methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                if "run" not in methods:
                    errors.append("Trader class is missing required 'run(self, state)' method")

            # Enforce strict allowlist of datamodel + pure Python standard library modules
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root_mod = alias.name.split(".", 1)[0]
                    if root_mod == "prosperity_toolkit":
                        errors.append(f"Forbidden internal import in submission file: {alias.name}")
                    elif root_mod not in ALLOWED_SUBMISSION_MODULES:
                        errors.append(
                            f"Disallowed external/unsafe import in submission file: {alias.name}",
                        )
            elif isinstance(node, ast.ImportFrom):
                if node.level > 0:
                    errors.append(
                        f"Disallowed relative import in submission file: {node.module or ''}",
                    )
                elif node.module:
                    root_mod = node.module.split(".", 1)[0]
                    if root_mod == "prosperity_toolkit":
                        errors.append(
                            f"Forbidden internal import in submission file: {node.module}",
                        )
                    elif root_mod not in ALLOWED_SUBMISSION_MODULES:
                        errors.append(
                            f"Disallowed external/unsafe import in submission file: {node.module}",
                        )

        if not has_trader_class:
            errors.append("Submission file does not define a 'Trader' class")

        return errors
