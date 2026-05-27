# Survey validators (Python)

These validators are the hard guardrails for the global `survey-creator-skill` generator.

In this document, `<survey-creator-root>` means:

`/path/to/survey-creator-skill/skills/survey-creator`

If you edited the split template source under `template-src/partials/`, rebuild the frozen single-file template before running release-grade checks:

```bash
python3 <survey-creator-root>/tools/build_template.py
```

## Files
- `<survey-creator-root>/tools/build_template.py`
- `<survey-creator-root>/validators/validate_survey_schema.py`
- `<survey-creator-root>/validators/auto_repair_survey_schema.py`
- `<survey-creator-root>/validators/validate_survey_payload.py`
- `<survey-creator-root>/validators/validate_payload_against_schema.py`
- `<survey-creator-root>/validators/validate_survey_html_runtime.py`
- `<survey-creator-root>/validators/validate_survey_html_e2e.py`
- `<survey-creator-root>/validators/auto_repair_survey_html.py`
- `<survey-creator-root>/validators/run_survey_creator_pipeline.py`
- `<survey-creator-root>/validators/run-validator-smoke-tests.sh`

## 1) Schema validator
Purpose:
- reject unsupported fields
- reject duplicate ids
- reject invalid child/input structures
- reject invalid datatype usage
- emit semantic lint warnings for suspicious but structurally valid survey designs
- classify warnings by severity: `high` / `medium` / `low`
- include machine-actionable metadata: `code`, `suggestion`, `fixHint`

Usage:
```bash
python3 <survey-creator-root>/validators/validate_survey_schema.py /absolute/path/to/schema.json
python3 <survey-creator-root>/validators/validate_survey_schema.py /absolute/path/to/schema.json --json
```

## 2) Payload validator
Purpose:
- enforce the default submission contract
- reject wrong `input.value` shape
- reject wrong range value shape
- reject duplicate `questionId` in answers

Usage:
```bash
python3 <survey-creator-root>/validators/validate_survey_payload.py /absolute/path/to/payload.json
python3 <survey-creator-root>/validators/validate_survey_payload.py /absolute/path/to/payload.json --json
```

## 2.5) Payload-against-schema validator
Purpose:
- bind submitted payloads to one concrete survey schema
- reject unknown questionId / optionId / childId
- reject questionType or dataType mismatch
- enforce required-question presence in submitted payloads
- enforce checkbox exclusive / mutual-exclusion legality in collected data
- enforce score / NPS scope and step constraints

Usage:
```bash
python3 <survey-creator-root>/validators/validate_payload_against_schema.py /absolute/path/to/schema.json /absolute/path/to/payload.json
python3 <survey-creator-root>/validators/validate_payload_against_schema.py /absolute/path/to/schema.json /absolute/path/to/payload.json --json
```

## 3) HTML runtime contract checker
Purpose:
- confirm generated HTML still contains the required runtime hooks
- check schema-driven rendering, payload assembly, cache, child visibility, exclusive / mutual-exclusion handling

Usage:
```bash
python3 <survey-creator-root>/validators/validate_survey_html_runtime.py /absolute/path/to/file.html
python3 <survey-creator-root>/validators/validate_survey_html_runtime.py /absolute/path/to/file.html --json
```

## 3.5) HTML E2E smoke checker
Purpose:
- catch blank-page failures in a real browser runtime
- detect page errors, empty form mounts, and zero-screen render failures
- serve as the final frontend delivery gate after HTML generation

Usage:
```bash
python3 <survey-creator-root>/validators/validate_survey_html_e2e.py /absolute/path/to/file.html
python3 <survey-creator-root>/validators/validate_survey_html_e2e.py /absolute/path/to/file.html --json
python3 <survey-creator-root>/validators/validate_survey_html_e2e.py /absolute/path/to/file.html --viewport mobile
```

By default this runs both `desktop` (1440×960) and `mobile` (390×844) viewports.

Current checks:
- page loads without `pageerror`
- `#surveyForm` exists
- `#surveyForm` has rendered children
- `.screen` count > 0
- active screen count > 0
- body text is non-empty

## 3.6) HTML interaction E2E checker
Purpose:
- open the generated HTML in a real browser
- automatically answer radio, checkbox, input, score, and nps screens
- click through to submit
- verify a console payload is produced
- verify rendered question types appear in submitted payload
- verify submit clears survey localStorage cache

Usage:
```bash
python3 <survey-creator-root>/validators/validate_survey_html_interaction_e2e.py /absolute/path/to/file.html
python3 <survey-creator-root>/validators/validate_survey_html_interaction_e2e.py /absolute/path/to/file.html --json
python3 <survey-creator-root>/validators/validate_survey_html_interaction_e2e.py /absolute/path/to/file.html --viewport mobile
```

By default this runs both `desktop` (1440×960) and `mobile` (390×844) viewports and requires both to be fillable and submittable.

## 3.7) HTML accessibility checker
Purpose:
- catch unlabeled controls and buttons before release
- verify document `lang` and title
- verify media has alt / controls
- verify score and NPS toggle buttons expose `aria-pressed`
- run the same checks in desktop and mobile viewports

Usage:
```bash
python3 <survey-creator-root>/validators/validate_survey_html_accessibility.py /absolute/path/to/file.html
python3 <survey-creator-root>/validators/validate_survey_html_accessibility.py /absolute/path/to/file.html --json
python3 <survey-creator-root>/validators/validate_survey_html_accessibility.py /absolute/path/to/file.html --viewport mobile
```

## 3.8) HTML auto repair
Purpose:
- recover from blank-page HTML failures before delivery
- fix known deterministic script issues
- if needed, extract `surveySchema` from the broken HTML and re-render using the latest template shell

Usage:
```bash
python3 <survey-creator-root>/validators/auto_repair_survey_html.py /absolute/path/to/file.html --out /absolute/path/to/repaired.html
python3 <survey-creator-root>/validators/auto_repair_survey_html.py /absolute/path/to/file.html --json
```

Current safe repair strategies:
- known broken inline regex replacement
- re-render from extracted schema using the current validated template
- preserve current style block and topbar shell when possible

## Smoke tests
```bash
<survey-creator-root>/validators/run-validator-smoke-tests.sh
```

## Semantic lint examples
The schema validator now also emits warnings for patterns such as:
- semantically empty rich-text titles
- multiple exclusive checkbox options
- exclusive options carrying child inputs
- multiple “other” style radio options
- finish descriptions that look like question instructions
- redundant option-level random overrides
- range fields using string-length constraints
- mismatched datatype / placeholder semantics
- invalid or inconsistent score question scopes / steps
- invalid NPS scope / scoreDesc ranges / option count

## Warning severity guidance
- `high`: likely to confuse respondents or damage data quality; should usually be fixed before delivery
- `medium`: structurally legal but product semantics are questionable; should be reviewed case by case
- `low`: minor redundancy or quality hint; safe to ship if intentional

## Warning payload shape
Example warning item:

```json
{
  "path": "questions[1].option",
  "message": "Multiple 'other' style radio options detected; usually only one is needed.",
  "severity": "medium",
  "code": "multiple-other-options",
  "suggestion": "Collapse duplicate 'Other' style options into one.",
  "fixHint": "Keep a single explanation-style fallback option and attach child inputs there if needed."
}
```

This shape is intended to support future auto-repair flows.

## 1.5) Auto repair pass
Purpose:
- apply conservative, schema-safe fixes for deterministic warning patterns
- reduce manual cleanup before HTML rendering
- stop before making aggressive product decisions

Usage:
```bash
python3 <survey-creator-root>/validators/auto_repair_survey_schema.py /absolute/path/to/schema.json --out /absolute/path/to/repaired-schema.json
python3 <survey-creator-root>/validators/auto_repair_survey_schema.py /absolute/path/to/schema.json --json
```

Typical auto-fixes:
- fill empty fallback titles
- rewrite finish copy that looks like question instructions
- remove redundant option-level random overrides
- remove child fields from exclusive checkbox options
- keep only one exclusive option
- remove invalid range `minLength` / `maxLength`
- normalize email / tel / date placeholders

## 1.6) Unified pipeline entry
Purpose:
- run the full delivery chain from one command
- emit repaired schema, html, payload sample, and a pipeline report together
- provide one stable entrypoint for the skill

Usage:
```bash
python3 <survey-creator-root>/validators/run_survey_creator_pipeline.py \
  --schema /absolute/path/to/schema.json \
  --output-dir /absolute/path/to/output-dir \
  --auto-repair \
  --fail-on-high-warning
```

Outputs:
- `*.repaired.schema.json`
- `*.html`
- `*.payload.json`
- `*.pipeline-report.json`

The pipeline validates the generated sample payload twice:
1. generic submission contract via `validate_survey_payload.py`
2. concrete schema identity/value constraints via `validate_payload_against_schema.py`

The pipeline report now includes:
- `releaseDecision.shipReady`
- `releaseDecision.blockedReasons`
- `releaseDecision.manualReviewRequired`
- desktop/mobile viewport reports under `htmlE2E.viewports` and `htmlInteractionE2E.viewports`
- accessibility report under `htmlAccessibility`, including desktop/mobile viewport subreports
- `htmlRepair`
- `htmlSyntax`

Interpretation:
- `shipReady=true` means no blocking schema/html/payload issue remains
- `manualReviewRequired` means the artifact is technically buildable, but still has warnings worth checking before release

## Important limitation
These validators greatly reduce hallucination and protocol drift risk, but they do not replace:
- real browser E2E testing
- visual regression testing
- server-side payload validation


---

# Unified release checker

## File

`<survey-creator-root>/validators/validate_survey_release.py`

## Purpose
One command to run schema validation, HTML runtime validation, and payload validation together.

## Usage

```bash
python3 <survey-creator-root>/validators/validate_survey_release.py   --schema /absolute/path/to/schema.json   --html /absolute/path/to/file.html   --payload /absolute/path/to/payload.json
```

JSON report:

```bash
python3 <survey-creator-root>/validators/validate_survey_release.py   --schema /absolute/path/to/schema.json   --html /absolute/path/to/file.html   --payload /absolute/path/to/payload.json   --json
```

Any subset also works, for example:

```bash
python3 <survey-creator-root>/validators/validate_survey_release.py --html /absolute/path/to/file.html
```

You can also let the release checker generate a payload sample from schema:

```bash
python3 <survey-creator-root>/validators/validate_survey_release.py \
  --schema /absolute/path/to/schema.json \
  --html /absolute/path/to/file.html \
  --generate-sample-payload \
  --write-sample-payload /absolute/path/to/generated-payload.json
```


---

# Sample payload generator

## File

`<survey-creator-root>/validators/generate_sample_payload.py`

## Purpose
Generate a valid payload sample directly from a frozen schema, so you do not need to hand-write a payload JSON before running release checks.

## Usage

```bash
python3 <survey-creator-root>/validators/generate_sample_payload.py /absolute/path/to/schema.json
```

Write to file:

```bash
python3 <survey-creator-root>/validators/generate_sample_payload.py /absolute/path/to/schema.json --out /absolute/path/to/payload.json
```


---

# Automated build pipeline

## File

`<survey-creator-root>/validators/build_validated_survey.py`

## Purpose
Run the full automatic pipeline from frozen schema to final HTML and generated payload sample, without requiring a person to manually step through each validator.

Pipeline:
1. validate schema
2. render HTML from schema
3. validate HTML runtime contract
4. generate payload sample from schema
5. validate payload contract

Practical rule:
- do not return final HTML when schema validation has errors
- review `high` warnings before considering the build ready

## Usage

```bash
python3 <survey-creator-root>/validators/build_validated_survey.py   --schema /absolute/path/to/schema.json   --out-html /absolute/path/to/output.html   --out-payload /absolute/path/to/output-payload.json
```

With repair and strict warning gate:

```bash
python3 <survey-creator-root>/validators/build_validated_survey.py \
  --schema /absolute/path/to/schema.json \
  --out-schema /absolute/path/to/repaired-schema.json \
  --out-html /absolute/path/to/output.html \
  --out-payload /absolute/path/to/output-payload.json \
  --auto-repair \
  --fail-on-high-warning
```

JSON report:

```bash
python3 <survey-creator-root>/validators/build_validated_survey.py   --schema /absolute/path/to/schema.json   --out-html /absolute/path/to/output.html   --out-payload /absolute/path/to/output-payload.json   --json
```


## One-command legality check

```bash
<survey-creator-root>/run_all_legality_checks.sh
```

## Reference consistency checker

File:

`<survey-creator-root>/validators/validate_reference_consistency.py`

Purpose:
- verify reference JSON question types match schema validator supported types
- verify payload validator supports the same question types
- verify every supported type has a `*-fields.md` guide
- verify advanced type docs / validators / template hooks stay aligned

Usage:

```bash
python3 <survey-creator-root>/validators/validate_reference_consistency.py
python3 <survey-creator-root>/validators/validate_reference_consistency.py --json
```
