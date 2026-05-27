# Local cache rules

This document defines the default local caching strategy for `survey-creator-skill` when `survey.attribute.onePageOneQuestion === true`.

## Cache purpose
Local cache exists to:
- preserve step answers while navigating between screens
- support previous-page navigation without data loss
- keep the submission payload stable even when questions are rendered one at a time

## Default storage mechanism
Use `localStorage`.

## Cache key rule
Use a per-survey key in this format:

`survey_step_cache_${surveyId}`

Example:

`survey_step_cache_survey_9f3k2m8x`

## Cache value shape
Store a JSON string representing in-progress answers.
A recommended default shape is:

{
  "surveyId": "survey_xxx",
  "updatedAt": "2026-04-20T17:00:00.000Z",
  "answers": {
    "question_xxx": {
      "questionType": "radio",
      "value": { ... }
    }
  }
}

## Cache behavior

### On step change
- update local cache after the current step is completed or changed
- keep previously answered step data intact

### On previous-page navigation
- read existing cached values and repopulate the previous step
- do not drop answers when navigating backward

### On page reload
- if local cache exists for the current survey, repopulate the form from cache by default

### On final submit
- assemble the final submission payload from the current form state and/or cached data
- `console.log` the final payload by default
- if submission is considered successful, clear the local cache for this survey immediately after submit

## Clear rule
On successful submit, remove the survey cache key from `localStorage`.

Example:
- remove `survey_step_cache_${surveyId}`

## Safety rule
- never let one survey reuse another survey's cache key
- always scope cache by `surveyId`
