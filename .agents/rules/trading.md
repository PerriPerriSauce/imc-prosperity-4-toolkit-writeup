
---
trigger: model_decision
description: Apply when implementing, reviewing or modifying Prosperity trading strategies.
---

# Trading Strategy Rules

- Verify the competition interface before coding.
- Keep the submission interface compatible with the actual datamodel.
- Separate research-only dependencies from competition dependencies.
- Respect all position and order limits.
- Handle empty books and missing observations.
- Never introduce look-ahead bias.
- Keep strategy parameters explicit and documented.
- Make each strategy independently testable.
- Do not claim a strategy was submitted unless evidence exists.
