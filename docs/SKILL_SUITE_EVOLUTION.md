# Skill Suite Evolution Plan

## Goal

Evolve `survey-creator-skill` from a single generation skill into a **survey skill suite repository** without breaking the existing generation pipeline.

The repository should keep its current generator capability intact and add adjacent skills for:

- publishing
- backend submission/runtime scaffolding
- analytics
- orchestration

## Non-goal

Do not rewrite the current generator.

Do not merge publishing, backend, and analytics responsibilities into the current `survey-creator-skill` body.

Do not create a second repository unless there is a packaging constraint that cannot be solved inside this repo.

## Why reuse this repository

The current repository already contains the hardest and most valuable layer:

- schema legality references
- validators
- runtime validation
- payload validation
- HTML renderer
- real-world examples

Those are upstream primitives for the whole workflow.

If publishing, backend, and analytics are built elsewhere, they will either:

1. duplicate these rules
2. drift from these rules
3. treat survey output as loosely structured files instead of validated artifacts

Reusing this repository avoids that.

## Target repository model

Keep this repository as the **source-of-truth survey suite repo**.

Recommended shape:

```text
survey-creator-skill/
  README.md
  README.zh-CN.md
  SKILL.md
  docs/

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
      references/
      scripts/
    analytics/
      SKILL.md
      references/
      scripts/
    orchestrator/
      SKILL.md
      references/

  services/
    tencent-cloudbase/
      functions/
      docs/
      configs/
```

## Why `skills/`

Use a dedicated `skills/` directory because:

- this repository is no longer just one root skill
- multiple installable / packageable skills should have a predictable home
- this matches repositories like `dbskill`, where the repo root is the product container and `skills/` is the distribution boundary
- sub-skills can reuse shared root references and docs without pretending they are standalone repos

## Root compatibility

If backward compatibility matters, keep a lightweight root-level `SKILL.md` temporarily as a bridge that points to `skills/survey-creator/`.

But the long-term canonical location for the generator skill should be:

```text
skills/survey-creator/
```

## Skill roles

### `skills/survey-creator`

Role:
- survey intent -> schema -> validated html -> payload sample -> report

This remains the upstream artifact producer.

### `skills/publisher`

Role:
- consume a generated bundle
- archive artifacts in provider storage
- deploy HTML to a browser-openable web-facing hosting layer
- produce a publish record

Current first provider:
- `tencent`

### `services/tencent-cloudbase`

Role:
- real runtime service layer, not a skill
- store survey answers
- provide submission endpoint
- provide CloudBase Functions and document-database integration

Recommended storage model:
- survey answers stored as full JSON payload documents
- no need to flatten answers into relational rows in the first phase

### `skills/analytics`

Role:
- consume schema + answers
- produce analytics summaries and insight reports

### `skills/orchestrator`

Role:
- route multi-step user intents across the above skills

Example:
- generate survey
- publish to Tencent
- wire submission backend

## Shared contracts

The suite should not exchange loose files informally.

All downstream skills should consume a normalized bundle contract.

Recommended bundle:

```text
<bundle-dir>/
  survey.html
  survey.schema.json
  survey.payload.sample.json
  survey.report.json
  survey.manifest.json
```

`survey.manifest.json` is the handoff object between skills.

## Manifest minimum

```json
{
  "surveyId": "survey-310992845731864576",
  "title": "Example survey",
  "version": "1.0.0",
  "createdAt": "2026-05-27T10:00:00+08:00",
  "paths": {
    "html": "./survey.html",
    "schema": "./survey.schema.json",
    "samplePayload": "./survey.payload.sample.json",
    "report": "./survey.report.json"
  },
  "submission": {
    "contractVersion": "default-v1",
    "endpoint": "",
    "method": "POST"
  },
  "publish": {
    "provider": "",
    "mode": "",
    "surveyUrl": "",
    "schemaUrl": "",
    "htmlStorageUrl": "",
    "publishedAt": ""
  }
}
```

## Migration strategy

### Phase 1

Do not break the current `skills/survey-creator/` generator logic.

Only add:

- suite documentation
- new sub-skill specs
- manifest contract docs

### Phase 2

Add `skills/publisher/`.

This is the first operational downstream skill and should be implemented before backend or analytics.

Reason:
- it directly consumes current generator output
- it solves the first real deployment problem
- it forces the bundle contract to become concrete

### Phase 3

Add `services/tencent-cloudbase/`.

This depends on stable publish metadata and stable schema contract.
It should be implemented as deployable service code, not as a skill.

### Phase 4

Add `skills/analytics/`.

This depends on stable answer payloads and schema semantics.

### Phase 5

Add `skills/orchestrator/`.

This should be last, because orchestration on unstable primitives only hides design mistakes.

## What should change in the root skill

Only lightweight, backward-compatible changes are justified during migration:

1. document that the repository is becoming a suite repo
2. formalize bundle output naming
3. formalize manifest generation
4. reference downstream skills and services in docs
5. keep a temporary root bridge only if packaging compatibility requires it

The generator skill should not become a deployment skill.

## Recommended next implementation step

Implement `skills/publisher/` first, with `tencent` as the first provider.

This is the smallest useful addition and the one most tightly connected to the current user pain:

- generated HTML exists
- schema exists
- users need a stable online survey URL

## Packaging note

Two distribution models are possible later:

1. single repository, multiple skill entrypoints under `skills/`, plus real runtime service code under `services/`
2. root repo as source-of-truth, with optional split-out packaged skills

For now, keep model 1.

The repository should evolve first; packaging can be decided later.
