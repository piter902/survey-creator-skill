# Skill Suite Evolution Plan

## Goal

Evolve `survey-creator-skill` from a single generation skill into a **survey skill suite repository** without breaking the existing generation pipeline.

The repository should keep its current generator capability intact and add one adjacent skill for:

- analytics

## Non-goal

Do not rewrite the current generator.

Do not merge hosting, backend, and analytics responsibilities into the current `survey-creator-skill` body.

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

If analytics and external integrations are built elsewhere, they will either:

1. duplicate these rules
2. drift from these rules
3. treat survey output as loosely structured files instead of validated artifacts

Reusing this repository avoids that.

## Target repository model

Keep this repository as the **source-of-truth survey skill + contract repo**.

Recommended shape:

```text
survey-creator-skill/
  README.md
  README.zh-CN.md
  SKILL.md
  docs/
  specs/

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
    survey-analytics/
      SKILL.md
      references/
```

`specs/` is where backend/storage/hosting integration contracts live.

They are intentionally **not** implemented as first-party hosted services in this repository.

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

### `skills/survey-analytics`

Role:
- consume schema + answers
- produce analytics summaries and insight reports

### `specs/*`

Role:
- define how adopters should host generated HTML
- define how adopters should receive answer payloads
- define how adopters should store answers
- define what `survey-analytics` expects as input

## Shared contracts

The repository should not exchange loose files informally.

The core skills and external adopters should consume a normalized bundle contract.

Recommended bundle:

```text
<bundle-dir>/
  survey.html
  survey.schema.json
  survey.payload.sample.json
  survey.report.json
  survey.manifest.json
```

`survey.manifest.json` is the handoff object between the creator skill and any external system.

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
    "endpoint": "/api/survey/submit",
    "method": "POST"
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

Add `skills/survey-analytics/` and formalize `specs/`.

Reason:
- analytics is a natural second skill
- hosting/storage/submission should remain external implementation concerns
- it forces the bundle contract to become concrete

### Phase 3

Refine `specs/` based on real adopter feedback.

This should focus on:

- bundle portability
- submission payload interoperability
- answer storage compatibility
- analytics input clarity

## What should change in the root skill

Only lightweight, backward-compatible changes are justified during migration:

1. document that the repository is becoming a suite repo
2. formalize bundle output naming
3. formalize manifest generation
4. reference the analytics skill and external integration specs in docs
5. keep a temporary root bridge only if packaging compatibility requires it

The generator skill should not become a deployment skill.

## Recommended next implementation step

Implement `skills/survey-analytics/` first and stabilize `specs/`.

This is the smallest useful addition that stays inside the right open-source boundary:

- generated HTML/schema already exist
- answer submission/storage should remain adopter-owned
- analytics is the natural second capability on top of the creator output

## Packaging note

Two distribution models are possible later:

1. single repository, many skills plus embedded service implementations
2. single repository, two core skills under `skills/`, plus protocol contracts under `specs/`

For now, keep model 2.

The repository should evolve first; packaging can be decided later.
