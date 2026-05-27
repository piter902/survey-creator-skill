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

- question-level summaries
- option distribution analysis
- segment comparisons
- notable anomalies or data-quality warnings
- an actionable business summary

## Read these first

Before analyzing, read:

- `../../specs/analytics-input.md`
- `../../specs/answer-storage.md`
- `../../specs/submission-api.md`
- `./references/metrics-model.md`
- `./references/report-shape.md`

## Expected input

Preferred input:

- absolute path to a survey schema JSON file
- absolute path to an answers JSON or JSONL file

Also acceptable:

- inline schema JSON
- inline answers JSON
- a directory containing both schema and answers exports

## Analysis rules

1. validate that every answer document belongs to the provided `surveyId`
2. ignore malformed records, but report how many were excluded and why
3. compute distributions only from structurally valid answers
4. preserve question ids and option ids in intermediate reasoning
5. separate factual summary from interpretation
6. call out low sample size before making strong conclusions
7. do not invent respondent intent that is not grounded in the dataset

## Minimum output

Return:

1. one-line survey result summary
2. dataset health summary
3. key findings by question
4. cross-question patterns or segments when supported by the data
5. concrete next actions

## Recommended report shape

Use this high-level structure:

- overview
- sample quality
- key metrics
- question findings
- segment patterns
- risks and caveats
- recommendations

## Output style

Keep the analysis decision-useful.

Do not dump raw counts without interpretation.
Do not make causal claims unless the data supports them.
