# Submission API contract

This repository defines the HTTP contract that generated survey HTML uses to submit answers.

It does not implement the backend endpoint. Adopters must implement the endpoint in their own application, serverless function, or API gateway.

## Contract version

Current version:

```text
default-v1
```

Generated survey manifests should reference this version under:

```json
{
  "submission": {
    "contractVersion": "default-v1",
    "endpoint": "/api/survey/submit",
    "method": "POST"
  }
}
```

## Default endpoint

Generated survey HTML submits to:

```text
POST /api/survey/submit
```

The generated HTML will call this endpoint automatically when it is hosted under the adopter's domain. Users should not need to modify the generated HTML just to wire answer collection.

If a different endpoint is required, it should be configured in schema metadata before rendering, not patched manually in the final HTML.

## HTTP request

### Method and path

```text
POST /api/survey/submit
```

### Headers

Required:

```http
Content-Type: application/json
Accept: application/json
```

Generated HTML sends the request with:

```js
credentials: 'same-origin'
```

This means the default contract is optimized for same-origin hosting:

- survey HTML and `/api/survey/submit` are served from the same site
- cookies can be included if the adopter has an auth/session layer
- no CORS setup is required for the default deployment model

If the API is hosted on a different origin, adopters must configure CORS themselves and ensure the browser is allowed to send JSON `POST` requests from the survey page origin.

## Request body

The request body must be one JSON object.

```json
{
  "surveyId": "survey-310992845731864576",
  "submittedAt": 1748320800000,
  "extra": {
    "utm_source": "wechat",
    "campaign": "spring",
    "tag": ["offline", "vip"]
  },
  "answers": [
    {
      "questionId": "radio-123456",
      "questionType": "radio",
      "value": {
        "optionId": "radio-654321"
      }
    }
  ]
}
```

### Top-level fields

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `surveyId` | string | yes | The concrete survey id from `schema.survey.id`. |
| `submittedAt` | integer | yes | Unix timestamp in milliseconds generated at final submit time. |
| `extra` | object | yes | URL search params captured from the survey page at submit time. Empty object when no params exist. |
| `answers` | array | yes | Submitted answers. Unanswered questions must not appear. |

### `submittedAt`

`submittedAt` must be a millisecond timestamp, for example:

```json
1748320800000
```

Do not send formatted date-time strings such as `2026-05-27T10:00:00+08:00` in this field.

### `extra`

Generated HTML copies all URL query params into `extra`.

Example page URL:

```text
https://example.com/survey-310992845731864576.html?utm_source=wechat&campaign=spring&tag=offline&tag=vip
```

Submitted `extra`:

```json
{
  "utm_source": "wechat",
  "campaign": "spring",
  "tag": ["offline", "vip"]
}
```

Rules:

- single query param value becomes a string
- repeated query param keys become an array of strings
- `extra` is attribution metadata only
- the backend must not trust `extra` for authorization, pricing, permissions, or ownership

## Answer formats

Each item in `answers` uses this base shape:

```json
{
  "questionId": "radio-123456",
  "questionType": "radio",
  "value": {}
}
```

Rules:

- `questionId` must exist in the concrete survey schema
- `questionType` must match the schema question type
- supported `questionType` values are `radio`, `checkbox`, `input`, `score`, and `nps`
- every submitted `optionId` must belong to the submitted question
- every submitted `childId` must belong to the selected option
- one question can appear at most once in `answers`

### Radio

```json
{
  "questionId": "radio-123456",
  "questionType": "radio",
  "value": {
    "optionId": "radio-654321",
    "child": [
      {
        "childId": "input-111111",
        "dataType": "text",
        "value": "其他原因"
      }
    ]
  }
}
```

Rules:

- `value.optionId` is required
- `value.child` is optional
- child answers are only valid when the selected option has matching `child[]` definitions in schema

### Checkbox

```json
{
  "questionId": "checkbox-123456",
  "questionType": "checkbox",
  "value": [
    {
      "optionId": "checkbox-654321"
    },
    {
      "optionId": "checkbox-654322",
      "child": [
        {
          "childId": "input-111112",
          "dataType": "text",
          "value": "补充说明"
        }
      ]
    }
  ]
}
```

Rules:

- `value` must be a non-empty array
- `exclusive` options must not be submitted together with other options
- only one `mutual-exclusion` option may be submitted in the same answer
- child answers follow the same rules as radio child answers

### Input

```json
{
  "questionId": "input-123456",
  "questionType": "input",
  "value": [
    {
      "optionId": "input-654321",
      "dataType": "email",
      "value": "user@example.com"
    },
    {
      "optionId": "input-654322",
      "dataType": "dateRange",
      "value": {
        "start": "2026-05-01",
        "end": "2026-05-07"
      }
    }
  ]
}
```

Rules:

- `value` must be a non-empty array
- one input question can contain multiple input fields under `option[]`
- each answered input field is serialized by its `optionId`
- scalar data types serialize `value` as a string
- range data types serialize `value` as `{ "start": "...", "end": "..." }`
- supported data types are `email`, `tel`, `number`, `text`, `date`, `time`, `dateTime`, `dateRange`, `timeRange`, and `dateTimeRange`

### Score

```json
{
  "questionId": "score-123456",
  "questionType": "score",
  "value": [
    {
      "optionId": "score-654321",
      "score": 4
    },
    {
      "optionId": "score-654322",
      "score": 4.5
    }
  ]
}
```

Rules:

- `value` must be a non-empty array
- each item represents one score row from `option[]`
- `score` may be integer or decimal according to the schema `scope` and `step`
- if the score question is required, every score row in that question must be submitted

### NPS

```json
{
  "questionId": "nps-123456",
  "questionType": "nps",
  "value": {
    "optionId": "nps-654321",
    "score": 9
  }
}
```

Rules:

- `value.optionId` must reference the NPS option in schema
- `value.score` must be an integer inside the configured NPS range, normally `0` through `10`
- `scoreDesc` is display metadata and should not be submitted

## Required backend behavior

The backend implementation should perform these checks before storing the answer:

1. Parse JSON and reject invalid JSON.
2. Validate the generic payload shape.
3. Load the concrete survey schema by `surveyId`.
4. Validate the payload against that exact schema.
5. Verify every `questionId`, `optionId`, `childId`, `dataType`, and score value belongs to the schema.
6. Enforce required question rules server-side.
7. Reject submissions for closed, deleted, or unavailable surveys.
8. Store the original payload as a whole JSON document after validation.

The frontend validation exists for user experience. It is not a security boundary.

## Success response

Return HTTP `200` or `201`.

Recommended response:

```json
{
  "ok": true,
  "surveyId": "survey-310992845731864576",
  "submissionId": "submission-310992845731864577",
  "receivedAt": 1748320800123
}
```

Fields:

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `ok` | boolean | yes | Must be `true` on success. |
| `surveyId` | string | recommended | Echoes the submitted survey id. |
| `submissionId` | string | recommended | Server-generated unique answer record id. |
| `receivedAt` | integer | recommended | Server receive timestamp in milliseconds. |

Generated HTML treats a `2xx` response with no JSON body as success, but returning JSON is strongly recommended for observability.

## Failure response

Return JSON for all expected failures.

```json
{
  "ok": false,
  "code": "INVALID_PAYLOAD",
  "message": "Payload does not match schema."
}
```

Recommended status and code mapping:

| HTTP status | Code | Meaning |
|---:|---|---|
| `400` | `INVALID_JSON` | Request body is not valid JSON. |
| `400` | `INVALID_PAYLOAD` | Generic payload shape is invalid. |
| `404` | `SURVEY_NOT_FOUND` | `surveyId` does not map to a known schema. |
| `409` | `DUPLICATE_SUBMISSION` | The same submission was already accepted. |
| `410` | `SURVEY_CLOSED` | Survey is no longer accepting answers. |
| `422` | `SCHEMA_MISMATCH` | Payload ids or values do not match the concrete schema. |
| `429` | `RATE_LIMITED` | Client submitted too frequently. |
| `500` | `INTERNAL_ERROR` | Unexpected server failure. |

Generated HTML displays `message` when available. Keep it respondent-safe and avoid exposing internal stack traces.

## Retry and idempotency

Generated HTML behavior:

- keeps local draft cache while the request is pending
- clears local draft cache only after a successful response
- keeps answers on screen if the request fails
- allows the respondent to submit again after failure
- only runs `finish[].postSubmit.redirect` after successful submission

Backend recommendations:

- tolerate duplicate user clicks and network retries
- generate a unique `submissionId` server-side
- if the adopter adds a client-side submission token later, enforce idempotency with that token
- never clear or mark a survey complete before the answer is durably stored

## Security and abuse controls

Adopters should implement at least:

- server-side payload validation against the concrete schema
- request body size limit
- per-IP or per-session rate limiting
- survey availability checks
- safe JSON storage without executing user-provided content
- output escaping in any admin/reporting UI that renders answers
- optional bot protection when public traffic is expected

Do not trust:

- browser-side required validation
- `extra` query params
- respondent-controlled URLs
- hidden fields or DOM state

## Generated HTML behavior

The generated HTML handles submission as follows:

1. validate all visible required questions
2. assemble the payload
3. call `POST /api/survey/submit`
4. keep local draft cache while the request is pending
5. clear local draft cache only after a successful response
6. run `finish[].postSubmit.redirect` only after successful submission
7. keep answers on screen and show an error message if the request fails

## Local preview and tests

When opened from `file://`, the generated HTML treats submission as a local preview success and logs the payload for inspection.

For automated tests or custom host integration, a page may define:

```js
window.__surveySubmit = async (payload, context) => ({ ok: true });
```

If this hook exists, the generated HTML uses it instead of `fetch`.

The `context` object contains:

```json
{
  "endpoint": "/api/survey/submit",
  "surveyId": "survey-310992845731864576"
}
```
