# Survey Creator Legality Matrix

This matrix summarizes what `survey-creator-skill` currently guarantees at the legality layer.

| Layer | Guarantee | Enforced by |
|---|---|---|
| Reference consistency | References, schema validator, payload validator, field guides, and template mention the same supported types | `validate_reference_consistency.py` |
| Top-level schema | Must contain `survey`, `questions`, `finish` | `validate_survey_schema.py` |
| Question types | Only `radio`, `checkbox`, `input`, `score`, `nps` | `validate_survey_schema.py` |
| Field whitelist | Unsupported fields are blocking errors | `validate_survey_schema.py` |
| IDs | Duplicate ids are blocking errors | `validate_survey_schema.py` |
| Rich text | Rendered through sanitizer / whitelist path | template + runtime validator |
| Media | Only `image`, `audio`, `video` with non-empty URL | schema validator |
| Radio / checkbox | Option array required, child must be input-like; submitted options/children must exist; checkbox exclusive / mutual-exclusion cannot submit illegal combinations | schema + payload-against-schema validators |
| Input | `dataType` / range / option value shape enforced | schema + payload validators |
| Payload ↔ schema identity | surveyId / questionId / questionType / optionId / childId must match the concrete schema | `validate_payload_against_schema.py` |
| Score | `scope`, `step`, `scoreDesc`, payload array shape, submitted score within scope/step | schema + payload-against-schema validators |
| NPS | `scope`, range-based `scoreDesc`, payload object shape, submitted score within scope | schema + payload-against-schema validators |
| Runtime hooks | payload assembly / cache / child / exclusive / nps / score hooks present | runtime validator |
| Browser render | No blank page in real browser smoke check for desktop and mobile viewports | E2E validator |
| Browser interaction | Automated browser can fill every rendered question family and submit a payload in desktop and mobile viewports | interaction E2E validator |
| Accessibility | Document language/title, labeled controls/buttons, media semantics, score/NPS toggle state, and alert semantics are checked in desktop and mobile viewports | accessibility validator |
| Delivery gate | only `shipReady=true` is deliverable | pipeline |

## Current supported question families

- radio
- checkbox
- input
- score
- nps

## Current non-goals

The legality engine does **not** guarantee:
- best business questionnaire strategy
- best conversion rate
- perfect copy quality
- zero issues in every third-party WebView
- backend acceptance without server-side validation

## Standard maintenance flow

Whenever fields or types change, run:

```bash
<survey-creator-root>/run_all_legality_checks.sh
```
