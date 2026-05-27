# Submission API contract

This repository defines the endpoint and payload format that generated survey HTML should submit.

It does not implement the backend endpoint.

## Default endpoint

Generated survey HTML submits to:

```text
POST /api/survey/submit
```

Adopters should implement this endpoint in their own application.

The generated HTML will call this endpoint automatically when it is hosted under the adopter's domain. Users should not need to modify the generated HTML just to wire answer collection.

## HTTP expectation

- method: `POST`
- path: `/api/survey/submit`
- content type: `application/json`
- credentials: same-origin

## Request body

```json
{
  "surveyId": "survey-310992845731864576",
  "submittedAt": 1748320800000,
  "answers": [
    {
      "questionId": "radio-123456",
      "questionType": "radio",
      "value": {
        "optionId": "radio-654321",
        "childAnswers": []
      }
    }
  ],
  "extra": {
    "utm_source": "wechat",
    "campaign": "spring"
  }
}
```

## Rules

- `submittedAt` must be a millisecond timestamp
- unanswered questions must not appear in `answers`
- `extra` should contain all page URL search params visible at submit time
- every `questionId`, `optionId`, and `childId` must belong to the concrete survey schema
- the backend must validate the payload against the concrete survey schema before storing it
- the backend should return JSON for both success and failure

## Success response

The endpoint should return HTTP `2xx` and either an empty JSON-compatible success body or:

```json
{
  "ok": true,
  "surveyId": "survey-310992845731864576",
  "submissionId": "submission-001"
}
```

## Failure response

For validation errors, return HTTP `400` or `422`:

```json
{
  "ok": false,
  "code": "INVALID_PAYLOAD",
  "message": "Payload does not match schema."
}
```

Recommended error codes:

- `INVALID_JSON`
- `INVALID_PAYLOAD`
- `SURVEY_NOT_FOUND`
- `SURVEY_CLOSED`
- `DUPLICATE_SUBMISSION`
- `RATE_LIMITED`
- `INTERNAL_ERROR`

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

When opened from `file://`, the generated HTML treats submission as a local preview success and still logs the payload for inspection.

For automated tests or custom host integration, a page may define:

```js
window.__surveySubmit = async (payload, context) => ({ ok: true });
```

If this hook exists, the generated HTML uses it instead of `fetch`.
