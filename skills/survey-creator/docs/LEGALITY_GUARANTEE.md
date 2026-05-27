# Survey Creator Legality Guarantee

`survey-creator-skill` is a schema legality engine plus fixed HTML renderer for survey pages.

Its goal is not to guarantee that a questionnaire is the best possible business questionnaire. Business intent, wording, conversion strategy, and product judgment should still be refined through user + AI iteration.

Its goal is to guarantee that any delivered artifact is technically legal, renderable, fillable, submittable, and payload-valid under the supported survey protocol.

## Responsibility boundary

### User + AI own business semantics
They decide and iterate:
- the survey goal
- question count and wording
- whether a question belongs in the flow
- which answers should be required
- which options should be mutually exclusive
- whether score / nps is appropriate
- whether the final questionnaire matches the target campaign

### `survey-creator-skill` owns legality
It must enforce:
- only supported top-level shape: `survey`, `questions`, `finish`
- only supported question types: `radio`, `checkbox`, `input`, `score`, `nps`
- no unsupported fields
- no duplicate ids
- valid rich-text-safe render path
- valid `attribute` objects per node type
- valid media objects: `image`, `audio`, `video` with non-empty URL/base64
- valid selection option structures
- valid child input structures
- valid input data types
- valid score scopes / steps / descriptions
- valid nps scopes / range descriptions
- valid fixed-template HTML runtime hooks
- valid baseline accessibility semantics for forms, controls, media, score/NPS toggles, and validation errors
- valid browser smoke render with no blank page in desktop and mobile viewports
- valid sample payload shape
- valid sample payload identity against the concrete schema: surveyId / questionId / optionId / childId / score values must belong to that exact schema

## Core guarantee

If the unified pipeline report says:

```json
{
  "releaseDecision": {
    "shipReady": true
  }
}
```

then the artifact has passed the current legality gates:

1. reference consistency validation
2. schema validation
3. optional safe schema auto-repair
4. fixed-template HTML render
5. HTML runtime contract validation
6. real-browser E2E smoke validation for desktop and mobile viewports
7. real-browser interaction E2E validation for desktop and mobile viewports
8. baseline accessibility validation for desktop and mobile viewports
9. sample payload generation
10. payload contract validation
11. payload-against-schema validation
12. release-decision gate

## What this does not guarantee

`shipReady=true` does not guarantee:
- the survey has ideal business strategy
- the copy is persuasive
- every target WebView is bug-free
- external media URLs will never fail
- backend storage accepts the payload without its own validation
- the visual design is perfect on every device

## Non-negotiable delivery rule

Do not deliver the final HTML if:
- schema validator fails
- high-severity warnings remain when `--fail-on-high-warning` is enabled
- HTML runtime validator fails
- browser E2E smoke fails in any required viewport
- browser interaction E2E fails in any required viewport
- accessibility validator fails in any required viewport
- payload validator fails
- payload-against-schema validator fails
- `releaseDecision.shipReady !== true`

## Fixed renderer rule

AI should generate schema content. Runtime behavior must come from the fixed template and validators.

Do not hand-write bespoke submit logic, random custom validation logic, or custom payload assembly for each survey unless the user explicitly asks for a new protocol extension and the validators are updated first.

## Extension rule

When adding a new question type or field:

1. add the JSON reference
2. add the field guide
3. update `schema-notes.md`
4. update `submission-contract.md` if payload changes
5. update `validate_survey_schema.py`
6. update `validate_survey_payload.py` if payload changes
7. update `generate_sample_payload.py`
8. update `validate_payload_against_schema.py` for id/value constraints
9. update the fixed template renderer
10. add contract tests
11. run smoke + contract tests

A new field is not supported until references, validator, renderer, and contract tests agree.
