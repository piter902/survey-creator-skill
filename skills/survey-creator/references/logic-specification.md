# Final logic specification

This document is the consolidated runtime specification for `survey-creator-skill` logic behavior.

Use this as the final source of truth when designing, validating, repairing, or reviewing logic-enabled surveys.

---

## 1. Evaluation model

- `logic` is a top-level array.
- Rules are evaluated in array order, from top to bottom.
- A rule only participates when:
  - `when` is valid
  - `action` is valid
  - the condition evaluates to `true`

Logic is recomputed from current answers during runtime interaction.

---

## 2. Supported condition operators

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

### Operator semantics

#### `selected`
True when the source answer selected the given `optionId`.

#### `not_selected`
True when the source answer did not select the given `optionId`.

#### `contains`
True when:
- a selected option set contains `when.optionId`, or
- a scalar/text answer contains `when.value`

#### `not_contains`
True when:
- a selected option set does not contain `when.optionId`, or
- a scalar/text answer does not contain `when.value`

#### `exists`
True when the current selected option set intersects with `when.optionIds`.

#### `not_exists`
True when the current selected option set has no intersection with `when.optionIds`.

#### `answered`
True when the source question currently has an answer.

#### `not_answered`
True when the source question currently has no answer.

#### `eq`
True when any scalar answer value equals `when.value`.

#### `neq`
True when the source question is answered and every scalar value is not equal to `when.value`.

#### `gt`
True when any scalar answer value is numerically greater than `when.value`.

#### `lt`
True when any scalar answer value is numerically less than `when.value`.

---

## 3. Supported actions

- `show_question`
- `hide_question`
- `show_option`
- `hide_option`
- `auto_select_option`
- `jump_to_question`
- `jump_to_page`
- `end_survey`

---

## 4. Default visibility model

### Questions
- If a question is targeted by any `show_question` rule, it is hidden by default.
- It becomes visible only when at least one matching `show_question` rule makes it visible after conflict resolution.

### Options
- If an option is targeted by any `show_option` rule, it is hidden by default.
- It becomes visible only when at least one matching `show_option` rule makes it visible after conflict resolution.

### Hide rules
- `hide_question` and `hide_option` work from the normal visible state.

---

## 5. Conflict resolution

When multiple matched rules target the same subject, **the later matched rule wins**.

This applies to:
- question visibility
- option visibility
- jump destinations

### Examples

#### Question conflict
- `hide_question(question_x)`
- later `show_question(question_x)`
- final result: `question_x` is visible

#### Option conflict
- `show_option(question_y, option_a)`
- later `hide_option(question_y, option_a)`
- final result: `option_a` is hidden

#### Jump conflict
- `jump_to_page(question_target)`
- later `end_survey`
- final result: jump goes to finish

---

## 6. Runtime order of effects

At runtime, the effective behavior is:

1. compute matched rules
2. resolve visibility conflicts in declaration order
3. resolve jump conflicts in declaration order
4. derive skipped questions from the final jump target
5. treat hidden or skipped questions as unavailable
6. clear unavailable question cache and DOM state
7. clear hidden option state
8. apply auto-select on the final visible state only

---

## 7. Unavailable question semantics

A question is **unavailable** when:
- it is hidden by logic, or
- it is skipped by jump logic

In both cases, the question is treated as if it does not exist.

### Consequences
- unavailable questions do not block validation
- unavailable questions are omitted from payload
- unavailable questions are removed from local cache
- unavailable questions are removed from visible step flow

This is the core rule:

> hidden = nonexistent  
> skipped = nonexistent

---

## 8. Required exemption

If a question is hidden or skipped:
- `required` is automatically exempted
- the question must not block next step or submit

This applies equally to:
- `hide_question`
- `jump_to_question`
- `jump_to_page`
- `end_survey`

---

## 9. Hidden option semantics

If an option becomes hidden:
- it is no longer selectable
- if it had been selected before, that selection must be cleared
- child input under that option must be cleared
- hidden score/nps rows must not be validated or submitted

---

## 10. Auto-select semantics

`auto_select_option` runs only after final visibility is resolved.

Therefore:
- if the target question is unavailable, auto-select is ignored
- if the target option is hidden, auto-select is ignored
- if the target option is visible, it may be auto-selected

For radio:
- selecting one auto-selected option clears the others

For checkbox:
- the option is added only if it is currently visible

---

## 11. Jump semantics

### `jump_to_question`
- jumps to the target question screen in step mode

### `jump_to_page`
- jumps to the page containing `targetQuestionId`
- if one-page-one-question is enabled, it behaves like `jump_to_question`

### `end_survey`
- jumps directly to a finish screen
- if `action.targetQuestionId` points to a `finish[].id`, that specific finish screen becomes the destination
- otherwise the first finish screen is used
- all later questions are considered skipped

### Final jump rule
- if multiple jump actions match from the same source path, the last matched jump wins

---

## 12. Pagination interaction

- `Pagination` is only meaningful when `survey.attribute.onePageOneQuestion !== true`
- when `onePageOneQuestion === true`, `Pagination` is invalid and must be rejected by validation

---

## 13. Cache behavior

The local cache must reflect the effective logic state.

### Required behaviors
- answered visible questions can be cached
- once a question becomes unavailable, its cache entry must be removed
- once a hidden option becomes unavailable, its option-level value must be removed
- after successful submit, survey cache must be cleared

---

## 14. Payload behavior

The final payload must only include effective answers.

Therefore:
- hidden questions are omitted
- skipped questions are omitted
- hidden options are omitted
- cleared child answers are omitted

---

## 15. Safety interpretation

When evaluating whether a logic-enabled survey is safe to ship, the minimum guarantees are:

- invalid rule references are blocked by schema validation
- unsupported operators/actions are blocked by schema validation
- unavailable questions never block required validation
- unavailable questions never leak into payload
- later matched conflicting rules override earlier ones
- auto-select cannot resurrect hidden targets

If any of those guarantees fail, the survey is not ship-ready.
