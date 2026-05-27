# Tencent Provider

Current first provider implementation.

## Role mapping

- `archive` -> COS
- `publicWeb` -> CloudBase Hosting or another Tencent browser-openable hosting layer

## Required config

```json
{
  "provider": "tencent",
  "archive": {
    "bucket": "example-bucket",
    "region": "ap-guangzhou",
    "prefix": "surveys"
  },
  "publicWeb": {
    "type": "cloudbase-hosting",
    "envId": "example-env",
    "prefix": "/surveys"
  }
}
```

`publicWeb.prefix` is the public root path prefix.
If it is `/surveys`, the final public HTML path becomes:

```text
/surveys/<surveyId>.html
```

## Operational rule

Do not use COS default object-domain access as the primary respondent-facing HTML delivery path.

Use COS as archive, and CloudBase Hosting as delivery.

## Expected provider meta

```json
{
  "bucket": "example-bucket",
  "region": "ap-guangzhou",
  "schemaObjectKey": "surveys/survey-310992845731864576/survey.schema.json",
  "htmlObjectKey": "surveys/survey-310992845731864576/survey.html",
  "envId": "example-env",
  "publicPath": "/surveys/survey-310992845731864576.html"
}
```
