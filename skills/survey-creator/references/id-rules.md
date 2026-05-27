# ID rules

Schema ids use two levels of uniqueness:

- `survey.id` must be a **global long snowflake id**
- all other ids use **type prefix + 6-digit local snowflake-style numeric suffix**

## Canonical format

For non-survey nodes, use:

```text
<prefix>-<6 digits>
```

Examples:

- `radio-234567`
- `checkbox-345678`
- `input-456789`
- `score-567890`
- `nps-678901`
- `finish-789012`
- `pagination-890123`

For `survey.id`, use a longer global id such as:

- `survey-190238471928`
- `survey-190238471929`

## Prefix rules

- `survey` node id → `survey-<long snowflake>`
- `radio` question id → `radio-xxxxxx`
- `checkbox` question id → `checkbox-xxxxxx`
- `input` question id → `input-xxxxxx`
- `score` question id → `score-xxxxxx`
- `nps` question id → `nps-xxxxxx`
- `finish` node id → `finish-xxxxxx`
- `Pagination` node id → `pagination-xxxxxx`

## Option id rules

Option ids should follow the **parent question type prefix**:

- radio option id → `radio-xxxxxx`
- checkbox option id → `checkbox-xxxxxx`
- input option id → `input-xxxxxx`
- score option id → `score-xxxxxx`
- nps option id → `nps-xxxxxx`

## Child input id rules

Child follow-up inputs are input-like nodes, so use:

- child input id → `input-xxxxxx`

## Generation rules

- ids must be generated **during schema creation time**, never at browser runtime
- `survey.id` should come from a **global long snowflake generator**
- all non-survey ids should use a **6-digit snowflake-style time-ordered suffix**
- ids must be unique within the whole survey
- ids must stay stable after the final HTML is delivered

## Uniqueness rules

- `survey.id` must be globally unique across all questionnaires
- question / option / child / finish / pagination ids must be unique inside the current survey
- for analytics, storage, and submission processing, treat non-survey ids as **jointly unique with `survey.id`**

## Forbidden patterns

Do not use:

- `survey-id`
- `question-id`
- `option-id`
- `finish_complete_default`
- `question_followup`
- `q-1`
- `opt-1`

These are useful during drafting, but not allowed in final schema output.
