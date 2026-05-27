# Answer storage contract

This repository recommends how adopters persist submitted survey answers after `POST /api/survey/submit` succeeds.

It does not require a specific database or storage engine.

## Goal

The storage layer should make it possible to:

- replay the original submission payload
- audit what the browser actually submitted
- analyze answers later without losing schema identity
- support export, re-validation, and downstream analytics

## Core rule

Store the submitted payload as a whole JSON document.

Do not flatten the first implementation unless there is a real reporting or indexing need.

The raw payload is the source of truth. Any denormalized fields are secondary indexes or query helpers.

## Recommended submission record

```json
{
  "submissionId": "submission-310992845731864577",
  "surveyId": "survey-310992845731864576",
  "submittedAt": 1748320800000,
  "receivedAt": 1748320800123,
  "payload": {
    "surveyId": "survey-310992845731864576",
    "submittedAt": 1748320800000,
    "extra": {
      "utm_source": "wechat",
      "campaign": "spring"
    },
    "answers": []
  },
  "extra": {
    "utm_source": "wechat",
    "campaign": "spring"
  },
  "status": "accepted",
  "createdAt": 1748320800123
}
```

## Field meanings

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `submissionId` | string | yes | Server-generated unique record id. |
| `surveyId` | string | yes | Survey id for partitioning and lookup. |
| `submittedAt` | integer | yes | Browser-side submit timestamp from the payload. |
| `receivedAt` | integer | recommended | Server-side receive timestamp. |
| `payload` | object | yes | The original validated submit payload. |
| `extra` | object | recommended | Convenience copy of `payload.extra` for easier filtering. |
| `status` | string | recommended | Storage or acceptance status, such as `accepted`. |
| `createdAt` | integer | yes | Storage write timestamp. |

## Required rules

- keep the original validated payload under `payload`
- keep `payload.answers` unchanged after validation
- ensure `submissionId` is unique within the storage system
- ensure `surveyId` matches `payload.surveyId`
- validate against the concrete schema before storing
- store millisecond timestamps, not formatted date strings, for time fields used by systems

## Recommended indexes

Minimum indexes:

- `surveyId`
- `submissionId`
- `createdAt`

Recommended additional indexes when filtering by campaign or source:

- `extra.utm_source`
- `extra.campaign`
- `payload.submittedAt`

## Optional ownership and business fields

If the adopter has an account system or management backend, they may additionally store:

- `ownerId`
- `workspaceId`
- `projectId`
- `publishedSurveyId`
- `channelId`
- `operatorId`

These fields are adopter-owned and external to this repository's core skill contracts.

## Security and retention

Recommended rules:

- do not trust `extra` as authorization data
- sanitize any respondent-provided values before rendering them in admin/reporting UIs
- keep schema-private surveys and answer data behind the adopter's own permission model
- define retention and deletion policy in the adopter system
- if personal data is collected, apply the adopter's compliance and export rules

## Analytics compatibility

`survey-analytics` can work from either:

1. the raw payload shape itself
2. a storage record that contains the raw payload under `payload`

If the adopter stores a wrapped submission document, keep `payload` intact so analytics can consume it without lossy transformation.
