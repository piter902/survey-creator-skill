#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"

python3 "$ROOT/tools/build_template.py"
python3 "$ROOT/validators/validate_reference_consistency.py"
python3 "$ROOT/tests/contract/run_contract_tests.py"
"$ROOT/validators/run-validator-smoke-tests.sh"

echo "✅ all legality checks passed"
