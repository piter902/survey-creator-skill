# Survey reference field guide overview

This folder now contains two layers of references:

1. **Example JSON files**
   - These show the allowed structural shapes.
2. **Field guide markdown files**
   - These explain what each field means, when to use it, and common pitfalls.
3. **Executable validator**
   - `validators/validate_survey_schema.py` is the hard guardrail that rejects unsupported fields, duplicate ids, invalid child structures, and invalid datatype usage.

When using this skill:
- Read `schema-notes.md` first.
- Read `id-rules.md` early whenever you need to generate or review ids.
- Then read the relevant `*-fields.md` files for every node type you plan to generate.
- Use the JSON examples to confirm structure.
- Use the field guides to validate semantics and field intent.

## Reference pairs
- `survey-welcom.json` + `survey-fields.md`
- `question-radio.json` + `radio-fields.md`
- `question-checkbox.json` + `checkbox-fields.md`
- `question-input.json` + `input-fields.md`
- `question-score.json` + `score-fields.md`
- `question-nps.json` + `nps-fields.md`
- `question-finish.json` + `finish-fields.md`

## Why this matters
The JSON examples alone are not enough because some fields require interpretation:
- `survey.id` must use a global long snowflake format, while all other ids follow the canonical local type-prefixed 6-digit format
- whether `description` should be concise or instructional
- when `child` is appropriate
- when `exclusive` vs `mutual-exclusion` makes sense
- how `input.option[].attribute` should map to rendered HTML
- what parts are structural vs optional

Always treat the field guides as the semantic explanation layer.
Treat the validator as the machine-enforced structure layer.

- `logic-rules.md`
  - Explains the top-level logic array, supported operators, supported action types, and runtime visibility/navigation semantics.
