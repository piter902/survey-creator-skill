# Input question fields

Use this reference for free-text input questions.

## Purpose
The `input` node represents a question answered by typed text.

## Fields

### `type`
- Expected value: `input`
- Meaning: identifies a text-entry question

### `id`
- Meaning: unique question identifier
- Rule: must use `input-xxxxxx`, with the `input` prefix plus a 6-digit snowflake-style numeric suffix
- Rule: must remain unique within the questionnaire

### `title`
- Type: `string`
- Meaning: the prompt shown to the respondent
- Supports: rich text

### `description`
- Type: `string`
- Meaning: helper instruction for what kind of answer is expected
- Supports: rich text

### `attribute`
Question-level configuration.

#### `attribute.required`
- Meaning: whether this text question must be answered
- `true` = required
- `false` = optional

#### `attribute.media`
- Meaning: optional media attached to the question
- Supported media types: image, audio, video
- Resource value: link or base64

### `option`
- Meaning: array holding the input field definition
- Important: even though this is an input question, the reference still wraps the field definition inside `option[]`

## Option fields

### `option[].title`
- Type: `string`
- Meaning: label for the input field definition
- Supports: rich text

### `option[].id`
- Meaning: unique field identifier
- Rule: input option ids also use `input-xxxxxx`
- Rule: must remain unique within the questionnaire

### `option[].attribute`
Input behavior configuration.

#### `option[].attribute.dataType`
- Meaning: expected content type
- Allowed values: `email`, `tel`, `number`, `text`, `date`, `time`, `dateTime`, `dateRange`, `timeRange`, `dateTimeRange`
- Fallback rule: if the value is missing or unsupported, fall back to `text`
- Rule: do not casually invent unsupported datatype values

#### `option[].attribute.placeholder`
- Meaning: placeholder text shown inside the input control

#### `option[].attribute.maxLength`
- Meaning: maximum input length
- Follow the semantics described in the source JSON field description

#### `option[].attribute.minLength`
- Meaning: minimum input length
- Follow the semantics described in the source JSON field description

## Rendering guidance
- Render as a text input or textarea depending on prompt intent and expected answer length
- Preserve the semantic meaning of a free-text response
- When longer reflection is expected, a textarea is often more appropriate than a one-line input
- Do not assume `option[]` contains only one item; one `input` question may define multiple rendered input controls
- Submission should therefore preserve answers per `option[].id`, not collapse the whole question into a single scalar string


## `dataType` rendering guidance
- `dataType` should affect both control rendering and validation behavior
- `text` → text input or textarea
- `email` → email input
- `tel` → telephone input
- `number` → numeric input
- `date` → date input
- `time` → time input
- `dateTime` → datetime-local input
- `dateRange` → two coordinated date inputs or a range-style date UI
- `timeRange` → two coordinated time inputs or a range-style time UI
- `dateTimeRange` → two coordinated datetime-local inputs or a range-style datetime UI
- unknown or omitted values should fall back to `text`

## Submission guidance
- Serialize input answers by `option[]`, not by question title text
- Recommended per-option answer shape:

{
  "optionId": "option_xxx",
  "dataType": "text",
  "value": "..."
}

- For `dateRange`, `timeRange`, and `dateTimeRange`, serialize `value` as:

{
  "start": "...",
  "end": "..."
}

## Semantic guidance

### Recommended patterns
- Use `input` when the respondent should type, not choose
- A single `input` question may contain multiple `option[]` field definitions when the business object naturally has multiple fields
- Match `dataType` to the real data expectation, not to visual preference
- Use `maxLength` / `minLength` only for text-like constraints, not as a substitute for business validation on range fields

### Common misuses
- Do not use `number` for narrative answers just because the answer contains digits
- Do not use `dateRange` / `timeRange` / `dateTimeRange` for inline explanation fields
- Do not collapse multi-option input answers into one string at submit time
- Do not leave long-form prompts without any length guidance if downstream systems need bounded data

### Lint-worthy situations
- required input question without valid `option[]`
- range field uses `minLength` / `maxLength`
- `email` placeholder does not resemble an email hint
- `tel` placeholder does not resemble a phone hint
- `number` field title reads like a long-form text prompt
