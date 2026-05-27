# Survey bundle contract

This repository does not prescribe hosting or backend implementation.

The `survey-creator` skill is responsible for generating a portable survey bundle that other systems can consume.

## Minimum bundle

```text
<bundle-dir>/
  <survey.id>.html
  <survey.id>.repaired.schema.json
  <survey.id>.payload.json
  <survey.id>.pipeline-report.json
  survey.manifest.json
```

## Required manifest fields

```json
{
  "surveyId": "survey-310992845731864576",
  "title": "Example survey",
  "version": "1.0.0",
  "createdAt": "2026-05-27T10:00:00+08:00",
  "paths": {
    "html": "./survey-310992845731864576.html",
    "schema": "./survey-310992845731864576.repaired.schema.json",
    "samplePayload": "./survey-310992845731864576.payload.json",
    "report": "./survey-310992845731864576.pipeline-report.json"
  },
  "submission": {
    "contractVersion": "default-v1",
    "endpoint": "/api/survey/submit",
    "method": "POST"
  }
}
```

## Ownership boundary

The bundle does not define:

- hosting provider
- respondent-facing URL
- answer storage implementation
- user account model

Those belong to the adopter's own system.
