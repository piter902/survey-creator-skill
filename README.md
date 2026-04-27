# survey-creator-skill

[English](./README.md) | [简体中文](./README.zh-CN.md)

**A production-oriented survey skill for Codex, Claude, Trae, Cursor, and other AI agent workflows.**

`survey-creator-skill` is an open-source **agent skill repository** for generating schema-constrained, legality-checked survey HTML.

Its primary purpose is not just to render pages, but to help AI agents:

- validates survey schema legality
- repairs safe schema issues
- renders submittable HTML survey pages
- verifies runtime behavior in browser E2E
- checks interaction flow
- validates accessibility
- validates payload contract
- guarantees submitted payloads match the exact survey schema

If you want AI to generate questionnaires **without silently producing invalid forms or broken submit payloads**, this project is built for that.

---

## Why this skill exists

Most AI agents or AI form generators stop at:

- generate some JSON
- render some HTML
- hope the submit data is usable

That is usually not enough for real delivery.

Survey and questionnaire systems have stricter needs:

- schema must be legal
- ids must be stable and unique
- logic must not break required validation
- hidden/skipped questions must not leak into payload
- runtime must not blank-screen
- rendered form should be browser-testable
- submit payload must match the concrete survey definition

`survey-creator-skill` is designed to give agents that full chain as a reusable skill package.

---

## What this skill repository includes

Think of this repo as a packaged survey capability that an agent can read, retrieve from, and execute against.

### Skill layer
- `SKILL.md`
- structured generation workflow
- schema-first output discipline
- legality-first delivery rule

### Reference layer
- schema notes
- field guides
- rich text rules
- pagination rules
- child input rules
- local cache rules
- logic rules
- logic final specification
- logic example library
- submission contract

### Runtime layer
- frozen HTML template
- client-side step flow
- logic runtime
- cache handling
- payload assembly

### Validation layer
- schema validation
- schema auto-repair
- HTML runtime validation
- HTML E2E validation
- HTML interaction E2E validation
- accessibility validation
- payload validation
- payload-against-schema validation

### Quality layer
- contract tests
- smoke tests
- full legality checks

---

## Supported question types

- `radio`
- `checkbox`
- `input`
- `score`
- `nps`
- `survey`
- `finish`
- `Pagination`

## Supported toC style packs

- `consumer-minimal`
- `consumer-polished`
- `consumer-trust`
- `consumer-editorial`
- `consumer-utility`
- `consumer-campaign`

---

## Supported logic operators

- `selected`
- `not_selected`
- `contains`
- `not_contains`
- `exists`
- `not_exists`
- `answered`
- `not_answered`
- `eq`
- `neq`
- `gt`
- `lt`

## Supported logic actions

- `show_question`
- `hide_question`
- `show_option`
- `hide_option`
- `auto_select_option`
- `jump_to_question`
- `jump_to_page`
- `end_survey`

---

## Logic guarantees

This project already enforces these runtime rules:

- **hidden = nonexistent**
- **skipped = nonexistent**
- hidden/skipped questions do not block required validation
- hidden/skipped questions do not enter payload
- hidden/skipped questions are removed from cache
- hidden options are cleared from state
- conflicting rules resolve by declaration order
- later matched logic overrides earlier matched logic
- auto-select only applies to final visible targets
- `end_survey` can target a specific `finish[].id`
- multiple finish nodes are supported for branch-specific endings
- each `finish[]` may optionally define `postSubmit.redirect`
- redirect actions only run **after** a successful submit, so survey payload collection is not skipped

---

## Best use cases

- AI-generated surveys
- registration questionnaires
- screening / qualification forms
- customer satisfaction research
- NPS / score workflows
- AI Native form creation flows
- teams that need stronger legality guardrails before shipping HTML questionnaires

---

## Skill repository structure

```text
survey-creator-skill/
  SKILL.md                    # main skill definition for agents
  README.md                   # English usage guide
  README.zh-CN.md             # Chinese usage guide
  docs/                       # human-facing documentation
  references/                 # model-facing schema / logic constraints
  templates/                  # HTML template assets
  validators/                 # validation and rendering support
  examples/                   # bundled schema + HTML examples
  tests/                      # contract tests
  evals/                      # evaluation inputs
  LICENSE
```

---

## Runtime dependencies

This skill is portable, but it is **not dependency-free**.

To run the full legality / rendering / browser-validation pipeline, the target machine should have:

- Python **3.10+**
- Node.js **18+**
- npm

### Why both Python and Node are needed

- `validators/*.py` handles schema validation, rendering, payload validation, and pipeline orchestration
- `validators/package.json` provides the browser automation dependency used by Playwright-based checks

### One-time setup

From the repository root:

```bash
cd validators
npm install
npx playwright install
```

### Build the frozen single-file template

The repository now keeps the editable template source in:

- `template-src/partials/`

And builds the release artifact here:

- `templates/base-survey-template.html`

Rebuild it with:

```bash
python3 tools/build_template.py
```

### Recommended environment notes

- macOS / Linux is the recommended environment
- Windows users should prefer **WSL**
- if Playwright browsers are missing, HTML E2E / interaction checks will fail even though schema validation may still work

### Minimal dependency expectation for downstream users

If someone only wants the skill instructions and reference files for agent retrieval, they can read:

- `SKILL.md`
- `references/`
- `templates/`

But if they want the skill to actually perform validation and release-grade checks, they should install the dependencies above first.

---

## Use with AI coding/design agents

This repository is primarily meant to be used as a **skill** inside agent products, not as a standalone script-first toolkit.

Recommended environments:

- Codex
- Claude / Claude Code style local skills
- Trae
- Cursor

---

## Codex

Recommended setup:

1. place the repository in a local skills directory
   - `~/.codex/skills/survey-creator-skill`
   - or `~/.agents/skills/survey-creator-skill`
2. keep the repository structure unchanged
3. let Codex load `SKILL.md` and retrieve from `references/`

Typical prompt:

> Use `survey-creator-skill` to generate a survey HTML page, validate the schema, render the HTML, and verify payload correctness before returning the result.

Best practice:
- describe the survey goal in plain language
- describe respondent type, delivery channel, UI style, and question families
- let the skill build an internal schema first, then validate before returning HTML

---

## Claude / Claude Code style usage

If your workflow supports local prompt toolkits or markdown-based skills:

1. keep this repository as a standalone repo or local dependency
2. use `SKILL.md` as the skill/system instruction body
3. use `references/` as retrieval material
4. use `templates/` and `validators/` as implementation support

Recommended prompt pattern:

> Read `SKILL.md`, generate an internal survey schema from my request, validate legality, render HTML, and only return the result if the survey is safe to deliver.

---

## Trae

For Trae-style agent workflows, the recommended approach is:

1. keep this repo as a local knowledge/skill package
2. point the agent to `SKILL.md`
3. allow retrieval from `references/`
4. tell the agent to follow the legality-first workflow instead of directly generating HTML from raw prompt text

Recommended usage:

> Use the local skill in `SKILL.md`. Build the survey from references, validate the schema and logic, then generate the final HTML only after checks pass.

---

## Cursor

Cursor does not use a universal built-in skill standard in the same way as Codex, but this repository still works well as an agent companion package.

Recommended usage:

1. open the repository alongside your working project
2. reference `SKILL.md` in your chat context
3. tell Cursor to treat `references/` as the source of truth for schema and logic constraints
4. ask Cursor to generate survey HTML through the skill workflow, not directly from UI description alone

Recommended prompt:

> Follow `SKILL.md` in this repository. Use the reference files to construct a legal survey schema, validate logic and payload constraints, then output the final HTML.

---

## Example prompts

### Product feedback survey
> Use `survey-creator-skill` to create a mobile-friendly product feedback survey for AI design tool users. Include welcome, radio, checkbox, input, score, nps, and finish. Keep the UI lightweight and validate everything before returning HTML.

### Registration questionnaire
> Use `survey-creator-skill` to create a registration survey for kindergarten enrollment. The result should be a submittable HTML page, with schema legality and payload correctness checked before return.

### Logic-heavy research flow
> Use `survey-creator-skill` to build a survey with conditional follow-up questions, manual pagination, and jump-to-page behavior. Make sure hidden/skipped questions do not enter payload.

---

## Example files

The repository currently includes these example inputs in `examples/`:

- `minimal-survey.json` — the smallest valid survey example
- `ai-design-tool-demand-demo.json` — a richer demo covering logic, Pagination, multi-question pages, child input, score, and nps
- `service-satisfaction-multi-finish.json` — a more production-like satisfaction flow with branch-specific ending pages
- `service-satisfaction-three-finish.json` — a three-ending example for positive / neutral / negative user branches
- `service-satisfaction-post-submit-redirect.json` — a real-world service callback demo with branch-specific finish pages and different post-submit redirects

Generated HTML examples are also checked in for direct inspection and browser testing, including:

- `examples/ai-design-tool-demand-demo.html`
- `examples/service-satisfaction-multi-finish.html`
- `examples/service-satisfaction-three-finish.html`
- `examples/service-satisfaction-post-submit-redirect.html`

---

## What users should provide in prompts

To get the best result, users should describe:

- survey goal
- respondent type
- delivery channel
- UI style
- expected question types
- whether logic / pagination / jump behavior is needed
- whether one-page-one-question is needed

The skill is strongest when the prompt defines intent clearly and the repo enforces legality.

---

## Performance benchmark

A benchmark summary for the current generated HTML runtime is archived at:

- `docs/PERFORMANCE_BENCHMARK.md`

Short conclusion:

- comfortable zone: ~100 questions / ~150 logic rules
- still usable: ~200 questions / ~300 logic rules
- optimization recommended: 300+ questions / 400+ logic rules

---

## Run all checks

```bash
./run_all_legality_checks.sh
```

This runs:

- reference consistency check
- contract tests
- validator smoke tests

Only treat the repo as healthy when this command passes.

---

## Standalone usage

### Validate schema

```bash
python3 validators/validate_survey_schema.py /absolute/path/to/schema.json
python3 validators/validate_survey_schema.py /absolute/path/to/schema.json --json
```

### Render HTML

```bash
python3 validators/render_survey_html.py \
  --schema /absolute/path/to/schema.json \
  --out /absolute/path/to/output.html
```

### Full pipeline

```bash
python3 validators/run_survey_creator_pipeline.py \
  --schema /absolute/path/to/schema.json \
  --output-dir /absolute/path/to/output-dir \
  --auto-repair \
  --fail-on-high-warning
```

### Validate payload

```bash
python3 validators/validate_survey_payload.py /absolute/path/to/payload.json
python3 validators/validate_payload_against_schema.py \
  /absolute/path/to/schema.json \
  /absolute/path/to/payload.json
```

### Validate rendered HTML

```bash
python3 validators/validate_survey_html_runtime.py /absolute/path/to/file.html
python3 validators/validate_survey_html_e2e.py /absolute/path/to/file.html
python3 validators/validate_survey_html_interaction_e2e.py /absolute/path/to/file.html
python3 validators/validate_survey_html_accessibility.py /absolute/path/to/file.html
```

---

## Use as a Codex skill

Copy or symlink this repository into your local skills directory:

- `~/.codex/skills/survey-creator-skill`
- `~/.agents/skills/survey-creator-skill`

Then invoke it by name in your prompt.

Example:

> Use `survey-creator-skill` to generate a survey HTML page, validate the schema, render the HTML, and verify payload correctness before returning the result.

### Use with Claude-style local workflows

You can also use this repository as a standalone skill/toolchain in Claude-style or custom agent systems:

- keep `SKILL.md` as the main skill prompt
- keep `references/` as retrieval material
- use `validators/run_survey_creator_pipeline.py` as the main executable entrypoint
- only treat output as deliverable when the pipeline returns `shipReady = true`


---

## Documentation map

### Logic guide
- `references/logic-condition-action-guide.md`
- `docs/TOC_SURVEY_UI_SPEC.md`

### Core references
- `references/schema-notes.md`
- `references/field-guide-overview.md`
- `references/submission-contract.md`
- `references/logic-rules.md`
- `references/logic-specification.md`
- `references/logic-example-library.md`

### Validators
- `validators/README.md`
- `docs/PRE_RELEASE_CHECKLIST.md`

### Tests
- `tests/contract/README.md`

---

## Open-source readiness

This repository is designed to be portable:

- repository-relative path resolution
- generated outputs ignored by `.gitignore`
- no fixed local machine path requirement
- contract-tested logic semantics
- browser-validated runtime behavior

---

## Recommended positioning

This project is best described as:

> A schema-safe survey generator and legality pipeline for AI-driven questionnaire creation.

That is more accurate than calling it only an “HTML form generator”, because the main value is not just rendering — it is **legality, logic safety, payload correctness, and pre-release validation**.

---

## License

MIT
