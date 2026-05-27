# Metrics model

Use these default analysis primitives unless the user requests a custom method:

- total submissions
- valid submissions
- invalid submissions
- completion rate
- per-question answer rate
- option distribution
- average score for `score`
- average value and band distribution for `nps`
- top free-text themes by manual summary, not fabricated clustering

Rules:

- always report sample size with percentage-based findings
- treat unanswered questions as missing, not negative responses
- when comparing segments, report both count and ratio
