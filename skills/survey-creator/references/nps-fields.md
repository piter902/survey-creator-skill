# NPS question fields

Use this reference for Net Promoter Score / recommendation-intent questions.

## Purpose
The `nps` node represents a single 0-10 style recommendation score question.

## Fields

### `type`
- Expected value: `nps`
- Meaning: identifies an NPS question

### `id`
- Meaning: unique identifier for the question
- Rule: must use `nps-xxxxxx`, with the `nps` prefix plus a 6-digit snowflake-style numeric suffix
- Rule: must remain unique within the questionnaire

### `title`
- Type: `string`
- Meaning: the main NPS question text, usually asking recommendation willingness
- Supports: rich text

### `description`
- Type: `string`
- Meaning: helper instruction for the scoring scale
- Supports: rich text

### `attribute.required`
- Meaning: whether the NPS question must be answered
- `true` = required
- `false` = optional

### `attribute.media`
- Meaning: optional media attached to the NPS question itself
- Supported media types: image, audio, video
- Resource value: link or base64
- Rendering: show near the question description before the scale

### `option`
- Meaning: NPS scale configuration collection
- Recommended: one option item per NPS question
- Important: preserve `option[].id` in payload for analytics and future positioning

## Option fields

### `option[].id`
- Meaning: unique identifier for the NPS scale configuration
- Rule: NPS option ids also use `nps-xxxxxx`
- Rule: must remain unique within the questionnaire

### `option[].attribute.scope`
- Type: `array`
- Required shape: `[min, max]`
- Standard NPS shape: `[0, 10]`
- Meaning: numeric NPS score range
- Rule: `min < max`; render integer score values in this range

### `option[].attribute.media`
- Meaning: optional media attached to the NPS scale / scoring context
- Supported media types: image, audio, video
- Resource value: link or base64
- Rendering: show near the NPS scale

### `option[].attribute.scoreDesc`
- Type: `object`
- Optional
- Meaning: segment description map keyed by score ranges
- Range key format: `min-max`
- Example:

```json
{
  "0-6": "非常不满意",
  "7-8": "一般",
  "9-10": "非常满意"
}
```

## Rendering guidance
- render one NPS scale from `option[0]`
- render all integer values derived from `scope`
- when `scoreDesc` exists, show the matching segment description after a value is selected
- if `required=true`, a score must be selected before submit

## Submission guidance
Recommended answer shape:

```json
{
  "questionId": "question_xxx",
  "questionType": "nps",
  "value": {
    "optionId": "option_xxx",
    "score": 9
  }
}
```

## Semantic guidance

### Recommended patterns
- use `nps` for recommendation willingness, brand loyalty, product advocacy, and post-purchase satisfaction
- prefer the standard `[0, 10]` scope
- use `scoreDesc` ranges to explain detractor / passive / promoter segments

### Common misuses
- do not use multiple NPS options unless there is a strong reason
- do not use non-integer NPS scores
- do not use scoreDesc keys outside the configured scope
- do not replace a multi-dimensional rating matrix with NPS; use `score` for multi-item rating

### Lint-worthy situations
- `scope` invalid or reversed
- non-standard NPS scope
- multiple option items in one NPS question
- scoreDesc range keys outside `scope`
