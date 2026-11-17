"""Submission template and standalone packaging verification."""

from __future__ import annotations

import ast
from pathlib import Path


class SubmissionValidator:
    """Checks standalone submission script for competition compliance."""

    @staticmethod
    def validate_file(filepath: Path | str) -> list[str]:
        """Validate script contains required Trader class and no illegal internal imports."""
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

            # Check for illegal external/internal framework imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("prosperity_toolkit"):
                        errors.append(f"Forbidden internal import in submission file: {alias.name}")
            elif (
                isinstance(node, ast.ImportFrom)
                and node.module
                and node.module.startswith("prosperity_toolkit")
            ):
                errors.append(f"Forbidden internal import in submission file: {node.module}")

        if not has_trader_class:
            errors.append("Submission file does not define a 'Trader' class")

        return errors
