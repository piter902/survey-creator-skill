# Report shape

Recommended fields for a machine-readable analysis artifact:

```json
{
  "surveyId": "survey-310992845731864576",
  "summary": "",
  "sample": {
    "total": 0,
    "valid": 0,
    "invalid": 0
  },
  "questions": [],
  "segments": [],
  "warnings": [],
  "recommendations": []
}
```

Guidance:

- `summary` should fit in one paragraph
- `questions` should preserve `questionId`
- `segments` should describe grouping logic explicitly
- `warnings` should separate data-quality issues from business risk
