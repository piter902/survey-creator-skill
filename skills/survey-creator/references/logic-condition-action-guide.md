# Logic condition and action guide

This document explains the practical meaning of every supported logic condition (`when.operator`) and logic result (`action.type`) in `survey-creator-skill`.

It is intended for users who understand that the skill supports logic, but need a clearer explanation of:

- what each condition means
- which question types it applies to
- what each action actually does at runtime
- what happens to hidden / skipped / unavailable questions

---

## 1. Logic condition operators

### `selected`
Meaning:
- the specified `optionId` is selected in the source question

Typical source question types:
- `radio`
- `checkbox`

Typical usage:
- selected “yes” → show follow-up question
- selected a route option → jump to a page
- selected a mode → auto-select a recommended option later

---

### `not_selected`
Meaning:
- the specified `optionId` is not selected in the source question

Typical source question types:
- `radio`
- `checkbox`

Typical usage:
- if user did not select a certain option, hide a branch
- if user did not choose “yes”, do not display advanced questions

---

### `contains`
Meaning:
- for selection questions: the current answer contains the specified `optionId`
- for text/scalar answers: the answer contains the specified `value`

Typical usage:
- selected set contains a specific feature option
- text feedback contains a keyword like “price” or “bug”

---

### `not_contains`
Meaning:
- for selection questions: the current answer does not contain the specified `optionId`
- for text/scalar answers: the answer does not contain the specified `value`

Typical usage:
- text does not contain “do not contact me” → show contact permission question
- selection does not contain a given option → keep some branch hidden

---

### `exists`
Meaning:
- the selected option set intersects with the specified `optionIds`

Typical source question types:
- `checkbox`
- sometimes `radio` if treated as a one-item selected set

Typical usage:
- if the user selected any option in a category, show a follow-up block

---

### `not_exists`
Meaning:
- the selected option set has no intersection with the specified `optionIds`

Typical usage:
- if user selected none of a target option group, keep related questions hidden

---

### `answered`
Meaning:
- the source question has been answered, regardless of exact answer value

Typical source question types:
- all supported question types

Typical usage:
- once the respondent answered a gating question, reveal next step
- use as a generic branch condition independent of exact content

---

### `not_answered`
Meaning:
- the source question has not been answered

Typical usage:
- if the source question is still empty, keep later steps hidden
- show a fallback state only before the source question is filled

---

### `eq`
Meaning:
- at least one scalar answer value equals `when.value`

Typical source question types:
- `input`
- `score`
- `nps`
- any source that yields a scalar-like value

Typical usage:
- code field equals `VIP`
- score exactly equals a threshold value

---

### `neq`
Meaning:
- the source question is answered and every scalar value is not equal to `when.value`

Typical usage:
- user entered something, but it is not a privileged or special code

---

### `gt`
Meaning:
- at least one scalar answer value is numerically greater than `when.value`

Typical usage:
- budget > threshold
- age > threshold
- score/NPS > threshold

---

### `lt`
Meaning:
- at least one scalar answer value is numerically less than `when.value`

Typical usage:
- NPS below threshold → show recovery question
- budget below threshold → jump to lightweight plan page

---

## 2. Logic result actions

### `show_question`
Meaning:
- make the target question visible

Runtime model:
- if any `show_question` rule targets a question, that question becomes hidden by default
- it becomes visible only when a matching `show_question` rule wins after conflict resolution

Typical usage:
- show a follow-up question only for matched respondents

---

### `hide_question`
Meaning:
- hide the target question

Runtime consequences:
- hidden question is treated as unavailable
- unavailable question is treated as if it does not exist
- required is automatically exempted
- hidden question is omitted from payload
- hidden question local cache should be cleared

Typical usage:
- hide irrelevant questions in a fast path

---

### `show_option`
Meaning:
- make the target option visible inside a target question

Runtime model:
- if any `show_option` rule targets an option, that option becomes hidden by default
- it becomes visible only when a matching `show_option` rule wins after conflict resolution

Typical usage:
- reveal a premium or advanced option only for matched users

---

### `hide_option`
Meaning:
- hide the target option inside a target question

Runtime consequences:
- hidden option can no longer be selected
- if it had already been selected, that selection is cleared
- child inputs under that option are cleared as well
- hidden option data must not be submitted in payload

Typical usage:
- remove incompatible or irrelevant options based on earlier answers

---

### `auto_select_option`
Meaning:
- automatically select the target option

Runtime consequences:
- runs only after final visibility is resolved
- ignored if the target question is unavailable
- ignored if the target option is hidden
- for radio: selecting one option clears others
- for checkbox: the visible target option is added to the current selection

Typical usage:
- recommend AI mode after a user selects an AI-heavy workflow path

---

### `jump_to_question`
Meaning:
- jump directly to the screen containing `targetQuestionId`

Runtime consequences:
- skipped questions are treated as unavailable
- unavailable questions are exempt from required validation
- unavailable questions are omitted from payload and removed from cache

Typical usage:
- skip intermediate questions and go to a relevant target question

---

### `jump_to_page`
Meaning:
- jump to the page that contains `targetQuestionId`

Typical prerequisites:
- manual pagination via `Pagination`
- `survey.attribute.onePageOneQuestion === false`

Runtime consequences:
- all skipped questions/pages are treated as unavailable
- required is automatically exempted for skipped questions
- skipped question answers must not remain in payload or cache

Typical usage:
- fast-path respondents directly to a summary or target page

---

### `end_survey`
Meaning:
- terminate the questionnaire early and move to the finish state

Runtime consequences:
- all later questions become unavailable
- required is automatically exempted for skipped questions
- later questions must not appear in payload
- later cached answers should be cleared

Typical usage:
- disqualify a respondent early
- close the flow when a hard-stop condition is met

---

## 3. Conflict resolution rule

Current rule:
- when multiple matched rules target the same subject, **the later matched rule wins**

This applies to:
- question visibility
- option visibility
- jump results

Examples:
- `hide_question(question_x)` then later `show_question(question_x)` → final result: visible
- `show_option(option_a)` then later `hide_option(option_a)` → final result: hidden
- `jump_to_page(...)` then later `end_survey` → final result: end survey

---

## 4. Unavailable question semantics

A question is unavailable when:
- it is hidden by logic, or
- it is skipped by jump logic

Core rule:
- hidden = nonexistent
- skipped = nonexistent

That means:
- unavailable questions do not block validation
- unavailable questions do not appear in payload
- unavailable questions should be removed from cache
- unavailable questions should disappear from visible step flow

---

## 5. Recommended condition → action combinations

Most stable combinations:
- `selected` → `show_question`
- `selected` → `hide_option`
- `selected` → `auto_select_option`
- `selected` → `jump_to_page`
- `answered` → `show_question`
- `contains` → `show_question`
- `gt` / `lt` → `show_question`
- `selected` → `end_survey`

Use with extra care:
- `not_answered` → `jump_to_question`
- `not_selected` → `end_survey`
- `neq` on loosely controlled text fields

Those combinations may be legal, but are more likely to confuse respondents if overused.

---

## 6. Best practice for users of the skill

When prompting the skill to generate logic, describe the intent in plain language first, for example:

- “If user selects ‘yes’, show a follow-up question.”
- “If user has not used AI before, jump directly to the summary page.”
- “If the answer mentions price, reveal a pricing-related question.”
- “If NPS is below 7, ask why they would not recommend it.”

The skill can then translate that intent into supported `when.operator` and `action.type` structures.
