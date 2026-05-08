# Checkbox question fields

Use this reference for multiple-choice questions.

## Purpose
The `checkbox` node represents a question where the respondent may choose multiple options.

## Fields

### `type`
- Expected value: `checkbox`
- Meaning: identifies a multi-select question

### `id`
- Meaning: unique identifier for the question
- Rule: must use `checkbox-xxxxxx`, with the `checkbox` prefix plus a 6-digit snowflake-style numeric suffix
- Rule: must remain unique within the questionnaire

### `title`
- Type: `string`
- Meaning: the main question text
- Supports: rich text

### `description`
- Type: `string`
- Meaning: helper copy such as “可多选” or extra instructions
- Supports: rich text

### `attribute`
Question-level settings.

#### `attribute.required`
- Meaning: whether at least one option should be selected
- `true` = required
- `false` = optional

#### `attribute.random`
- Meaning: whether options should be randomized
- `true` = randomize option order

#### `attribute.media`
- Meaning: optional question-level media
- Supported media types: image, audio, video
- Resource value: link or base64

### `option`
- Meaning: array of selectable options

## Option fields

### `option[].title`
- Type: `string`
- Meaning: visible option label
- Supports: rich text

### `option[].id`
- Meaning: unique option identifier
- Rule: checkbox option ids also use `checkbox-xxxxxx`
- Rule: must remain unique within the questionnaire

### `option[].child`
- Meaning: optional follow-up input shown after this option
- If present, this option should insert a fill-in field after itself when selected
- Good use case: `其他，请说明`
- Child note: child items may also include their own `attribute` configuration; when present, treat it as full rendering and validation metadata for that child input
- Child attribute rule: because these child nodes are input-like fill-in fields, their `attribute` semantics should follow the same input-field configuration model you already received, including things like required state, placeholder, and length-related constraints when present

### `option[].attribute`
Option-level metadata container.

#### `option[].attribute.random`
- Meaning: option-level randomization override
- `false` = this option must remain fixed even if the parent question has `attribute.random === true`
- Use case: keep important anchor options stable while randomizing the rest

#### `option[].attribute.exclusive`
- Meaning: this option is exclusive against all other options in the same checkbox question
- Interaction: when an option with `exclusive: true` is selected, all other selected options in this question must be cleared; when any non-exclusive option is selected, any selected `exclusive: true` option must be cleared
- Typical use: “以上都不是” / “不适用” / catch-all answers

#### `option[].attribute.mutual-exclusion`
- Meaning: this option is mutually exclusive only with other options that also have `mutual-exclusion: true` in the same checkbox question
- Interaction: when selecting one `mutual-exclusion: true` option, clear other selected options that also have `mutual-exclusion: true`, but do not clear normal non-mutual options
- This is different from `exclusive`: it only excludes options in the same mutual-exclusion group

#### `option[].attribute.media`
- Meaning: optional option-level media
- Supported media types: image, audio, video
- Resource value: link or base64

## Rendering guidance
- Render as true checkboxes
- If question-level random is enabled, options with `option[].attribute.random === false` must remain fixed in place
- If an option has `exclusive: true`, it should clear all other options in the same checkbox question when selected
- If an option has `mutual-exclusion: true`, it should only clear other selected options that also have `mutual-exclusion: true`
- Child inputs appear only when the related option is checked

## Semantic guidance

### Recommended patterns
- Use `checkbox` only when multiple selections are genuinely allowed
- `exclusive` is for catch-all answers such as “None”, “Not applicable”, “以上都不是”
- `mutual-exclusion` is for a small subgroup of options that should cancel each other, not the whole question
- Use `child` for “please specify” follow-ups, not as a replacement for main question text

### Common misuses
- Do not mark more than one option as `exclusive`
- Do not mark every option as `mutual-exclusion`; that usually means the question should be `radio`
- Do not give an `exclusive` option a child input unless there is a very strong business reason
- Do not set option-level `random=false` when the question itself is not randomized

### Lint-worthy situations
- more than one `exclusive`
- all options are `mutual-exclusion`
- only one option is `mutual-exclusion`
- `exclusive` option label does not look like a catch-all answer
- `exclusive` option also has `child`
