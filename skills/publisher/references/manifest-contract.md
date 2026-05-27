# Manifest Contract

`survey-publisher` consumes a survey bundle through `survey.manifest.json`.

## Preferred entrypoint

```text
/absolute/path/to/bundle/survey.manifest.json
```

## Minimum manifest shape

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
    "publishedAt": "",
    "meta": {}
  }
}
```

## Rules

- `surveyId` is required
- `paths.html` is required
- `paths.schema` is required
- downstream skills must resolve file locations through manifest paths rather than filename guessing
- after publish, `publish.*` fields should be updated in place
- provider-specific details should go into `publish.meta`

## Publish record

The publisher skill should also emit a sibling `publish-record.json` or similarly named record beside the bundle.
