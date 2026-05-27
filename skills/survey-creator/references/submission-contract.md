# Submission contract

This document defines the default submission data protocol for `survey-creator-skill`.

This contract is the default until the user provides a more specific backend format.

Generated HTML submits this payload to `POST /api/survey/submit` by default.

Adopters should implement that endpoint in their own application. The generated HTML keeps local answers if the request fails, clears local cache only after success, and only runs finish redirects after successful submission.

## Goal
The submission payload should make it possible to:
- identify which survey was answered
- identify which question each answer belongs to
- identify which option was selected when relevant
- preserve free-text child input answers
- support analytics and later positioning
- support one-page-one-question or full-page rendering without changing the payload model

## Submission model
Use a single top-level payload object.

Default shape:

{
  "surveyId": "survey_xxx",
  "submittedAt": 1776742800000,
  "extra": {},
  "answers": [ ... ]
}

## Top-level fields

### `surveyId`
- Type: `string`
- Meaning: unique id of the survey
- Source: schema `survey.id`
- Required: yes

### `submittedAt`
- Type: `integer`
- Meaning: Unix timestamp in milliseconds for when the submission happened
- Required: yes
- Note: generated at submit time

### `answers`
- Type: `array`
- Meaning: collection of question answers
- Required: yes
- Rule: one answer object per question

## Answer object shape
Each item inside `answers` should use this base structure:

{
  "questionId": "question_xxx",
  "questionType": "radio",
  "value": ...
}

## Common answer fields

### `questionId`
- Type: `string`
- Meaning: unique id of the question from schema
- Required: yes

### `questionType`
- Type: `string`
- Allowed values: `radio`, `checkbox`, `input`, `score`, `nps`
- Required: yes

### `value`
- Meaning: answer value payload
- Type depends on question type
- Required: yes for answered questions
- Optional omission rule: if the question is not required and left blank, it may be omitted or included as empty depending on product needs
- Current default: unanswered questions do not appear in `answers`; required questions must be answered before final submit

## Type-specific answer formats

### Radio answer
Use this shape:

{
  "questionId": "question_xxx",
  "questionType": "radio",
  "value": {
    "optionId": "option_xxx",
    "child": [
      {
        "childId": "child_xxx",
        "dataType": "text",
        "value": "补充输入"
      }
    ]
  }
}

#### Radio rules
- `optionId` is required when the question is answered
- `child` is optional
- `child` should be treated as a list of child answer objects because one option may contain one or multiple child fields
- include `child` only if the selected option contains child input(s) and those child fields should be serialized
- each child answer object should preserve `childId`, `dataType` when available, and `value`
- if the child node includes its own `attribute` configuration, respect that configuration fully when rendering, validating, or serializing child input content

### Checkbox answer
Use this shape:

{
  "questionId": "question_xxx",
  "questionType": "checkbox",
  "value": [
    {
      "optionId": "option_xxx",
      "child": [
        {
          "childId": "child_xxx",
          "dataType": "text",
          "value": "补充输入"
        }
      ]
    },
    {
      "optionId": "option_yyy"
    }
  ]
}

#### Checkbox rules
- `value` is an array because multiple options may be selected
- each selected option becomes one object in the array
- `child` is optional per option
- `child` should be treated as a list of child answer objects because one option may contain one or multiple child fields
- include `child` only when that selected option has child input(s) that should be serialized
- each child answer object should preserve `childId`, `dataType` when available, and `value`
- if the child node includes its own `attribute` configuration, respect that configuration fully when rendering, validating, or serializing child input content

### Input answer
Use this shape:

{
  "questionId": "question_xxx",
  "questionType": "input",
  "value": [
    {
      "optionId": "option_xxx",
      "dataType": "text",
      "value": "用户输入内容"
    },
    {
      "optionId": "option_yyy",
      "dataType": "dateRange",
      "value": {
        "start": "2026-04-21",
        "end": "2026-04-28"
      }
    }
  ]
}

#### Input rules
- `value` is an array because one input question may define one or multiple input fields inside `option[]`
- keep `optionId` because the schema defines each concrete input field inside `option[]`
- each answered input field should serialize as one item in the array
- each item should preserve:
  - `optionId`
  - `dataType`
  - `value`
- scalar-like data types such as `text`, `email`, `tel`, `number`, `date`, `time`, `dateTime` should serialize `value` as a string
- range-like data types such as `dateRange`, `timeRange`, `dateTimeRange` should serialize `value` as:

{
  "start": "...",
  "end": "..."
}

- input control rendering and validation should follow `option[].attribute.dataType` and related constraints
- unanswered optional input fields should not be included in the input question's `value` array
- if no input field in the question is answered, the whole question should be omitted from `answers`

### Score answer
Use this shape:

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

#### Score rules
- `value` is an array because one score question may contain multiple score rows inside `option[]`
- every answered score row becomes one item in the array
- each item should preserve:
  - `optionId`
  - `score`
- `score` may be integer or decimal, depending on `step`
- if `required=true`, every score row in this question should be answered before final submit


### NPS answer
Use this shape:

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

#### NPS rules
- `value` is an object because one NPS question normally has one scale configuration.
- Preserve `optionId` from `nps.option[0].id` for analytics and positioning.
- `score` must be an integer inside `option[].attribute.scope`, normally `0` through `10`.
- `scoreDesc` is display metadata and is not required in the submitted payload.

## Recommended HTML serialization strategy
In generated HTML:
- keep `surveyId` available at form level
- preserve `questionId` on each question container using `data-question-id`
- preserve `questionType` using `data-question-type`
- preserve `optionId` on each selectable control using `value` or `data-option-id`
- preserve child input ids using `data-child-id`
- preserve input field option ids on rendered input controls using `data-option-id`
- on submit, assemble the payload into the default shape above

## Validation rules before submit
- required questions must have an answer
- if a selected option includes a visible child input that is intended to be filled, capture that child value
- if `onePageOneQuestion === true`, step validation may happen per screen, but the final payload shape remains the same
- if `onePageOneQuestion === true`, keep temporary local step cache in `localStorage` between screens
- if `allowBack === true`, moving backward must not lose already entered answers
- unanswered questions must not be serialized into `answers`

## Omitted fields by default
The default contract does **not** require these fields yet:
- respondent id
- device id
- page path
- session id
- draft id
- score
- nps
- analytics event stream

These can be added later if the user asks.

## HTML implementation guidance
Until a specific backend API is provided:
- intercept form submit with lightweight JS
- assemble the payload object in browser memory
- in `onePageOneQuestion` mode, cache step answers in `localStorage` between screens, following `references/local-cache-rules.md`
- on submit, `console.log` the final payload by default
- after successful submit, clear the survey cache from `localStorage`
- do not invent a production API contract yet

## Executable validation guidance
When possible, validate generated payload examples and runtime payload snapshots with:

```bash
python3 <survey-creator-root>/validators/validate_survey_payload.py /absolute/path/to/payload.json
```

Use this as the machine-enforced contract check after schema validation.
