# Technical details

This document contains the implementation-oriented details that are intentionally kept out of the README homepage.

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

## Resume and restart behavior

When a user refreshes or revisits the survey and local step cache from a previous page lifecycle exists, the generated HTML supports survey checkpoint resume:

- on a first-ever visit, no resume prompt is shown
- on refresh/revisit with saved progress, users see two choices:
  - **Restart from the beginning**
  - **Continue where I left off**
- continue resumes from the last active survey screen
- restart clears cached answers and returns to the start of the survey
- this behavior is built on top of the existing localStorage step cache

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

The repository keeps the editable template source in:

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

### Codex

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

### Claude / Claude Code style usage

If your workflow supports local prompt toolkits or markdown-based skills:

1. keep this repository as a standalone repo or local dependency
2. use `SKILL.md` as the skill/system instruction body
3. use `references/` as retrieval material
4. use `templates/` and `validators/` as implementation support

Recommended prompt pattern:

> Read `SKILL.md`, generate an internal survey schema from my request, validate legality, render HTML, and only return the result if the survey is safe to deliver.

### Trae

For Trae-style agent workflows, the recommended approach is:

1. keep this repo as a local knowledge/skill package
2. point the agent to `SKILL.md`
3. allow retrieval from `references/`
4. tell the agent to follow the legality-first workflow instead of directly generating HTML from raw prompt text

Recommended usage:

> Use the local skill in `SKILL.md`. Build the survey from references, validate the schema and logic, then generate the final HTML only after checks pass.

### Cursor

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

## More docs

- Logic condition and action guide: `references/logic-condition-action-guide.md`
- toC survey UI spec: `docs/TOC_SURVEY_UI_SPEC.md`
- legality guarantee: `docs/LEGALITY_GUARANTEE.md`
- legality matrix: `docs/LEGALITY_MATRIX.md`
- pre-release checklist: `docs/PRE_RELEASE_CHECKLIST.md`
