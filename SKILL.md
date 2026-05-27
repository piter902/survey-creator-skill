---
name: survey-creator-skill
description: Bridge entry for the survey skill suite repository. The repository now centers on two canonical skills: `skills/survey-creator/` for survey generation and `skills/survey-analytics/` for survey result analysis. Use `specs/` for integration contracts that adopters implement in their own systems.
---

# Survey Skill Suite Bridge

This repository has evolved from a single-skill repository into a multi-skill survey suite.

Canonical skill locations:

- `skills/survey-creator/`
- `skills/survey-analytics/`

If you need survey generation, use:

```text
skills/survey-creator/SKILL.md
```

If you need survey result analysis, use:

```text
skills/survey-analytics/SKILL.md
```

This bridge exists for compatibility while the repository transitions to a `skills/`-based structure and keeps backend hosting/storage concerns outside the core open-source skills.
