# Survey Analytics Outputs

The executable analytics pipeline generates three artifact types.

## 1. Excel workbook

Filename:

```text
<name>.analysis.xlsx
```

Purpose:

- give operators a flat answer table
- include per-question summary tables
- embed charts directly in the workbook
- provide cross-tab sheets for quick business review

Minimum sheets:

- `Overview`
- `Responses`
- `Question Summary`
- `Cross Tabs`
- `Finish Sentiment`
- `Extra Analysis`
- `Insights`

Additional sheets:

- one per question for chartable output or sampled text values

## 2. Analysis JSON

Filename:

```text
<name>.analysis.json
```

Purpose:

- machine-readable analysis artifact
- easy to feed into other agents or downstream automation

Recommended contents:

- survey summary
- sample counts
- question findings
- segment findings
- warnings
- recommendations

## 3. Insight Markdown

Filename:

```text
<name>.analysis.md
```

Purpose:

- concise narrative report for humans
- useful for PM,运营,销售,客服复盘

## Flattened response table rule

The `Responses` sheet should:

- start with metadata columns such as `submissionId`, `surveyId`, timestamps, finish path, and `extra`
- follow with one column per question in schema order
- use readable strings for selected options, score rows, and child inputs

## Text analysis boundary

The current pipeline performs theme extraction and basic sentiment analysis only for text fields that look like feedback or opinion.

It does not run sentiment analysis for obvious information-collection fields such as:

- name
- phone
- email
- company
- contact info

This prevents contact data from polluting opinion analysis.

## Current implementation notes

The current pipeline is intentionally dependency-light:

- Python standard library
- `xlsxwriter`

It does not require:

- `pandas`
- `openpyxl`
- `matplotlib`

This keeps the skill easier to run in constrained local environments.

## Optional cross config

When the user wants only specific cross-question analyses, provide:

```text
--cross-config /absolute/path/to/cross-config.json
```

Example:

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

If no cross config is provided, the pipeline uses its default cross analysis heuristics.

## Optional analysis config

Use:

```text
--analysis-config /absolute/path/to/analysis-config.json
```

This is mainly useful for text analysis scope control.

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

Recommended usage:

- include feedback-like text fields
- exclude contact and identity fields
- use question ids first when possible because they are more stable than labels
