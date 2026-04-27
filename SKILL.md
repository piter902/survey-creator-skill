---
name: survey-creator-skill
description: Create schema-validated HTML survey pages from natural-language requirements using the admin designer references. Use this skill whenever the user asks to create, design, prototype, render, or generate a survey/questionnaire HTML page, especially when they want free-form UI style but need the question structure constrained by a reference schema. Be proactive about using it for survey creation, registration forms, feedback forms, AI Native questionnaire pages, and similar structured form UIs.
---

# Survey Creator

Generate **HTML survey pages only**.

The workflow is:
1. understand the user's intent
2. analyze the prompt and infer the survey structure
3. generate a schema draft from `references/`
4. validate that schema against the reference formats and field rules
5. render a submittable HTML page from the validated schema
6. verify the HTML does not blank-screen in desktop and mobile browser runtimes
7. verify basic accessibility and form semantics
8. make the generated submit payload conform to the submission contract
9. validate the submit payload against the concrete schema so every questionId / optionId / childId / score belongs to that exact survey

Do **not** return raw JSON schema by default.
Use the schema as an internal generation artifact unless the user explicitly asks to inspect it.

## Load these references first
Before generating output, read only the files you need from:
- `references/schema-notes.md`
- `references/field-guide-overview.md`
- `references/survey-welcom.json`
- `references/survey-fields.md`
- `references/question-radio.json`
- `references/radio-fields.md`
- `references/question-checkbox.json`
- `references/checkbox-fields.md`
- `references/question-input.json`
- `references/input-fields.md`
- `references/question-score.json`
- `references/score-fields.md`
- `references/question-nps.json`
- `references/nps-fields.md`
- `references/question-finish.json`
- `references/finish-fields.md`
- `references/rich-text-rules.md`
- `references/pagination-rules.md`
- `references/submission-contract.md`
- `references/child-input-rules.md`
- `references/local-cache-rules.md`
- `references/logic-rules.md`
- `references/logic-specification.md`
- `references/logic-example-library.md`
- `references/toc-survey-ui-rules.md`
- `references/toc-style-system.md`
- `validators/README.md`
- `validators/validate_reference_consistency.py`
- `validators/validate_survey_schema.py`
- `validators/validate_survey_payload.py`
- `validators/validate_payload_against_schema.py`
- `validators/validate_survey_html_runtime.py`
- `validators/validate_survey_html_interaction_e2e.py`
- `validators/validate_survey_html_accessibility.py`
- `validators/render_survey_html.py`
- `validators/build_validated_survey.py`
- `validators/generate_sample_payload.py`
- `docs/LEGALITY_GUARANTEE.md`
- `docs/LEGALITY_MATRIX.md`
- `tests/contract/README.md`
- `run_all_legality_checks.sh`

Always read `references/schema-notes.md` first, then `references/field-guide-overview.md`, then `references/rich-text-rules.md`, `references/pagination-rules.md`, `references/submission-contract.md`, `references/child-input-rules.md`, `references/local-cache-rules.md`, `references/logic-rules.md`, `references/logic-specification.md`, and `references/logic-example-library.md`, then the specific `*-fields.md` files for every node type you plan to generate or validate. If the user requests a stronger toC visual direction, also read `references/toc-style-system.md` and `references/toc-survey-ui-rules.md`. When schema safety matters, also use `validators/validate_survey_schema.py` as the executable guardrail before rendering HTML.


## Legality engine boundary

Treat this skill as a **schema legality engine** plus fixed HTML renderer. The user and AI may iterate on business semantics, but the skill must enforce protocol legality before delivery.

Read `docs/LEGALITY_GUARANTEE.md` when changing the skill, adding fields, adding question types, or assessing whether generated artifacts are safe to deliver.

When modifying references, validators, payload format, or templates, run:

```bash
python3 <repo-root>/tests/contract/run_contract_tests.py
<repo-root>/validators/run-validator-smoke-tests.sh
```

Only consider the skill healthy when both pass.

## Primary job
Turn a user's high-level request into a **self-contained HTML survey page** that:
- matches the user's scenario and UI style
- uses only schema-supported question structures
- is built from a validated internal schema draft
- supports form submission at the HTML level
- serializes submission data using the default submission contract unless the user overrides it

## Core principle
- **Prompt determines intent and presentation**
- **References determine structure and allowed fields**
- **Validation is mandatory before HTML generation**

This skill should think in two layers:
1. an internal schema layer
2. a rendered HTML layer

The schema layer is not optional. Build it first, validate it, then render.

## Required execution sequence

### Step 1: Understand the user's intent
Read the prompt carefully and identify:
- the survey scenario
- who the respondent is
- likely question count
- whether the page is feedback / registration / research / satisfaction / other
- any explicit UI style directions
- whether the user implies optional conditional inputs such as “其他，请说明”
- whether one-page-one-question flow is implied or should be enabled
- whether previous-page navigation should be available
- whether the UI style implies a known `stylePack`

If the prompt is underspecified, make sensible product decisions instead of stopping.

### Step 1.5: Infer `stylePack`
When the user gives visual direction, infer a renderer `stylePack` before generating HTML.

Use only the generic toC packs:
- `consumer-minimal`
- `consumer-polished`
- `consumer-trust`
- `consumer-editorial`
- `consumer-utility`
- `consumer-campaign`

#### Explicit mapping
- mentions WeChat / 微信 / 小程序 / 表单感 / 轻量填写  
  → `consumer-minimal`
- mentions 更产品化 / 更高级 / 更精致 / 更有设计感  
  → `consumer-polished`
- mentions 满意度 / 购买后反馈 / 产品可信赖 / 售后体验  
  → `consumer-trust`
- mentions 年轻 / 内容感 / 社区感 / lifestyle / 更有氛围  
  → `consumer-editorial`
- mentions 克制 / 干净 / 工具型 / 平台感 / 高效率  
  → `consumer-utility`
- mentions 运营活动 / 活动页 / 更强视觉冲击 / 黑白紫活动风  
  → `consumer-campaign`

#### Implicit mapping
- generic toC without a strong aesthetic signal  
  → default to `consumer-minimal`
- product or purchase feedback  
  → default to `consumer-trust`
- more branded but still general consumer UI  
  → default to `consumer-polished`
- content or lifestyle tone  
  → default to `consumer-editorial`
- platform/tool-like tone  
  → default to `consumer-utility`

Always record this decision mentally and pass it into the renderer or pipeline command via `--style-pack`.

### Step 2: Infer an internal schema draft
Create an internal questionnaire object using both the reference JSON examples and the field-guide markdown files.

Do not rely on JSON shape alone. Use the field guides to understand what each field means, when it is optional, and how it should be rendered.

For a full survey, the internal shape should be:

{
  "survey": { ... },
  "questions": [ ... ],
  "finish": [ { ... } ]
}

This internal schema is the planning source for the HTML.
Do not expose it unless the user asks.

### Step 3: Validate the internal schema
Before rendering HTML, verify all of the following:

#### Structure validation
- top level contains `survey`, `questions`, `finish`
- `questions` is an array
- `finish` is an array of one or more finish objects
- `survey.type === "survey"`
- every `finish[i].type === "finish"`
- every question uses only supported types
- supported types include `radio`, `checkbox`, `input`, `score`, `nps`
- score questions may carry media at both `attribute.media` and `option[].attribute.media`
- nps questions may carry media at both `attribute.media` and `option[].attribute.media`, and use range-based `scoreDesc` keys such as `0-6`

#### Field validation
- `survey`, `radio`, `checkbox`, and `input` use `attribute`
- `title` and `description` are treated as rich-text-capable string fields
- `radio`, `checkbox`, and `input` include `id`, `title`, `description` when appropriate
- `radio` and `checkbox` use `option` arrays
- if a selection question is randomized, check for option-level `option[].attribute.random === false` overrides before shuffling
- `input` uses an `option` array with input metadata in `option[].attribute`
- `input` may contain one or multiple option-defined input fields, so submission must preserve answers per `option[].id` rather than collapsing everything into one string
- conditional free-text is only represented through `child` items of `type: "input"`
- an option may contain one or multiple child items; do not assume only one child field exists
- child items may include their own `attribute` configuration and should be fully respected when present, using the same input-style semantics you already received for child field behavior
- child and input rendering should follow `dataType` when present
- Allowed input/child dataType values are `email`, `tel`, `number`, `text`, `date`, `time`, `dateTime`, `dateRange`, `timeRange`, `dateTimeRange`; unknown values must fall back to `text`
- do not invent unsupported field names

#### Reference conformance validation
- field names must match the reference patterns
- field meanings must remain consistent with the field-guide explanations
- rich-text fields must be treated as normal HTML-capable content
- rich-text fields must be sanitized through a whitelist of display-oriented safe tags before rendering
- pagination-related fields must be interpreted according to the pagination rules
- when `attribute.random === true`, randomized option order should visibly change across reloads or renders, while preserving option ids and submitted values
- option-level random overrides must be respected: if an option has `option.attribute.random === false`, that option must stay fixed even when the question is randomized
- unsupported node types are forbidden unless the user explicitly asks to extend the schema
- checkbox `exclusive` and `mutual-exclusion` have different semantics: `exclusive` clears all other options, while `mutual-exclusion` only clears other mutual-exclusion options
- media is optional unless the prompt requires it

If the inferred schema fails validation, fix it before rendering.
Never render HTML from an invalid schema.

### Step 3.5: Run the executable schema validator
After the manual semantic review above, run the executable validator whenever you have local file access or can materialize the schema temporarily:

```bash
python3 <repo-root>/validators/validate_survey_schema.py /absolute/path/to/schema.json
```

Rules:
- if the validator returns non-zero, the schema must be fixed before HTML generation
- treat unsupported fields as hallucination risk, not as harmless extras
- treat duplicate ids as blocking errors
- treat unsupported `dataType` values as blocking errors
- inspect semantic lint warnings by severity; `high` warnings should normally be resolved before rendering final HTML
- prefer using warning `code`, `suggestion`, and `fixHint` to repair the schema automatically before proceeding
- use `--json` when you need a machine-readable validation report

If you cannot execute the validator in the current environment, you should still follow the same rule set manually and explicitly say that executable validation was not run.

### Step 4: Render HTML from the validated schema
When local scripting is available, prefer using the automated renderer:

```bash
python3 <repo-root>/validators/render_survey_html.py --schema /absolute/path/to/schema.json --out /absolute/path/to/output.html
```

Or use the full automatic pipeline in one command:

```bash
python3 <repo-root>/validators/build_validated_survey.py --schema /absolute/path/to/schema.json --out-html /absolute/path/to/output.html --out-payload /absolute/path/to/output-payload.json
```

When semantic warnings are expected, prefer the repair-enabled pipeline:

```bash
python3 <repo-root>/validators/build_validated_survey.py --schema /absolute/path/to/schema.json --out-schema /absolute/path/to/repaired-schema.json --out-html /absolute/path/to/output.html --out-payload /absolute/path/to/output-payload.json --auto-repair --fail-on-high-warning
```

For skill execution, prefer the single unified entry:

```bash
python3 <repo-root>/validators/run_survey_creator_pipeline.py --schema /absolute/path/to/schema.json --output-dir /absolute/path/to/output-dir --style-pack consumer-trust --auto-repair --fail-on-high-warning
```

Supported `--style-pack` values currently include:
- `consumer-minimal`
- `consumer-polished`
- `consumer-trust`
- `consumer-editorial`
- `consumer-utility`
- `consumer-campaign`

Only return the final HTML to the user after this automated chain succeeds, desktop/mobile E2E viewports pass, `htmlAccessibility.valid === true`, `payloadAgainstSchema.valid === true`, and the pipeline report says `releaseDecision.shipReady === true`.
If the generated HTML fails runtime or E2E checks, run the HTML auto-repair pass before giving up.

### Step 4: Render HTML from the validated schema
Map the validated schema to page structure:
- `survey` → welcome / intro / hero section
- render `title` and `description` using rich-text-capable output
- support only whitelisted display-oriented elements inside rich-text fields
- `radio` → radio group
- `checkbox` → checkbox group
- `input` → text input, textarea, or structured range input block
- `score` → score / rating grid
- `nps` → recommendation score scale
- `finish` → one or more submit / thank-you / final action sections

When multiple finish nodes exist:
- treat `finish[0]` as the default finish
- allow `logic.action.type === "end_survey"` to route to a specific `finish[].id` via `action.targetQuestionId`
- use multiple finish nodes only when the final tone or next-step guidance truly differs between user branches
- when a finish needs a follow-up destination, place it under `finish[].postSubmit`
- `finish[].postSubmit.redirect` must run only after successful submit, never when the finish screen first appears

### Step 5: Build submission payload behavior
Use `references/submission-contract.md` as the default submit serialization protocol.

At minimum, the generated HTML should make it possible to assemble:
- `surveyId`
- `submittedAt`
- `answers[]` with `questionId`, `questionType`, and type-specific `value`

For radio / checkbox / input / score / nps questions, preserve schema ids in DOM structure so submission assembly is reliable.
Unanswered questions must be omitted from `answers`.
If a child input carries its own `attribute` configuration, use that configuration in child rendering and validation. Treat child attribute semantics as the same input-style configuration family already defined by the provided materials.
If one option has multiple child fields, submission assembly must preserve them as a list of child answer objects rather than collapsing them into one value.
For input questions, use `option[].attribute.dataType` to choose control type and validation behavior. Apply the same rule to child inputs. If the dataType is missing or unsupported, fall back to `text`.
For `dateRange`, `timeRange`, and `dateTimeRange`, serialize the submitted value as `{ start, end }`.
For `input` questions, serialize `value` as an array of answered option-field objects, each preserving `optionId`, `dataType`, and `value`.

### Step 5.5: Run the executable payload validator
After assembling the default payload shape, validate it with:

```bash
python3 <repo-root>/validators/validate_survey_payload.py /absolute/path/to/payload.json
```

Rules:
- if the payload validator returns non-zero, treat the generated submit logic as unsafe
- if `input.value` collapses into an object instead of an array, that is a blocking error
- if a range datatype does not serialize to `{ start, end }`, that is a blocking error
- if `questionId` repeats in `answers`, that is a blocking error
- if child answers lose `childId`, `dataType`, or `value`, that is a blocking error

If you cannot execute the validator in the current environment, follow the same contract rules manually and explicitly say that runtime payload validation was not run.

### Step 5.8: Run the HTML runtime contract checker
After rendering the final HTML file, run:

```bash
python3 <repo-root>/validators/validate_survey_html_runtime.py /absolute/path/to/file.html
```

Use it to confirm the generated HTML still contains the critical behavior hooks for:
- schema-driven rendering
- event binding
- child visibility
- checkbox `exclusive`
- checkbox `mutual-exclusion`
- `localStorage` persistence and cleanup
- payload assembly

If the checker flags missing runtime hooks, treat the HTML as unsafe for delivery.
If the checker emits warnings about rich text sanitization or runtime-generated ids, call those out explicitly and fix them before production use.

## Output requirement
Always output a **single self-contained HTML document** with:
- semantic HTML
- embedded CSS in a `<style>` block
- minimal vanilla JS only when needed

Do not wrap the answer in markdown fences unless the user asks for fenced code.

## Submission requirement
The generated HTML must be **submittable**.

Until the user provides the exact submit contract, use this default approach:
- render the questionnaire inside a real `<form>`
- include a visible submit button
- keep all form controls serializable through standard HTML form behavior
- ensure inputs have usable `name` attributes
- ensure question and option relationships can be reconstructed from submitted values
- preserve schema ids in form names, values, or data attributes so downstream positioning and analytics remain possible
- use a safe placeholder submission target such as `action="#"` or a lightweight JS submit interception when no backend contract is provided
- when `survey.attribute.onePageOneQuestion === true`, render the intro, each question, and the finish section as separate steps and show only one at a time
- never combine `Pagination` with `survey.attribute.onePageOneQuestion === true`; validation must reject this conflict
- when manual `Pagination` grouping is needed, set `survey.attribute.onePageOneQuestion` to `false` and use `Pagination` nodes only as page separators
- in one-page-one-question mode, cache step answers in `localStorage` between screens using the key rules from `references/local-cache-rules.md`
- when `survey.attribute.allowBack === true`, render a previous-step action; otherwise do not expose previous-step navigation
- by default, final submit behavior should `console.log` the assembled payload
- after successful submit, clear the current survey cache from `localStorage`

Follow `references/submission-contract.md` as the default payload shape.
Do not invent a different backend API contract unless the user later specifies one.

## ID rules
All ids must be:
- randomly generated
- unique within the page
- non-placeholder
- frozen before the final HTML is delivered to users

This applies to:
- survey id
- question id
- option id
- child input id
- DOM element id when relevant

Never use placeholder or predictable ids such as:
- `survey-id`
- `question-id`
- `option-id`
- `q-1`
- `opt-1`

Use random readable ids such as:
- `survey_9f3k2m8x`
- `question_b7x4n2qp`
- `option_m3v8k1zr`

They do not need to follow one strict format, but they must look random and never repeat.

Important:
- generate ids during schema creation time, not at browser runtime
- the final HTML delivered to respondents must contain already-materialized stable ids
- do not use `Math.random()` or similar runtime generation for production survey ids inside the browser
- stable pre-frozen ids are required for correct cache keys, analytics, payload consistency, and debugging

## Supported schema types
Unless the user explicitly asks to extend the schema, only use:
- `survey`
- `radio`
- `checkbox`
- `input`
- `score`
- `nps`
- `finish`

## Schema behavior rules

### Preserve schema semantics
Even though the final output is HTML, keep the schema meaning intact:
- `title` and `description` are string fields with rich-text support
- render them with rich-text-aware output rather than flattening them to plain text only
- support only sanitized, whitelisted display elements inside these rich-text fields
- `survey` is an introduction block
- `radio` is single choice
- `checkbox` is multi choice
- `input` is free text input
- `finish` is the last section and submit context

### Use child inputs intentionally
Only render child inputs when the prompt logically implies:
- “Other, please specify”
- reason explanation
- follow-up text

Do not sprinkle child inputs everywhere.

### Treat media as optional
Only include media areas if the prompt explicitly asks for them or the scenario strongly implies them.
When used, media resources may be links or base64 values, and may represent image, audio, or video.

## Style rules
The user may freely describe the UI style.
Examples:
- AI Native
- 黑金高级
- 苹果风
- toC 感
- 极简
- 深色玻璃拟态
- 未来感
- 轻盈卡片风

Apply the requested style to:
- layout
- density
- color palette
- border radius
- buttons
- sections / cards
- shadows / outlines
- typography mood
- spacing rhythm

If the user gives no style direction, choose a clean, modern, readable default.

## Question design guidance
When the prompt is vague, make sensible product decisions:
- start with a concise welcome section
- if `survey.attribute.onePageOneQuestion` is enabled or implied, plan a step-based one-question-per-screen flow where intro, each question, and finish are independently displayed
- if the survey needs manual page groups with multiple questions per page, use `Pagination` separators and keep `survey.attribute.onePageOneQuestion` false
- if `survey.attribute.allowBack` is true, include previous-step navigation in step mode
- put easy questions first
- keep question order progressive
- place open input later unless the scenario suggests otherwise
- end with a clear submit section

For question count:
- if the user gives a number, honor it
- if not, default to **3–6 questions** for lightweight surveys
- default to **5–8 questions** for richer research-style surveys

## Response format
Return in this order:
1. a one-line summary of the generated page
2. the full HTML output
3. a short note on assumptions only if they materially affected the schema or submission behavior

## Example interpretation patterns

### Example 1
User asks: “做一个新品饮料试喝反馈问卷，5题左右，AI Native 风格。”

What to do:
- infer the survey intent
- build an internal schema using supported types
- validate the schema against both example JSON and field-guide references
- render a self-contained HTML page
- ensure the form is submittable
- assign random unique ids

### Example 2
User asks: “做一个活动报名问卷页面，偏 toC 一点，轻一点，不要后台感。”

What to do:
- identify it as a registration survey
- build the internal schema first
- validate field names, option structures, and field semantics
- render consumer-facing HTML
- keep submission available through the form
- assign random unique ids

### Example 3
User asks: “根据这个问卷需求做一个黑色高级感 HTML 页面。”

What to do:
- infer the structure from the prompt
- validate the schema before rendering
- generate HTML only
- ensure the page can submit
- assign random unique ids

## Quality bar
Before finalizing, quickly check:
- Did you first understand the prompt and infer intent?
- Did you build an internal schema before rendering HTML?
- Did you validate the schema against both the example JSON and the field-guide references?
- Did you run the executable validator or explicitly note why it could not be run?
- Did you validate the assembled payload against the executable payload validator or explicitly note why it could not be run?
- Did you run the HTML runtime contract checker or explicitly note why it could not be run?
- Is the final output HTML only?
- Does the page clearly reflect schema-supported survey structure?
- Do all ids look random and unique?
- Does the visual style match the user's prompt?
- Is the HTML submittable?
- Does the generated submit payload follow the submission contract?
- Is local step caching scoped and cleared correctly after submit?
- Did you avoid unsupported types?
- Is the page believable as a real survey UI or prototype?

If any answer is no, fix it before responding.
