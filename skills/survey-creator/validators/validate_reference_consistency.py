#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REFERENCES = ROOT / 'references'
VALIDATE_SCHEMA = ROOT / 'validators' / 'validate_survey_schema.py'
VALIDATE_PAYLOAD = ROOT / 'validators' / 'validate_survey_payload.py'
TEMPLATE = ROOT / 'templates' / 'base-survey-template.html'
SKILL = ROOT / 'SKILL.md'
SUBMISSION = REFERENCES / 'submission-contract.md'


def read(path):
    return path.read_text(encoding='utf-8')


def parse_allowed_types_from_python(path):
    text = read(path)
    match = re.search(r'ALLOWED_QUESTION_TYPES\s*=\s*\{([^}]+)\}', text)
    if not match:
        raise AssertionError(f'Cannot find ALLOWED_QUESTION_TYPES in {path}')
    return set(re.findall(r'"([^"]+)"', match.group(1)))


def reference_question_types():
    types = set()
    files = {}
    for path in REFERENCES.glob('question-*.json'):
        if path.name == 'question-finish.json':
            continue
        data = json.loads(read(path))
        qtype = data.get('type') if isinstance(data, dict) else None
        if qtype:
            types.add(qtype)
            files[qtype] = path
    return types, files


def require(condition, message, errors):
    if not condition:
        errors.append(message)


def main():
    errors = []
    warnings = []

    schema_types = parse_allowed_types_from_python(VALIDATE_SCHEMA)
    payload_types = parse_allowed_types_from_python(VALIDATE_PAYLOAD)
    ref_types, ref_files = reference_question_types()

    require(schema_types == ref_types, f'schema validator types {sorted(schema_types)} do not match reference question types {sorted(ref_types)}', errors)
    require(payload_types == schema_types, f'payload validator types {sorted(payload_types)} do not match schema validator types {sorted(schema_types)}', errors)

    skill_text = read(SKILL)
    submission_text = read(SUBMISSION)
    template_text = read(TEMPLATE)
    schema_validator_text = read(VALIDATE_SCHEMA)
    payload_validator_text = read(VALIDATE_PAYLOAD)

    for qtype in sorted(schema_types):
        require((REFERENCES / f'{qtype}-fields.md').exists(), f'missing field guide references/{qtype}-fields.md', errors)
        require(qtype in skill_text, f'SKILL.md does not mention question type {qtype}', errors)
        require(qtype in submission_text, f'submission-contract.md does not mention question type {qtype}', errors)
        require(qtype in template_text, f'base-survey-template.html does not mention/render question type {qtype}', errors)
        require(qtype in schema_validator_text, f'validate_survey_schema.py does not mention question type {qtype}', errors)
        require(qtype in payload_validator_text, f'validate_survey_payload.py does not mention question type {qtype}', errors)

    # Specific semantic consistency checks for advanced types.
    if 'score' in schema_types:
        score_guide = read(REFERENCES / 'score-fields.md')
        for term in ['scope', 'step', 'scoreDesc', 'media']:
            require(term in score_guide, f'score-fields.md missing {term}', errors)
            require(term in schema_validator_text, f'schema validator missing score support for {term}', errors)
        require('renderScoreQuestion' in template_text, 'template missing renderScoreQuestion', errors)

    if 'nps' in schema_types:
        nps_guide = read(REFERENCES / 'nps-fields.md')
        for term in ['scope', 'scoreDesc', 'media', '0-6']:
            require(term in nps_guide, f'nps-fields.md missing {term}', errors)
        require('validate_nps_question' in schema_validator_text, 'schema validator missing validate_nps_question', errors)
        require('validate_nps_value' in payload_validator_text, 'payload validator missing validate_nps_value', errors)
        require('renderNpsQuestion' in template_text, 'template missing renderNpsQuestion', errors)

    # Reference JSON examples should not contain placeholder-only unsupported fields.
    for qtype, path in sorted(ref_files.items()):
        try:
            data = json.loads(read(path))
        except json.JSONDecodeError as exc:
            errors.append(f'{path.name} is invalid JSON: {exc}')
            continue
        require(data.get('type') == qtype, f'{path.name} type mismatch', errors)
        require('id' in data, f'{path.name} missing id', errors)
        require('attribute' in data, f'{path.name} missing attribute', errors)

    result = {
        'valid': not errors,
        'errors': errors,
        'warnings': warnings,
        'questionTypes': sorted(schema_types),
        'referenceFiles': {k: str(v) for k, v in sorted(ref_files.items())},
    }

    if '--json' in sys.argv:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        if result['valid']:
            print('✅ Reference consistency check passed.')
            print('Question types:', ', '.join(result['questionTypes']))
        else:
            print('❌ Reference consistency check failed.')
            for i, error in enumerate(errors, 1):
                print(f'{i}. {error}')
    sys.exit(0 if result['valid'] else 1)


if __name__ == '__main__':
    main()
