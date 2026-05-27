#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
TMP_DIR="$(mktemp -d /tmp/survey-creator-smoke.XXXXXX)"
trap 'rm -rf "$TMP_DIR"' EXIT

python3 "$ROOT/validate_survey_schema.py" "$ROOT/sample-valid-schema.json"
python3 "$ROOT/validate_survey_payload.py" "$ROOT/sample-valid-payload.json"
python3 "$ROOT/validate_payload_against_schema.py" "$ROOT/sample-valid-schema.json" "$ROOT/sample-valid-payload.json"
python3 "$ROOT/run_survey_creator_pipeline.py"   --schema "$ROOT/sample-valid-schema.json"   --output-dir "$TMP_DIR"   --auto-repair   --fail-on-high-warning

echo "✅ validator smoke tests passed"
