# Radio question fields

Use this reference for single-choice questions.

## Purpose
The `radio` node represents a question where the respondent may choose exactly one option.

## Fields

### `type`
- Expected value: `radio`
- Meaning: identifies a single-choice question

### `id`
- Meaning: unique identifier for the question
- Rule: must use `radio-xxxxxx`, with the `radio` prefix plus a 6-digit snowflake-style numeric suffix
- Rule: must remain unique within the whole questionnaire
- HTML note: should map cleanly to `data-question-id`, field grouping, and analytics hooks

### `title`
- Type: `string`
- Meaning: the main question text
- Supports: rich text
- Rule: should be answerable as a single-select decision

### `description`
- Type: `string`
- Meaning: helper copy for context or answering instruction
- Supports: rich text
- Optional in spirit, but preferred when it improves clarity

### `attribute`
Question-level settings.

#### `attribute.required`
- Meaning: whether this question must be answered before submission
- `true` = required
- `false` = optional

#### `attribute.random`
- Meaning: whether option order should be randomized
- `true` = randomize options
- HTML implication: if implemented, randomize only the display order, not the option identity

#### `attribute.media`
- Meaning: optional media attached to the question itself
- Supported media types: image, audio, video
- Resource value: link or base64

### `option`
- Meaning: array of answer choices
- Rule: radio questions must use an option array

## Option fields

### `option[].title`
- Type: `string`
- Meaning: visible option label
- Supports: rich text

### `option[].id`
- Meaning: unique option identifier
- Rule: radio option ids also use `radio-xxxxxx`
- Rule: must remain unique inside the questionnaire

### `option[].child`
- Meaning: optional follow-up inputs attached to a specific option
- If present, that means this option should insert one or more fill-in fields after the option
- Typical child type: `input`
- Use only when the option logically requires explanation, such as “Other, please specify”
- Child note: child items may also include their own `attribute` configuration; when present, treat it as full rendering and validation metadata for that child input
- Child attribute rule: because these child nodes are input-like fill-in fields, their `attribute` semantics should follow the same input-field configuration model you already received, including things like required state, placeholder, dataType, and length-related constraints when present

### `option[].attribute`
Option-level metadata container.

#### `option[].attribute.random`
- Meaning: option-level randomization override
- `false` = this option must remain fixed even if the parent question has `attribute.random === true`
- Use case: keep important anchor options stable while randomizing the rest

#### `option[].attribute.media`
- Meaning: optional media tied to one specific option
- Supported media types: image, audio, video
- Resource value: link or base64

## Rendering guidance
- Render with true single-select controls
- All options in one question must share one radio group name
- If question-level random is enabled, options with `option[].attribute.random === false` must remain fixed in place
- Child inputs should only appear when the related option is selected

## Semantic guidance

### Recommended patterns
- Use `radio` only when exactly one answer is allowed
- Keep option count small and mutually exclusive in meaning
- Use `child` only for explanation-style follow-ups such as “Other, please specify”
- If `attribute.random=true`, keep anchors like “Other” or “None of the above” fixed via `option[].attribute.random=false`

### Common misuses
- Do not use `radio` for “choose all that apply”
- Do not add multiple “Other” style options
- Do not attach child inputs to ordinary options unless the follow-up is truly conditional
- Do not set option-level `random=false` when the question itself is not randomized

### Lint-worthy situations
- fewer than 2 options
- multiple “other/其它/其他” options
- child input attached to a non-explanation option
- optional radio with too few options and no explicit skip path
