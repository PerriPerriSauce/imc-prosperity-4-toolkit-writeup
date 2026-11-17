# Workflow: Run Test Suite & Verification

1. **Format & Linting Check**:
   ```bash
   uv run ruff check .
   uv run ruff format --check .
   ```

2. **Static Type Checking**:
   ```bash
   uv run mypy .
   ```

3. **Unit & Integration Tests**:
   ```bash
   uv run pytest -ra --cov=prosperity_toolkit
   ```

4. **Submission Verification**:
   ```bash
   uv run python scripts/validate_submission.py traders/round1/submission.py
   ```
