# Survey file storage contract

This repository defines how generated survey files should be saved and handed off to an adopter's hosting system.

It does not implement upload, CDN publishing, object storage, authentication, or a management backend.

## Goal

After `survey-creator` generates and validates a survey, adopters usually need to:

1. save the generated HTML file
2. save the repaired schema file
3. optionally save sample payload and pipeline report files
4. upload the respondent-facing HTML to static hosting or object storage
5. keep the schema available to the backend submission endpoint
6. return the respondent-facing survey URL and the adopter-owned management URL

This document defines the portable file contract for that workflow.

## Minimum saved files

For a generated survey with:

```json
{
  "survey": {
    "id": "survey-310992845731864576"
  }
}
```

save files using this naming rule:

```text
<bundle-dir>/
  survey-310992845731864576.html
  survey-310992845731864576.repaired.schema.json
  survey-310992845731864576.payload.json
  survey-310992845731864576.pipeline-report.json
  survey.manifest.json
```

Required:

- `<survey.id>.html`
- `<survey.id>.repaired.schema.json`
- `survey.manifest.json`

Recommended for debugging and release review:

- `<survey.id>.payload.json`
- `<survey.id>.pipeline-report.json`

## File roles

| File | Role | Respondent-facing |
|---|---|---:|
| `<survey.id>.html` | The actual survey page respondents open. | yes |
| `<survey.id>.repaired.schema.json` | The validated schema used to render and validate submissions. | no by default |
| `<survey.id>.payload.json` | Sample payload generated for contract testing. | no |
| `<survey.id>.pipeline-report.json` | Validation and release decision report. | no |
| `survey.manifest.json` | Handoff metadata for upload, management, and integration systems. | no by default |

## MIME types

When uploading to object storage, static hosting, CDN, or any file server, set the correct content type.

| Extension | Content-Type |
|---|---|
| `.html` | `text/html; charset=utf-8` |
| `.json` | `application/json; charset=utf-8` |

The HTML file must render in the browser. If it downloads instead of rendering, the storage object is likely missing `Content-Type: text/html; charset=utf-8` or is being served with a forced-download `Content-Disposition`.

Do not set this for respondent-facing HTML:

```http
Content-Disposition: attachment
```

## Public and private file boundary

Recommended default:

- make `<survey.id>.html` publicly readable
- keep `<survey.id>.repaired.schema.json` private or server-side only
- keep payload samples and pipeline reports private
- expose management pages only through the adopter's own application and permission model

Reason:

- respondents only need the HTML page
- the backend needs the schema to validate submissions
- schema, reports, and sample payloads may reveal survey logic, internal ids, branch rules, or operational metadata

If an adopter intentionally serves schema publicly, it should be a conscious product/security decision, not the default.

## Recommended storage paths

This contract is provider-neutral. The same layout can be used on object storage, static hosting, or application storage.

Recommended object paths:

```text
surveys/<survey.id>/<survey.id>.html
surveys/<survey.id>/<survey.id>.repaired.schema.json
surveys/<survey.id>/<survey.id>.payload.json
surveys/<survey.id>/<survey.id>.pipeline-report.json
surveys/<survey.id>/survey.manifest.json
```

Example:

```text
surveys/survey-310992845731864576/survey-310992845731864576.html
surveys/survey-310992845731864576/survey-310992845731864576.repaired.schema.json
surveys/survey-310992845731864576/survey.manifest.json
```

## Cache control

Recommended defaults:

| File | Cache-Control |
|---|---|
| HTML | `no-cache` or short `max-age` while iterating |
| Schema | `private, no-cache` if served through backend |
| Versioned immutable assets | `public, max-age=31536000, immutable` |
| Reports / samples | private, no-cache |

Because the generated HTML is named by `survey.id`, not by content hash, adopters should avoid long immutable caching for HTML unless they never overwrite a published survey file.

## Manifest storage metadata

`survey.manifest.json` should include local file paths before upload and may include hosted URLs after upload.

Minimum:

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

After an adopter uploads the files, their own system may extend the manifest:

```json
{
  "surveyId": "survey-310992845731864576",
  "urls": {
    "surveyUrl": "https://example.com/surveys/survey-310992845731864576/survey-310992845731864576.html",
    "managementUrl": "https://app.example.com/surveys/survey-310992845731864576",
    "schemaUrl": "https://internal.example.com/surveys/survey-310992845731864576/schema"
  },
  "storage": {
    "provider": "custom",
    "bucket": "example-bucket",
    "htmlObjectKey": "surveys/survey-310992845731864576/survey-310992845731864576.html",
    "schemaObjectKey": "surveys/survey-310992845731864576/survey-310992845731864576.repaired.schema.json"
  }
}
```

The `urls` and `storage` fields are adopter-owned extensions. This repository does not require a specific provider shape.

## Upload workflow

Recommended adopter workflow:

1. Run `survey-creator` and generate the validated bundle.
2. Human-check the generated HTML and schema when needed.
3. Upload `<survey.id>.html` with `Content-Type: text/html; charset=utf-8`.
4. Save `<survey.id>.repaired.schema.json` somewhere the submission backend can read.
5. Save or generate `survey.manifest.json` in the adopter's own management system.
6. Return at least:
   - `surveyUrl`
   - `managementUrl`
   - `surveyId`
7. Use the concrete schema during `POST /api/survey/submit` validation.

## Returned publish result

When an adopter builds a publisher around this repository, the recommended publish result is:

```json
{
  "ok": true,
  "surveyId": "survey-310992845731864576",
  "surveyUrl": "https://example.com/surveys/survey-310992845731864576/survey-310992845731864576.html",
  "managementUrl": "https://app.example.com/surveys/survey-310992845731864576",
  "storage": {
    "htmlObjectKey": "surveys/survey-310992845731864576/survey-310992845731864576.html",
    "schemaObjectKey": "surveys/survey-310992845731864576/survey-310992845731864576.repaired.schema.json"
  }
}
```

This publish result is a recommendation for adopters. It is not produced by the current skills directly.

## Provider-specific notes

For object storage providers such as Tencent COS, Aliyun OSS, S3-compatible storage, or Cloudflare R2:

- upload HTML as a normal object, not as an attachment
- set HTML content type to `text/html; charset=utf-8`
- use a public-read bucket/object or signed URL for respondent access
- ensure the default domain or CDN domain serves `.html` as a page
- keep schema/report/sample files private unless there is a clear reason to expose them

For application-hosted files:

- serve the HTML through a static route
- serve or load schema server-side for submission validation
- do not require respondents to access schema directly

## Non-goals

This repository does not define:

- which cloud provider to use
- how to authenticate administrators
- how to implement survey ownership
- how to build a management dashboard
- how to upload files from a UI
- how to store respondent answers

Those belong to the adopter's product or infrastructure.
