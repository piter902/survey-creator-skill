---
name: survey-analytics
description: Analyze survey answer datasets against a survey schema and produce structured findings, summaries, segment insights, and action recommendations. Use this skill when the user wants to review survey results, summarize answers, compare segments, identify patterns, or generate a survey analysis report.
---

# Survey Analytics

This skill analyzes survey results.

It does **not** generate survey HTML.
It consumes:

- a survey schema
- a survey answers dataset

## Primary job

Take a validated survey schema plus answers and produce:

- one Excel workbook where columns are questions and rows are submissions
- per-question statistics and charts by question type
- cross-question or logic-driven analysis tables
- a machine-readable analysis JSON
- a human-readable insight report

## Read these first

Before analyzing, read:

- `../../specs/analytics-input.md`
- `../../specs/answer-storage.md`
- `../../specs/submission-api.md`
- `./references/metrics-model.md`
- `./references/report-shape.md`
- `./docs/OUTPUTS.md`

## Expected input

Preferred input:

- absolute path to a survey schema JSON file
- absolute path to an answers JSON or JSONL file

Also acceptable:

- inline schema JSON
- inline answers JSON
- a directory containing both schema and answers exports

## Required execution mode

Do not stop at a prose-only analysis when local file execution is available.

Use the executable pipeline:

```bash
python3 <survey-analytics-root>/tools/analyze_survey_results.py \
  --schema /absolute/path/to/schema.json \
  --answers /absolute/path/to/answers.json \
  --out-dir /absolute/path/to/output-dir
```

When the user wants specific cross-question analysis, pass a config file:

```bash
python3 <survey-analytics-root>/tools/analyze_survey_results.py \
  --schema /absolute/path/to/schema.json \
  --answers /absolute/path/to/answers.json \
  --cross-config /absolute/path/to/cross-config.json \
  --out-dir /absolute/path/to/output-dir
```

The script generates:

- `<name>.analysis.xlsx`
- `<name>.analysis.json`
- `<name>.analysis.md`

If the user only asks for insights and does not want files, you may summarize the generated report instead of returning file contents.

## Analysis rules

1. validate that every normalized answer document belongs to the provided `surveyId`
2. ignore malformed records, but report how many were excluded and why
3. compute distributions only from structurally valid answers
4. preserve question ids and option ids in intermediate reasoning
5. separate factual summary from interpretation
6. call out low sample size before making strong conclusions
7. do not invent respondent intent that is not grounded in the dataset
8. when schema logic exists, use it to infer finish-path or segment-level analysis when possible

## Output requirements

The workbook should include at least:

- `Overview`
- `Responses`
- `Question Summary`
- `Cross Tabs`
- `Finish Sentiment`
- `Extra Analysis`
- `Insights`
- one dedicated sheet per question for chartable output

The flattened response table should use:

- fixed metadata columns first
- then one column per question
- cell values should be respondent-readable, not raw nested JSON unless unavoidable

## Chart rules by question type

- `radio`: option distribution column chart
- `checkbox`: option selection frequency column chart
- `input`: no forced chart; keep a readable sample table instead
- `score`: score distribution chart and average score
- `nps`: score distribution chart plus promoter/passive/detractor band summary

## Text analysis rule

For free-text fields, the skill should distinguish between:

- feedback/opinion text
- information collection text

Only feedback/opinion text should receive:

- theme extraction
- sentiment analysis using business-friendly Chinese labels such as:
  - `高度满意`
  - `满意`
  - `中性`
  - `不满`
  - `强烈不满`

Do **not** run sentiment analysis on fields that are clearly for information collection, such as:

- name
- phone
- email
- company
- contact info
- address

These fields may still appear in the flattened workbook, but they should not drive sentiment findings.

## Cross analysis strategy

Default cross analysis should prefer:

- `radio` vs `score`
- `radio` vs `nps`
- `radio` vs `checkbox`
- finish-path distribution when logic contains `end_survey`
- `extra` attribution dimensions such as `utm_source` / `campaign` vs finish-path and text sentiment
- logic-driven path summaries for branch-heavy surveys

If the user explicitly names segment questions or wants tighter control, create a cross config JSON with this shape:

```json
{
  "pairs": [
    {
      "segmentQuestionId": "radio-205152",
      "metricQuestionId": "score-205160"
    }
  ]
}
```

Only those pairs should be generated when a cross config is provided.

When the user wants explicit control over which text fields receive theme/sentiment analysis, pass:

```bash
python3 <survey-analytics-root>/tools/analyze_survey_results.py \
  --schema /absolute/path/to/schema.json \
  --answers /absolute/path/to/answers.json \
  --analysis-config /absolute/path/to/analysis-config.json \
  --out-dir /absolute/path/to/output-dir
```

Example:

```json
{
  "textAnalysis": {
    "includeQuestionIds": ["checkbox-205170"],
    "excludeQuestionIds": ["input-205179"],
    "includeLabels": ["补充说明", "其他"],
    "excludeLabels": ["姓名", "手机号", "联系方式"]
  }
}
```

Rules:

- if a text field matches `excludeQuestionIds` or `excludeLabels`, do not analyze its sentiment
- if `includeQuestionIds` or `includeLabels` matches, do analyze it
- when no config is provided, fall back to the built-in heuristic

## Minimum output

Return:

1. workbook path
2. analysis JSON path
3. insight markdown path
4. short summary of what was generated
5. any data-quality warnings

## Output style

Keep the analysis decision-useful.

Do not dump raw counts without interpretation.
Do not make causal claims unless the data supports them.
