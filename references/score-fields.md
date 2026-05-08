# Score question fields

Use this reference for rating / score questions.

## Purpose
The `score` node represents a question where respondents rate one or more items on a numeric scale.

## Fields

### `type`
- Expected value: `score`
- Meaning: identifies a rating question

### `id`
- Meaning: unique identifier for the question
- Rule: must use `score-xxxxxx`, with the `score` prefix plus a 6-digit snowflake-style numeric suffix
- Rule: must remain unique within the questionnaire

### `title`
- Type: `string`
- Meaning: the main score question text
- Supports: rich text

### `description`
- Type: `string`
- Meaning: helper instruction for how to score
- Supports: rich text

### `attribute.required`
- Meaning: whether every score item in this question must be completed
- `true` = all score rows are required
- `false` = optional

### `attribute.media`
- Meaning: optional media attached to the score question itself
- Supported media types: image, audio, video
- Resource value: link or base64
- Rendering: show near the question description before the score rows

### `option`
- Meaning: score item collection
- Important: each option is one score row / one rating dimension

## Option fields

### `option[].id`
- Meaning: unique identifier for the scored item
- Rule: score option ids also use `score-xxxxxx`
- Rule: must remain unique within the questionnaire

### `option[].title`
- Type: `string`
- Meaning: label of the scored item
- Supports: rich text

### `option[].attribute.scope`
- Type: `array`
- Required shape: `[min, max]`
- Meaning: numeric score range
- Rule: `min < max`
- Recommended use: `[1, 5]`

### `option[].attribute.step`
- Allowed values: `0.5`, `1`
- Meaning: score increment
- `1` = integer-only rating
- `0.5` = half-step rating

### `option[].attribute.media`
- Meaning: optional media attached to a specific score item / rating dimension
- Supported media types: image, audio, video
- Resource value: link or base64
- Rendering: show inside the score item row near the item title

### `option[].attribute.scoreDesc`
- Type: `object`
- Optional
- Meaning: optional score description map by concrete score value
- Example:

```json
{
  "1": "非常不满意",
  "2": "不满意",
  "3": "一般",
  "4": "满意",
  "5": "非常满意"
}
```

## Rendering guidance
- render one score row per `option[]`
- render question-level `attribute.media` near the question description
- render score-item-level `option[].attribute.media` inside the related score row
- render all available score values derived from `scope` + `step`
- when `scoreDesc` exists, show the matching hint near the selected score or below the score row
- if `required=true`, all score rows must be answered before submit

## Submission guidance
Recommended answer shape:

```json
{
  "questionId": "question_xxx",
  "questionType": "score",
  "value": [
    {
      "optionId": "option_xxx",
      "score": 4
    }
  ]
}
```

## Semantic guidance

### Recommended patterns
- use `score` for satisfaction, preference, quality perception, and service evaluation
- use one option per rating dimension, such as appearance / usability / durability
- keep the scale consistent within one question

### Common misuses
- do not mix different ranges inside the same score question unless there is a strong business reason
- do not set `step` to unsupported values
- do not use `scoreDesc` keys that fall outside `scope`

### Lint-worthy situations
- `scope` invalid or reversed
- `step` not in `0.5 | 1`
- `scoreDesc` keys outside valid generated score values
