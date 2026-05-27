# Integration Checklist

Use this checklist before treating a `survey-creator` integration as production-ready.

## Bundle

- Generated bundle contains `<survey.id>.html`.
- Generated bundle contains `<survey.id>.repaired.schema.json`.
- Generated bundle contains `survey.manifest.json`.
- Manifest `surveyId` matches the schema `survey.id`.
- Manifest `paths.html` points to `<survey.id>.html`.
- Manifest `submission.contractVersion` is `default-v1`.

## File storage

- Respondent-facing HTML is uploaded with `Content-Type: text/html; charset=utf-8`.
- Respondent-facing HTML renders in browser instead of downloading.
- Schema file is stored somewhere the submit backend can read.
- Schema file is not publicly exposed unless intentionally designed that way.
- Payload sample and pipeline report are not respondent-facing.
- Published system can return a `surveyUrl`.
- Published system can return a `managementUrl`.

## Submit API

- Backend implements `POST /api/survey/submit` or the configured equivalent.
- Backend accepts `application/json`.
- Backend returns JSON on both success and failure.
- Backend validates payload shape before storage.
- Backend validates payload against the concrete schema before storage.
- Backend rejects unknown `questionId`, `optionId`, and `childId`.
- Backend uses millisecond timestamps for server-side time fields.
- Backend returns a unique `submissionId` on success.

## Runtime behavior

- Submit success clears local draft cache.
- Submit failure keeps local draft cache.
- Submit failure keeps respondent answers on screen.
- Finish-page redirect runs only after submit success.
- URL query params are submitted under `extra`.
- Repeated URL query params are preserved as string arrays in `extra`.
- Required questions are blocked client-side before final submit.

## Answer storage

- Stored record preserves the original validated payload under `payload`.
- Stored record keeps `surveyId` as a top-level indexed field.
- Stored record keeps `submissionId` as a unique field.
- Stored record keeps `createdAt` as a millisecond timestamp.
- Stored record keeps `receivedAt` if the backend tracks server receive time.
- Storage layer can query by `surveyId`.

## Analytics readiness

- Analytics dataset can be exported as JSON array or JSONL.
- Each analytics record can be normalized to either raw payload or `record.payload`.
- Mixed-survey records can be filtered by `surveyId`.
- Dataset export does not drop `answers` or `extra`.

## Security

- Backend does not trust `extra` for authorization or ownership.
- Admin/reporting UI escapes respondent-provided content before rendering.
- Public endpoints have rate limiting or equivalent abuse controls.
- Private schema and answer files are protected by the adopter's own access model.

## Final smoke test

- Open the public `surveyUrl` in a browser and confirm the page loads.
- Complete the survey once and confirm the backend stores one accepted record.
- Confirm the stored payload matches the survey schema.
- Trigger one expected validation failure and confirm the respondent sees a safe error message.
- Export one dataset and confirm `survey-analytics` can consume it.
