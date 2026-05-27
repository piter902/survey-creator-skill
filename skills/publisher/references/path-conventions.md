# Path Conventions

For survey id:

```text
survey-310992845731864576
```

Use:

```text
archive schema key:
surveys/survey-310992845731864576/survey.schema.json

archive html key:
surveys/survey-310992845731864576/survey.html

public html path:
/surveys/survey-310992845731864576.html
```

## Why

- stable per-survey archive layout
- easy backend registration
- predictable public URL shape

## Rule

Always prefer survey-id-based public path naming, even if the local html file uses another filename.

`publicWeb.prefix` already represents the root path prefix, so providers must not inject an extra hard-coded `/surveys` segment on top of it.
