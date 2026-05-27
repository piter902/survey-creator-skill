# Logic rules

`survey-creator-skill` now supports a top-level `logic` array for conditional questionnaire behavior.

## Top-level shape

```json
{
  "survey": { ... },
  "questions": [ ... ],
  "finish": [ { ... } ],
  "logic": [ ... ]
}
```

## Rule shape

```json
{
  "id": "logic-rule-id",
  "when": {
    "questionId": "source-question-id",
    "operator": "selected",
    "optionId": "option-id"
  },
  "action": {
    "type": "show_question",
    "targetQuestionId": "target-question-id"
  }
}
```

## `when` fields

### `when.questionId`
- Source question id
- The logic condition reads the current answer of this question

### `when.operator`
Supported operators:
- `selected`
- `not_selected`
- `contains`
- `not_contains`
- `exists`
- `not_exists`
- `answered`
- `not_answered`
- `eq`
- `neq`
- `gt`
- `lt`

### `when.optionId`
Used by:
- `selected`
- `not_selected`
- optionally `contains` / `not_contains`

### `when.optionIds`
Used by:
- `exists`
- `not_exists`

Meaning:
- whether the user's selected option set intersects with the provided option ids

### `when.value`
Used by:
- `contains`
- `not_contains`
- `eq`
- `neq`
- `gt`
- `lt`

Meaning:
- compare against text / scalar values extracted from the source answer

## `action` fields

### `action.type`
Supported actions:
- `show_question`
- `hide_question`
- `show_option`
- `hide_option`
- `auto_select_option`
- `jump_to_question`
- `jump_to_page`
- `end_survey`

### `action.targetQuestionId`
Required for:
- `show_question`
- `hide_question`
- `jump_to_question`
- `jump_to_page`
- `show_option`
- `hide_option`
- `auto_select_option`

Optional for:
- `end_survey`

When `action.type === "end_survey"` and `targetQuestionId` is provided, it must point to a `finish[].id`.
If omitted, the runtime uses the first finish node.

### `action.targetOptionId`
Required for:
- `show_option`
- `hide_option`
- `auto_select_option`

## Default visibility semantics

To make `show_question` / `show_option` useful without adding extra hidden flags:
- a question targeted by any `show_question` rule is treated as hidden by default until one matching rule becomes true
- an option targeted by any `show_option` rule is treated as hidden by default until one matching rule becomes true
- `hide_question` / `hide_option` work from the normal visible state

## Runtime behavior rules

### Conflict resolution
- `logic` rules are evaluated in array order from top to bottom.
- If multiple matched rules target the same question / option / jump source, the later matched rule wins.
- This means conflicts should be resolved by declaration order:
  - `hide_question` followed by `show_question` for the same `targetQuestionId` leaves the question visible.
  - `show_question` followed by `hide_question` for the same `targetQuestionId` leaves the question hidden.
  - `hide_option` followed by `show_option` for the same `targetQuestionId + targetOptionId` leaves the option visible.
  - `show_option` followed by `hide_option` for the same `targetQuestionId + targetOptionId` leaves the option hidden.
  - multiple `jump_to_question` / `jump_to_page` / `end_survey` rules from the same source question use the last matched jump target.
- `auto_select_option` runs after final visibility is computed. If the target question or option is hidden / skipped after conflict resolution, auto-select is ignored.

### Hidden question behavior
- hidden questions do not participate in validation
- hidden questions do not appear in payload answers
- if a question becomes hidden, its cached answer should be removed

### Hidden option behavior
- hidden options are not selectable
- if a selected option becomes hidden, the selection should be cleared
- hidden input fields / score rows should not be validated or submitted

### Auto select behavior
- `auto_select_option` only targets `radio` or `checkbox`
- if the target option is visible and its rule is true, the runtime may auto-check it

### Navigation behavior
- `jump_to_question` is evaluated during step navigation
- `jump_to_page` is evaluated during step navigation and jumps to the page containing `action.targetQuestionId`
- when every question is already its own page, `jump_to_page` behaves the same as `jump_to_question`
- `end_survey` jumps directly to the finish screen in step mode

## Recommended usage patterns

### Show a follow-up question when a certain option is selected
```json
{
  "id": "logic_show_budget",
  "when": {
    "questionId": "question_need_demo",
    "operator": "selected",
    "optionId": "option_need_demo_yes"
  },
  "action": {
    "type": "show_question",
    "targetQuestionId": "question_budget"
  }
}
```

### Hide an option when a certain answer exists
```json
{
  "id": "logic_hide_none",
  "when": {
    "questionId": "question_problem_tags",
    "operator": "answered"
  },
  "action": {
    "type": "hide_option",
    "targetQuestionId": "question_problem_tags",
    "targetOptionId": "option_problem_none"
  }
}
```

### End the survey early
```json
{
  "id": "logic_end_early",
  "when": {
    "questionId": "question_need_tool",
    "operator": "selected",
    "optionId": "option_need_tool_no"
  },
  "action": {
    "type": "end_survey"
  }
}
```

### Route different users to different finish pages
```json
{
  "id": "logic_end_to_negative_finish",
  "when": {
    "questionId": "question_satisfaction",
    "operator": "selected",
    "optionId": "option_not_satisfied"
  },
  "action": {
    "type": "end_survey",
    "targetQuestionId": "finish_negative_followup"
  }
}
```

## Multi-finish best practices

- Keep `finish[0]` as the default finish for users who do not hit any special branch.
- Use additional finish nodes only when the final tone or next-step guidance truly differs.
- Typical finish splits:
  - positive / promoter → thanks and referral-style copy
  - neutral → standard completion copy
  - negative / complaint → apology, comfort, and follow-up expectations
- When a branch still needs more information, do **not** end immediately:
  - first `show_question` for the follow-up fields
  - then trigger `end_survey` from the final branch question
- Recommended naming:
  - `finish_default`
  - `finish_positive`
  - `finish_negative`
  - `finish_followup_required`

## Validation notes
- all referenced source / target question ids must exist
- all referenced target option ids must exist under the target question
- when `end_survey.targetQuestionId` is present, it must reference an existing `finish[].id`
- `auto_select_option` may only target `radio` or `checkbox`
- duplicate logic rule ids are forbidden when ids are provided
