# Provider Model

`survey-publisher` should be provider-neutral.

## Two-role abstraction

Every provider implementation should explain how it satisfies:

1. `archive`
2. `publicWeb`

### `archive`

Stable artifact storage for:

- schema
- optional html archive

### `publicWeb`

Respondent-facing browser-openable page delivery for:

- html

## Adapter rule

Provider-specific code belongs in provider adapters, not in the root skill flow.

Current provider adapters:

- `tencent`

Future providers can include:

- `aliyun`
- `aws_s3`
- `cloudflare_r2`
- `generic_http`

The root publish contract must not change when a new provider is added.
