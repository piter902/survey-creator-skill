# Answer storage contract

This repository recommends how adopters persist submitted answers.

It does not require a specific database.

## Storage model

Store the submitted payload as a whole JSON document.

Do not flatten the first implementation unless you have a clear reporting need.

## Minimum fields

```json
{
  "surveyId": "survey-310992845731864576",
  "submissionId": "submission-001",
  "submittedAt": 1748320800000,
  "payload": {},
  "extra": {},
  "createdAt": 1748320800100
}
```

## Recommended rules

- keep the original payload for replay and audit
- preserve URL params under `extra`
- index by `surveyId`
- ensure `submissionId` is unique within the storage system
- validate against schema again on the server side before storing

## Ownership model

If the adopter has an account system, they may additionally store:

- `ownerId`
- `workspaceId`
- `projectId`

These fields are optional and external to this repository's core skill contracts.
