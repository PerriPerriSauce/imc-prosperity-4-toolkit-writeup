
# Project Instructions — IMC Prosperity 4

## 1. Project Objective

Build a high-quality quantitative trading research repository for IMC Prosperity 4, .

The repository should contain:
- Round-specific trading strategies and experiments.
- Historical competition data and data-processing tools.
- A reproducible backtesting framework.
- Quantitative research and analysis.
- Manual challenge research.
- Strategy optimisation and performance evaluation.
- Professional technical documentation and a final writeup.

## 2. Technical Stack

Primary language: Python 3.11.

Use:
- NumPy for numerical computation.
- Pandas for tabular data.
- SciPy when specialised numerical algorithms are required.
- Matplotlib for research visualisations.
- Pytest for testing.
- Ruff for formatting and linting.
- Jupyter for exploratory research.

Use uv for dependency and virtual-environment management.

Keep the initial architecture Python-first. Do not introduce Rust,
WebAssembly, React, databases or distributed infrastructure without
a demonstrated requirement and explicit approval.

## 3. Trading Strategy Requirements

Competition-facing trader implementations must respect the actual
Prosperity 4 submission interface and runtime restrictions.

Before implementing a strategy:
1. Inspect the relevant official or attributable datamodel.
2. Verify the Trader interface.
3. Verify available libraries and runtime constraints.
4. Verify product position limits.
5. Verify order and state semantics.

Do not invent APIs or assume that functionality available in the
local research environment is available in the competition runtime.

Strategies must:
- Handle missing and malformed observations defensively.
- Respect position limits.
- Avoid unintended state mutation.
- Handle empty order books.
- Have deterministic behaviour where randomness is not required.
- Be independently testable.

Keep competition-facing code separate from research infrastructure.

## 4. Quantitative Research Standards

Every research conclusion must be supported by reproducible analysis.

Distinguish between:
- Observed data.
- Estimated parameters.
- Model assumptions.
- Simulated results.
- Actual competition results.

Never present simulated performance as actual competition performance.

Avoid:
- Look-ahead bias.
- Survivorship bias.
- Data leakage.
- Overfitting.
- Unjustified parameter selection.
- Cherry-picked experiments.

Where appropriate, use out-of-sample validation, sensitivity analysis,
confidence intervals and baseline comparisons.

Always document assumptions and limitations.

## 5. Software Engineering Standards

Prefer:
- Small, modular functions.
- Clear interfaces.
- Type hints.
- Descriptive variable names.
- Explicit error handling.
- Reproducible configurations.
- Automated tests.

Avoid:
- Unnecessary abstraction.
- Monolithic scripts.
- Duplicated implementations.
- Hidden global state.
- Excessive dependencies.
- Premature optimisation.

Do not refactor unrelated files when implementing a narrowly scoped task.

Do not silently change public interfaces or existing data formats.

## 6. Testing and Verification

Before declaring a task complete:
1. Run relevant unit tests.
2. Run relevant integration tests.
3. Run Ruff.
4. Run type checking where configured.
5. Verify the documented execution commands.
6. Inspect the Git diff for unintended changes.

Never claim a test passed unless it was actually executed
and its result was observed.

If a test cannot run, explain why.

## 7. Data Integrity and Attribution

Never overwrite original source data.

Keep raw, processed and generated data separate.

For every external dataset, record:
- Source.
- Retrieval date.
- Original filename.
- Data format.
- Relevant licence or usage restrictions.
- SHA-256 checksum where practical.

## 8. Documentation

Document:
- Architecture.
- Research methodology.
- Strategy logic.
- Configuration.
- Experiment methodology.
- Performance metrics.
- Known limitations.

Use Markdown for technical documentation.

Research reports should explain why a result occurs,
not merely state what the result is.

## 9. Agent Behaviour

Before making substantial changes:
1. Inspect the existing repository.
2. Read relevant documentation.
3. Identify affected files.
4. Propose a concise implementation plan.
5. Identify assumptions and uncertainties.

For ambiguous or consequential design decisions, ask before proceeding.

Prefer incremental changes over large autonomous rewrites.

Never fabricate missing information to make implementation easier.

When finished, provide:
- Summary of changes.
- Files created or modified.
- Commands executed.
- Test results.
- Outstanding issues.
- Suggested next step.
