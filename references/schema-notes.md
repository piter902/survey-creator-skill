# Survey schema notes

These notes summarize the JSON reference files copied from the admin designer materials, plus the clarified field semantics provided later in the skill design process.

## Supported node types
- `survey`: welcome/introduction page
- `radio`: single-choice question
- `checkbox`: multiple-choice question
- `input`: free-text input question
- `finish`: ending/completion page
- `score`: rating / score question
- `nps`: Net Promoter Score / recommendation-intent question
- `Pagination`: manual page separator node (layout-only, no answer)

## Global field rules
1. **`title` and `description` are both string fields that support rich text.**
   - In HTML rendering, treat them as rich-text content rather than plain text-only labels.
2. **All ids must be unique within a single questionnaire.**
   - This includes survey ids, question ids, option ids, and child input ids.
   - Their purpose is not only rendering, but also downstream positioning and analytics.
   - These ids should be materialized when schema is generated, not created dynamically at browser runtime.
3. **`attribute.required` means whether the field is required.**
   - `true` = required
   - `false` = optional
4. **`attribute.media` represents media resources.**
   - Supported media types: image, audio, video
   - Resource values may be URL links or base64 data
5. **For selection questions, `attribute.random` means whether options should be randomized.**
   - `true` = randomize option order
6. **`option` is the collection of options.**
   - If a single option has `child`, that means one or more extra fill-in fields should appear after that option.
   - child fields should be rendered according to their own `attribute.dataType` when present.
7. **Selection options may also carry an option-level `random` flag.**
   - If `option.attribute.random === false`, that option must stay fixed in place even when the question-level `attribute.random === true`.
   - In other words, question-level randomization must not move options explicitly marked as non-randomizable.
8. **For input questions, the option-level `attribute` meaning follows the dedicated input reference and JSON example.**
   - `dataType` should affect both control type and validation behavior.
   - Allowed input/child `dataType` values: `email`, `tel`, `number`, `text`, `date`, `time`, `dateTime`, `dateRange`, `timeRange`, `dateTimeRange`.
   - Unknown values should fall back to `text`.
9. **`survey.attribute.onePageOneQuestion` means one question per page.**
   - This affects rendering and page-flow behavior.
10. **Rich-text fields support normal HTML elements.**
   - Render them as normal HTML-rich content.
11. **`survey.attribute.allowBack` means whether previous-page navigation is supported.**
   - `true` = support previous page
   - `false` = do not support previous page
12. **`Pagination` node is layout-only and does not produce answer data.**
   - Shape is fixed as:
     ```json
     { "type": "Pagination", "id": "page-id" }
     ```
   - It must not contain title/description/attribute/option.
   - It is valid only inside `questions[]`.
   - It is mutually exclusive with `survey.attribute.onePageOneQuestion === true`.

## Important quirks
1. `radio`, `checkbox`, `input`, `score`, `nps`, and `survey` all use `attribute`
2. Checkbox option interaction fields have different semantics.
   - `exclusive: true` means this option excludes all other options in the same checkbox question
   - `mutual-exclusion: true` means this option only excludes other options that also have `mutual-exclusion: true`
3. `finish` is canonically an array of one or more finish nodes.
   - The legacy single-object shape may still be normalized for compatibility, but new schemas should always use an array.
   - This is what enables future logic rules to target different ending pages.
4. Media blocks are optional unless the prompt or scenario requires them.
5. `Pagination` separators can be used to manually group multiple questions into one step only when `onePageOneQuestion === false`.
   - Consecutive or leading/trailing separators are allowed but usually redundant.
   - If `onePageOneQuestion === true`, every answerable question is already its own page, so `Pagination` must be rejected by validation.

## Recommended full-survey output shape
Use one top-level object like this internally:

{
  "survey": { ... },
  "questions": [ ... ],
  "finish": [ { ... } ]
}

## Option children
`radio` and `checkbox` options may include `child` items of `type: "input"`.
Use them only when the prompt implies “Other, please specify”, follow-up text, or conditional free text.

6. **NPS questions support media at two levels.**
   - `nps.attribute.media` attaches media to the whole NPS question.
   - `nps.option[].attribute.media` attaches media to the NPS scale context.
   - `nps.option[].attribute.scoreDesc` uses range keys such as `0-6`, `7-8`, `9-10`.


## Logic rules
12. A full survey may include a top-level `logic` array.
13. Each logic rule contains `when` and `action`.
14. Source questions are referenced by `when.questionId`.
15. Supported operators are: `selected`, `not_selected`, `contains`, `not_contains`, `exists`, `not_exists`, `answered`, `not_answered`, `eq`, `neq`, `gt`, `lt`.
16. Supported action types are: `show_question`, `hide_question`, `show_option`, `hide_option`, `auto_select_option`, `jump_to_question`, `jump_to_page`, `end_survey`.
17. Questions or options targeted by `show_*` rules are treated as hidden by default until a matching rule becomes true.
18. Hidden questions/options should not be validated or submitted.
