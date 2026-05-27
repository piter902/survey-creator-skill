# Survey fields

Use this reference for the welcome / intro node.

## Purpose
The `survey` node represents the opening section of the questionnaire.
In HTML, it usually becomes the hero, intro card, or welcome block.

## Fields

### `type`
- Expected value: `survey`
- Meaning: identifies this node as the questionnaire introduction
- Rule: never change this value for a welcome node

### `id`
- Meaning: unique identifier for the survey intro node
- Rule: generate `survey-<long snowflake>`, using the `survey` prefix plus a global long snowflake numeric suffix
- Rule: this id must remain globally unique across all questionnaires, not just inside the current schema
- Important: ids support later positioning and analytics, not just rendering
- HTML note: may also be reused as a DOM anchor or `data-schema-id`

### `title`
- Type: `string`
- Meaning: primary heading shown at the top of the page
- Supports: rich text
- HTML note: render as rich text, not plain text-only output
- Recommended use: short and clear

### `description`
- Type: `string`
- Meaning: secondary explanation under the title
- Supports: rich text
- HTML note: render as rich text
- Recommended use: explain purpose, expected duration, and context

### `attribute`
Top-level configuration container for welcome-level optional metadata.

#### `attribute.media`
- Meaning: optional media associated with the intro
- Allowed media types: `image`, `video`, `audio`
- Resource value: may be a link or base64 data
- Rule: only include if the prompt explicitly asks for media or the scenario strongly benefits from it

#### `attribute.onePageOneQuestion`
- Meaning: whether the questionnaire should be rendered one question per page
- Value meaning:
  - `true` = one page one question
  - `false` or omitted = multi-question page allowed
- HTML implication: intro, every question, and finish should each render as independent screens when enabled

#### `attribute.allowBack`
- Meaning: whether previous-page navigation is supported
- Value meaning:
  - `true` = support previous page
  - `false` = do not support previous page
- HTML implication: controls whether a previous-step action should be rendered in step mode

## Rendering guidance
- Usually render this node before all questions
- This node is informational, not answer-bearing
- Keep hierarchy strong: title first, description second, optional meta third

## Semantic guidance

### Recommended patterns
- `title` should answer “what is this survey”
- `description` should explain scope, expected time, privacy, or participation context
- `onePageOneQuestion=true` is the preferred mode when the product is optimized for focused, step-by-step completion
- `allowBack=true` makes the most sense only when `onePageOneQuestion=true`

### Common misuses
- Do not stuff question instructions into `survey.description`
- Do not make `title` a full paragraph; that belongs in `description`
- Do not use the intro as the main submit area
- Do not enable `allowBack` for a non-step layout unless the UI really has a previous-step concept

### Lint-worthy situations
- visually rich but semantically empty `title`
- overly long `description`
- `allowBack=true` while `onePageOneQuestion=false`
