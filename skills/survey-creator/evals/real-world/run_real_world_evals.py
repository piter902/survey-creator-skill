#!/usr/bin/env python3
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVAL_ROOT = ROOT / 'evals' / 'real-world'
CASES = EVAL_ROOT / 'cases'
OUTPUTS = EVAL_ROOT / 'outputs'
PIPELINE = ROOT / 'validators' / 'run_survey_creator_pipeline.py'


def load_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def assert_true(condition, message, errors):
    if not condition:
        errors.append(message)


def schema_question_types(schema):
    return [q.get('type') for q in schema.get('questions', []) if isinstance(q, dict)]


def validate_business_expectations(case_id, schema, expected, report):
    errors = []
    qtypes = schema_question_types(schema)
    for qtype in expected.get('questionTypes', []):
        assert_true(qtype in qtypes, f'missing expected question type {qtype}', errors)
    min_q = expected.get('minQuestions')
    if min_q is not None:
        assert_true(len(schema.get('questions', [])) >= min_q, f'expected at least {min_q} questions, got {len(schema.get("questions", []))}', errors)
    ids = set()
    duplicates = []
    def walk(node):
        if isinstance(node, dict):
            node_id = node.get('id')
            if isinstance(node_id, str):
                if node_id in ids:
                    duplicates.append(node_id)
                ids.add(node_id)
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)
    walk(schema)
    assert_true(not duplicates, f'duplicate ids in schema: {duplicates}', errors)
    for qid in expected.get('mustIncludeQuestionIds', []):
        assert_true(qid in ids, f'missing expected id {qid}', errors)
    decision = report.get('releaseDecision', {})
    assert_true(report.get('valid') is True, 'pipeline valid is not true', errors)
    assert_true(decision.get('shipReady') is True, 'releaseDecision.shipReady is not true', errors)
    assert_true(report.get('payloadAgainstSchema', {}).get('valid') is True, 'payloadAgainstSchema.valid is not true', errors)
    assert_true(report.get('htmlAccessibility', {}).get('valid') is True, 'htmlAccessibility.valid is not true', errors)
    for section in ['htmlE2E', 'htmlInteractionE2E', 'htmlAccessibility']:
        viewports = report.get(section, {}).get('viewports', {})
        assert_true(viewports.get('desktop', {}).get('valid') is True, f'{section}.desktop is not valid', errors)
        assert_true(viewports.get('mobile', {}).get('valid') is True, f'{section}.mobile is not valid', errors)
    return errors


def run_case(case_dir):
    case_id = case_dir.name
    schema_path = case_dir / 'schema.json'
    expected_path = case_dir / 'expected.json'
    out_dir = OUTPUTS / case_id
    out_dir.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run([
        'python3', str(PIPELINE),
        '--schema', str(schema_path),
        '--output-dir', str(out_dir),
        '--auto-repair',
        '--fail-on-high-warning',
        '--json',
    ], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=180)
    if proc.returncode != 0:
        return {
            'caseId': case_id,
            'valid': False,
            'errors': [f'pipeline returned {proc.returncode}', proc.stderr.strip(), proc.stdout[:2000]],
            'outputDir': str(out_dir),
        }
    try:
        report = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        return {'caseId': case_id, 'valid': False, 'errors': [f'invalid pipeline json: {exc}', proc.stdout[:2000]], 'outputDir': str(out_dir)}
    schema = load_json(schema_path)
    expected = load_json(expected_path)
    errors = validate_business_expectations(case_id, schema, expected, report)
    return {
        'caseId': case_id,
        'valid': not errors,
        'errors': errors,
        'outputDir': str(out_dir),
        'html': report.get('output', {}).get('html'),
        'pipelineReport': report.get('output', {}).get('report'),
        'summary': report.get('summary', {}),
        'releaseDecision': report.get('releaseDecision', {}),
        'questionTypes': schema_question_types(schema),
    }


def main():
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    cases = sorted([p for p in CASES.iterdir() if p.is_dir() and (p / 'schema.json').exists()])
    results = [run_case(case) for case in cases]
    report = {
        'valid': all(item['valid'] for item in results),
        'caseCount': len(results),
        'passedCount': sum(1 for item in results if item['valid']),
        'failedCount': sum(1 for item in results if not item['valid']),
        'results': results,
    }
    report_path = OUTPUTS / 'real-world-eval-report.json'
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    if '--json' in sys.argv:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print('✅ REAL-WORLD EVALS PASS' if report['valid'] else '❌ REAL-WORLD EVALS FAIL')
        print(f"Cases: {report['passedCount']}/{report['caseCount']} passed")
        for item in results:
            status = '✅' if item['valid'] else '❌'
            print(f"{status} {item['caseId']} -> {item['outputDir']}")
            for error in item.get('errors', []):
                print(f"   - {error}")
        print(f"Report: {report_path}")
    sys.exit(0 if report['valid'] else 1)


if __name__ == '__main__':
    main()
