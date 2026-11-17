
---
trigger: model_decision
description: Apply when implementing tests, changing existing code or reviewing correctness.
---

# Testing Rules

- Use pytest.
- Test edge cases, not just normal inputs.
- Test empty and malformed order books.
- Test position-limit enforcement.
- Test partial fills and inventory changes.
- Test deterministic replay.
- Test numerical calculations against independently calculated examples.
- Never weaken or delete a test merely to make a build pass.
- Run relevant tests after every significant change.
