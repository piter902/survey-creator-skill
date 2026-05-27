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
  SKILL.md                    # root bridge skill
  README.md                   # English usage guide
  README.zh-CN.md             # Chinese usage guide
  docs/                       # suite-level documentation
  services/                   # runtime services
  skills/
    survey-creator/
      SKILL.md
      docs/
      evals/
      examples/
      references/
      template-src/
      templates/
      tests/
      tools/
      validators/
    publisher/
      SKILL.md
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

From `skills/survey-creator/validators`:

```bash
npm install
npx playwright install
```

### Build the frozen single-file template

The repository keeps the editable template source in:

- `template-src/partials/`

And builds the release artifact here:

- `templates/base-survey-template.html`

Rebuild it from `skills/survey-creator/` with:

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

- Claude Code
- Codex
- OpenCode

### Codex

Recommended setup:

1. publish the repository to a public GitHub repo
2. install it with:

```bash
npx skills add piter902/survey-creator-skill -a codex
```

3. let Codex load `skills/survey-creator/SKILL.md` and retrieve from `skills/survey-creator/references/`

Discovery check:

```bash
npx skills add https://github.com/piter902/survey-creator-skill --list
```

Typical prompt:

> Use `survey-creator-skill` to generate a survey HTML page, validate the schema, render the HTML, and verify payload correctness before returning the result.

Best practice:
- describe the survey goal in plain language
- describe respondent type, delivery channel, UI style, and question families
- let the skill build an internal schema first, then validate before returning HTML

### Claude / Claude Code style usage

Recommended setup:

```bash
npx skills add piter902/survey-creator-skill -a claude-code
```

Then:

1. use `skills/survey-creator/SKILL.md` as the skill/system instruction body
2. use `skills/survey-creator/references/` as retrieval material
3. use `skills/survey-creator/templates/` and `skills/survey-creator/validators/` as implementation support

Recommended prompt pattern:

> Read `SKILL.md`, generate an internal survey schema from my request, validate legality, render HTML, and only return the result if the survey is safe to deliver.

### OpenCode

Recommended setup:

```bash
npx skills add piter902/survey-creator-skill -a opencode
```

Then:

1. point the agent to `skills/survey-creator/SKILL.md`
2. allow retrieval from `skills/survey-creator/references/`
3. tell the agent to follow the legality-first workflow instead of directly generating HTML from raw prompt text

Recommended usage:

> Use the local skill in `SKILL.md`. Build the survey from references, validate the schema and logic, then generate the final HTML only after checks pass.

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

- `skills/survey-creator/docs/PERFORMANCE_BENCHMARK.md`

Short conclusion:

- comfortable zone: ~100 questions / ~150 logic rules
- still usable: ~200 questions / ~300 logic rules
- optimization recommended: 300+ questions / 400+ logic rules

---

## More docs

- Logic condition and action guide: `skills/survey-creator/references/logic-condition-action-guide.md`
- toC survey UI spec: `skills/survey-creator/docs/TOC_SURVEY_UI_SPEC.md`
- legality guarantee: `skills/survey-creator/docs/LEGALITY_GUARANTEE.md`
- legality matrix: `skills/survey-creator/docs/LEGALITY_MATRIX.md`
- pre-release checklist: `skills/survey-creator/docs/PRE_RELEASE_CHECKLIST.md`
