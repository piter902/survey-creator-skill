# Publish Contract

Every provider should return the same normalized publish result.

## Normalized publish result

```json
{
  "publishId": "publish-survey-310992845731864576-20260527T103000",
  "surveyId": "survey-310992845731864576",
  "provider": "tencent",
  "mode": "public-web",
  "surveyUrl": "https://example-host/surveys/survey-310992845731864576.html",
  "schemaUrl": "https://example-archive/surveys/survey-310992845731864576/survey.schema.json",
  "htmlStorageUrl": "https://example-archive/surveys/survey-310992845731864576/survey.html",
  "publishedAt": "2026-05-27T10:30:00+08:00",
  "meta": {}
}
```

## Required semantics

- `surveyUrl`: respondent-facing URL when mode is `public-web`
- `schemaUrl`: archive URL for schema
- `htmlStorageUrl`: archive URL for html if archived
- `meta`: provider-specific fields

## Failure rule

If publish is partial, keep the same shape but include provider-specific failure details in `meta` and do not mark manifest as fully published.
