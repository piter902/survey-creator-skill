# Finish fields

Use this reference for each ending / completion node inside the top-level `finish` array.

## Purpose
Each `finish` node represents a possible final section of the questionnaire.
In HTML, it usually becomes the submit area, completion explanation, or final CTA section.

## Fields

### `type`
- Expected value: `finish`
- Meaning: identifies the end-of-survey node

### `title`
- Type: `string`
- Meaning: the closing heading
- Supports: rich text

### `description`
- Type: `string`
- Meaning: explanatory copy shown in the final section
- Supports: rich text

### `media`
- Meaning: optional media associated with the finish block
- Supported media types: image, audio, video
- Resource value: link or base64

## Top-level shape
Canonical survey shape:

```json
{
  "survey": { ... },
  "questions": [ ... ],
  "finish": [
    { ... }
  ]
}
```

You may include multiple finish nodes when different logic branches should land on different ending pages.

## Rendering guidance
- This section should contain or sit immediately adjacent to the submit action
- It should clarify the last step of the respondent journey
- Use it to reinforce trust, next steps, or a concise thank-you message

## Semantic guidance

### Recommended patterns
- `title` should signal completion, delivery, or confirmation
- `description` should explain what happens after submit, not repeat questionnaire instructions
- Keep finish copy short and confidence-building

### Common misuses
- Do not place question instructions in the finish block
- Do not turn the finish block into a second welcome section
- Do not use finish copy to restate required-field rules

### Lint-worthy situations
- semantically empty title
- description that reads like a question, a pagination hint, or a required-field instruction
