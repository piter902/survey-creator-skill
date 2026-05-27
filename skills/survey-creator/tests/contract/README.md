# survey-creator-skill contract tests

These tests protect the legality boundary of `survey-creator-skill`.

They intentionally focus on protocol legality rather than business quality.

## What is covered

- supported question types: `radio`, `checkbox`, `input`, `score`, `nps`
- valid full schema with all current question families
- invalid unsupported fields
- invalid duplicate ids
- invalid input data types
- invalid score step
- invalid nps scoreDesc ranges
- valid and invalid payload shapes
- references ↔ validator supported-type consistency
- fixed renderer pipeline smoke for a full legal schema
- desktop and mobile viewport browser smoke checks
- desktop and mobile viewport interaction E2E checks
- accessibility checks for document language/title, labeled controls, button names, media alt/controls, score toggle state

## Run

```bash
python3 <survey-creator-root>/tests/contract/run_contract_tests.py
```

The test runner creates temporary output directories under `/tmp` and does not modify generated production surveys.

## Related consistency gate

The one-command legality check also runs:

```bash
python3 <survey-creator-root>/validators/validate_reference_consistency.py
```

This catches drift between references, validators, payload contract, and the fixed renderer before contract cases run.
