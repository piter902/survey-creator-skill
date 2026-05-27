# Minimal Backend Example

This document shows the smallest practical backend integration for `survey-creator`.

It is not a framework-specific implementation. The goal is to show the minimum logic your own backend must have to accept generated survey HTML submissions safely.

## What the backend needs to do

At minimum, your system needs these responsibilities:

1. save the generated survey HTML file
2. save the repaired schema file
3. expose the survey HTML at a public `surveyUrl`
4. implement `POST /api/survey/submit`
5. validate the submitted payload against the concrete schema
6. store the accepted payload as a JSON record

## Minimal data flow

```text
survey-creator output
  -> upload <survey.id>.html
  -> save <survey.id>.repaired.schema.json
  -> open surveyUrl in browser
  -> browser POST /api/survey/submit
  -> backend loads schema by surveyId
  -> backend validates payload
  -> backend stores submission record
  -> backend returns { ok: true, submissionId, receivedAt }
```

## Minimal publish-side state

Your application should store at least one publish record like this:

```json
{
  "surveyId": "survey-310992845731864576",
  "title": "Service satisfaction survey",
  "surveyUrl": "https://example.com/surveys/survey-310992845731864576/survey-310992845731864576.html",
  "managementUrl": "https://app.example.com/surveys/survey-310992845731864576",
  "htmlObjectKey": "surveys/survey-310992845731864576/survey-310992845731864576.html",
  "schemaObjectKey": "surveys/survey-310992845731864576/survey-310992845731864576.repaired.schema.json",
  "createdAt": 1748320700000
}
```

## Minimal submit handler logic

Pseudocode:

```text
handle POST /api/survey/submit:
  parse request JSON
  if invalid JSON:
    return 400 INVALID_JSON

  validate generic payload shape
  if invalid:
    return 400 INVALID_PAYLOAD

  load schema by payload.surveyId
  if schema not found:
    return 404 SURVEY_NOT_FOUND

  validate payload against concrete schema
  if invalid:
    return 422 SCHEMA_MISMATCH

  generate submissionId
  store accepted submission record

  return 200 {
    ok: true,
    surveyId,
    submissionId,
    receivedAt
  }
```

## Minimal Node-style example

This is intentionally plain pseudocode close to JavaScript:

```js
app.post('/api/survey/submit', async (req, res) => {
  const payload = req.body;

  const shapeReport = validateSurveyPayload(payload);
  if (!shapeReport.valid) {
    return res.status(400).json({
      ok: false,
      code: 'INVALID_PAYLOAD',
      message: 'Payload does not match the base submission contract.'
    });
  }

  const schema = await loadSurveySchema(payload.surveyId);
  if (!schema) {
    return res.status(404).json({
      ok: false,
      code: 'SURVEY_NOT_FOUND',
      message: 'Survey does not exist.'
    });
  }

  const schemaReport = validatePayloadAgainstSchema(schema, payload);
  if (!schemaReport.valid) {
    return res.status(422).json({
      ok: false,
      code: 'SCHEMA_MISMATCH',
      message: 'Payload does not match the concrete survey schema.'
    });
  }

  const submissionId = createSubmissionId();
  const receivedAt = Date.now();

  await saveSubmission({
    submissionId,
    surveyId: payload.surveyId,
    submittedAt: payload.submittedAt,
    receivedAt,
    payload,
    extra: payload.extra || {},
    status: 'accepted',
    createdAt: receivedAt
  });

  return res.status(200).json({
    ok: true,
    surveyId: payload.surveyId,
    submissionId,
    receivedAt
  });
});
```

## Minimal storage abstraction

Your backend needs only two read/write capabilities:

### 1. load schema by `surveyId`

```text
loadSurveySchema(surveyId) -> repaired schema JSON or null
```

### 2. save accepted submission record

```text
saveSubmission(record) -> persisted record
```

Everything else is optional optimization.

## Minimal release check

Before calling the integration complete, verify:

- `<survey.id>.html` opens in browser
- browser submit hits your backend
- backend can load the exact schema for that `surveyId`
- one valid response is accepted and stored
- one invalid response is rejected with JSON
- stored record still contains the original `payload`

## Recommended next step after the minimum works

After the minimal backend is stable, add:

- rate limiting
- ownership and permission checks in your management system
- export endpoint for analytics datasets
- publish logs and submission monitoring
