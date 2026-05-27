# Specs Overview

This directory defines the integration contracts adopters implement around the open-source skills in this repository.

The repository itself does not implement a hosted survey backend, survey publishing service, or answer database.

## What these specs cover

- how generated survey bundles are named and handed off
- how generated HTML submits answer payloads
- how adopters should save survey HTML and schema files
- how adopters should persist answer data
- how `survey-analytics` consumes answer datasets

## Recommended reading order

If you are integrating `survey-creator` into your own application, read in this order:

1. [survey-bundle.md](./survey-bundle.md)
2. [survey-file-storage.md](./survey-file-storage.md)
3. [submission-api.md](./submission-api.md)
4. [answer-storage.md](./answer-storage.md)
5. [analytics-input.md](./analytics-input.md)
6. [minimal-backend-example.md](./minimal-backend-example.md)
7. [integration-checklist.md](./integration-checklist.md)

## Contract map

| Spec | Purpose |
|---|---|
| [survey-bundle.md](./survey-bundle.md) | Defines the generated file set and manifest handoff. |
| [survey-file-storage.md](./survey-file-storage.md) | Defines how generated HTML/schema files should be saved and uploaded. |
| [submission-api.md](./submission-api.md) | Defines the default browser-to-backend submit contract. |
| [answer-storage.md](./answer-storage.md) | Defines the recommended answer persistence model after submit succeeds. |
| [analytics-input.md](./analytics-input.md) | Defines the dataset shapes `survey-analytics` can consume. |
| [minimal-backend-example.md](./minimal-backend-example.md) | Shows the smallest practical backend integration flow. |
| [integration-checklist.md](./integration-checklist.md) | Defines the release checklist for a complete adopter integration. |

## Example files

Concrete sample files live under [`specs/examples/`](./examples):

- `sample-survey.manifest.json`
- `sample-publish-result.json`
- `sample-submit-payload.json`
- `sample-submission-record.json`
- `sample-analytics-dataset.json`

## End-to-end integration flow

```text
survey-creator
  -> bundle files
  -> adopter uploads HTML/schema
  -> respondent opens <survey.id>.html
  -> browser POST /api/survey/submit
  -> adopter validates against concrete schema
  -> adopter stores payload
  -> survey-analytics reads schema + dataset
```

## Boundary

These specs intentionally do not define:

- login or registration flows
- tenant and permission systems
- survey management dashboards
- cloud-provider-specific deployment code
- billing, quotas, or workspace ownership logic

Those belong to the adopter's own product and infrastructure.
