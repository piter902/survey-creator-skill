# Pagination rules

## `survey.attribute.onePageOneQuestion`
Meaning:
- `true` = the HTML should display only one screen at a time
- `false` or omitted = the HTML may display multiple sections on the same page

## Step breakdown when `onePageOneQuestion === true`
The questionnaire should be split into independent screens in this order:
1. survey intro screen
2. question screens (either one-question-per-screen or manual grouped pages)
3. finish screen

That means:
- the survey introduction is displayed alone
- every question is displayed alone
- the finish section is displayed alone

## Manual page grouping with `Pagination` node
When `questions[]` contains nodes like:

```json
{ "type": "Pagination", "id": "page-id" }
```

the renderer should treat them as **page separators**:
- content before a separator belongs to the current page
- content after a separator starts a new page
- separator nodes are layout-only and never rendered as question UI
- separator nodes are never validated as answers and never submitted in payload

## Mutual exclusion with `onePageOneQuestion`
`Pagination` and `survey.attribute.onePageOneQuestion === true` are mutually exclusive:
- `onePageOneQuestion: true` means the whole questionnaire is already one question per page.
- In that mode, a manual `Pagination` separator has no valid meaning.
- Schema validation must reject any `questions[]` that contains `Pagination` while `onePageOneQuestion` is `true`.
- To manually group multiple questions into pages, set `onePageOneQuestion` to `false` and insert `Pagination` separators between groups.

## `survey.attribute.allowBack`
Meaning:
- `true` = the respondent may navigate back to the previous screen
- `false` = no previous-step navigation should be offered

## Rendering implications
When `onePageOneQuestion === true`:
- use a step-based HTML flow
- only one step is visible at a time
- navigation controls should move the respondent between steps
- submit should occur on the finish screen or final submission step
- do not include `Pagination` nodes

When `allowBack === true`:
- include a visible previous-step control where appropriate

When `allowBack === false`:
- do not render a previous-step action
- forward-only progression is allowed

## UX guidance
- the intro screen should usually lead into the first question
- the finish screen should sit immediately before or around final submit behavior
- if required validation is implemented, block forward progression when the current step is invalid
