#!/usr/bin/env python3
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'validators'))
CONTRACT = ROOT / 'tests' / 'contract'
SCHEMAS = CONTRACT / 'schemas'
PAYLOADS = CONTRACT / 'payloads'
VALIDATE_SCHEMA = ROOT / 'validators' / 'validate_survey_schema.py'
VALIDATE_PAYLOAD = ROOT / 'validators' / 'validate_survey_payload.py'
VALIDATE_PAYLOAD_SCHEMA = ROOT / 'validators' / 'validate_payload_against_schema.py'
VALIDATE_INTERACTION_E2E = ROOT / 'validators' / 'validate_survey_html_interaction_e2e.py'
VALIDATE_ACCESSIBILITY = ROOT / 'validators' / 'validate_survey_html_accessibility.py'
PIPELINE = ROOT / 'validators' / 'run_survey_creator_pipeline.py'
from run_survey_creator_pipeline import validate_browser_payloads_against_schema, compute_release_decision
from auto_repair_survey_html import auto_repair_html
from auto_repair_survey_schema import auto_repair_schema
from render_survey_html import render_html_from_schema, DEFAULT_TEMPLATE
from schema_id_utils import normalize_schema_ids
from validate_survey_payload import validate_survey_payload

SCHEMA_CASES = {
    'minimal-radio.json': True,
    'minimal-checkbox.json': True,
    'minimal-input.json': True,
    'minimal-score.json': True,
    'minimal-nps.json': True,
    'valid-logic-flow.json': True,
    'valid-logic-jump-page.json': True,
    'valid-logic-end-survey.json': True,
    'valid-logic-hide-question-required.json': True,
    'valid-logic-show-option-auto-select.json': True,
    'valid-logic-combo-chain.json': True,
    'valid-logic-conflict-question-last-show.json': True,
    'valid-logic-conflict-option-last-hide.json': True,
    'valid-logic-conflict-jump-last-end.json': True,
    'valid-logic-cache-hidden-cleanup.json': True,
    'valid-logic-input-operators.json': True,
    'valid-logic-selection-status-operators.json': True,
    'valid-pagination-manual-pages.json': True,
    'valid-resume-checkpoint.json': True,
    'complete-score-media.json': True,
    'complete-nps-media.json': True,
    'full-all-types.json': True,
    'valid-finish-post-submit-immediate.json': True,
    'invalid-unsupported-field.json': False,
    'invalid-duplicate-id.json': False,
    'invalid-input-datatype.json': False,
    'invalid-score-step.json': False,
    'invalid-nps-scoredesc.json': False,
    'invalid-radio-missing-option.json': False,
    'invalid-logic-operator.json': False,
    'invalid-logic-target.json': False,
    'invalid-pagination-with-one-page-one-question.json': False,
    'invalid-pagination-missing-id.json': False,
    'invalid-pagination-extra-fields.json': False,
    'invalid-media-type.json': False,
    'invalid-media-url-scheme.json': False,
    'invalid-finish-post-submit-url.json': False,
    'invalid-id-unsafe-chars.json': False,
    'invalid-nps-scope-reversed.json': False,
}

PAYLOAD_CASES = {
    'valid-all-types.json': True,
    'invalid-nps-array.json': False,
    'invalid-nps-float.json': False,
    'invalid-score-object.json': False,
    'invalid-range-scalar.json': False,
    'invalid-duplicate-question.json': False,
    'invalid-unknown-question-type.json': False,
    'invalid-child-missing-id.json': False,
}


def run_json(cmd):
    proc = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        print(proc.stdout)
        print(proc.stderr, file=sys.stderr)
        raise
    return proc.returncode, data, proc.stderr


def assert_case(name, actual, expected, detail=''):
    if actual != expected:
        raise AssertionError(f'{name}: expected {expected}, got {actual}. {detail}')
    print(f'✅ {name}')


def get_pipeline_output_path(report, key):
    output = report.get('output') or {}
    path = output.get(key)
    if not path:
        raise AssertionError(f'missing pipeline output path for {key}: {report}')
    return Path(path)


def get_pipeline_schema(report):
    schema_path = get_pipeline_output_path(report, 'schema')
    return json.loads(schema_path.read_text(encoding='utf-8'))


def build_schema_id_map(source_schema, repaired_schema):
    mapping = {}

    def remember(source_id, repaired_id):
        if isinstance(source_id, str) and isinstance(repaired_id, str):
            mapping[source_id] = repaired_id

    source_survey = source_schema.get('survey') or {}
    repaired_survey = repaired_schema.get('survey') or {}
    remember(source_survey.get('id'), repaired_survey.get('id'))

    source_questions = source_schema.get('questions') or []
    repaired_questions = repaired_schema.get('questions') or []
    for source_question, repaired_question in zip(source_questions, repaired_questions):
        if not isinstance(source_question, dict) or not isinstance(repaired_question, dict):
            continue
        remember(source_question.get('id'), repaired_question.get('id'))
        source_options = source_question.get('option') or []
        repaired_options = repaired_question.get('option') or []
        for source_option, repaired_option in zip(source_options, repaired_options):
            if not isinstance(source_option, dict) or not isinstance(repaired_option, dict):
                continue
            remember(source_option.get('id'), repaired_option.get('id'))
            source_children = source_option.get('child') or []
            repaired_children = repaired_option.get('child') or []
            for source_child, repaired_child in zip(source_children, repaired_children):
                if not isinstance(source_child, dict) or not isinstance(repaired_child, dict):
                    continue
                remember(source_child.get('id'), repaired_child.get('id'))

    source_finish = source_schema.get('finish') or []
    repaired_finish = repaired_schema.get('finish') or []
    for source_node, repaired_node in zip(source_finish, repaired_finish):
        if not isinstance(source_node, dict) or not isinstance(repaired_node, dict):
            continue
        remember(source_node.get('id'), repaired_node.get('id'))

    return mapping


def test_schema_cases():
    for name, expected in SCHEMA_CASES.items():
        code, data, _ = run_json(['python3', str(VALIDATE_SCHEMA), str(SCHEMAS / name), '--json'])
        assert_case(f'schema/{name}', data.get('valid') is True, expected, data.get('errors'))
        assert_case(f'schema-exit/{name}', code == 0, expected)


def test_payload_cases():
    for name, expected in PAYLOAD_CASES.items():
        code, data, _ = run_json(['python3', str(VALIDATE_PAYLOAD), str(PAYLOADS / name), '--json'])
        assert_case(f'payload/{name}', data.get('valid') is True, expected, data.get('errors'))
        assert_case(f'payload-exit/{name}', code == 0, expected)


def test_payload_extra_cases():
    payload = json.loads((PAYLOADS / 'valid-all-types.json').read_text(encoding='utf-8'))

    valid_extra = json.loads(json.dumps(payload))
    valid_extra['extra'] = {
        'utm_source': 'wechat',
        'channel': 'qr',
        'tag': ['a', 'b'],
    }
    report = validate_survey_payload(valid_extra)
    assert_case('payload-extra-valid', report.get('valid'), True, report.get('errors'))

    invalid_extra = json.loads(json.dumps(payload))
    invalid_extra['extra'] = {'utm_source': ''}
    report = validate_survey_payload(invalid_extra)
    assert_case('payload-extra-invalid-empty-string', report.get('valid'), False, report.get('errors'))

    invalid_extra_array = json.loads(json.dumps(payload))
    invalid_extra_array['extra'] = {'tag': ['a', '']}
    report = validate_survey_payload(invalid_extra_array)
    assert_case('payload-extra-invalid-empty-array-item', report.get('valid'), False, report.get('errors'))


def parse_allowed_types():
    text = VALIDATE_SCHEMA.read_text(encoding='utf-8')
    match = re.search(r'ALLOWED_QUESTION_TYPES\s*=\s*\{([^}]+)\}', text)
    if not match:
        raise AssertionError('Cannot find ALLOWED_QUESTION_TYPES in schema validator')
    return set(re.findall(r'"([^"]+)"', match.group(1)))


def test_reference_validator_consistency():
    allowed = parse_allowed_types()
    reference_types = set()
    for path in (ROOT / 'references').glob('question-*.json'):
        if path.name == 'question-finish.json':
            continue
        data = json.loads(path.read_text(encoding='utf-8'))
        if isinstance(data, dict) and data.get('type'):
            reference_types.add(data['type'])
    assert_case('reference-types-match-validator', reference_types, allowed)
    for qtype in allowed:
        md = ROOT / 'references' / f'{qtype}-fields.md'
        assert_case(f'field-guide/{qtype}', md.exists(), True)



def run_payload_against_schema_case(name, schema_data, payload_data, expected, message_contains=None):
    with tempfile.TemporaryDirectory(prefix='survey-creator-payload-schema.') as tmp:
        tmp_path = Path(tmp)
        schema_path = tmp_path / 'schema.json'
        payload_path = tmp_path / 'payload.json'
        schema_path.write_text(json.dumps(schema_data, ensure_ascii=False, indent=2), encoding='utf-8')
        payload_path.write_text(json.dumps(payload_data, ensure_ascii=False, indent=2), encoding='utf-8')
        code, data, _ = run_json(['python3', str(VALIDATE_PAYLOAD_SCHEMA), str(schema_path), str(payload_path), '--json'])
        assert_case(f'payload-schema/{name}', data.get('valid') is True, expected, data.get('errors'))
        assert_case(f'payload-schema-exit/{name}', code == 0, expected)
        if message_contains:
            messages = ' '.join(item.get('message', '') for item in data.get('errors', []))
            assert_case(f'payload-schema-message/{name}', message_contains in messages, True, messages)


def test_payload_against_schema_cases():
    schema = json.loads((SCHEMAS / 'full-all-types.json').read_text(encoding='utf-8'))
    payload = json.loads((PAYLOADS / 'valid-all-types.json').read_text(encoding='utf-8'))
    run_payload_against_schema_case('valid-all-types', schema, payload, True)

    bad_unknown_option = json.loads(json.dumps(payload))
    bad_unknown_option['answers'][0]['value']['optionId'] = 'option_missing'
    run_payload_against_schema_case('invalid-unknown-option', schema, bad_unknown_option, False, 'does not exist under question')

    bad_required_missing = json.loads(json.dumps(payload))
    bad_required_missing['answers'] = [a for a in bad_required_missing['answers'] if a.get('questionId') != 'question_score']
    run_payload_against_schema_case('invalid-required-missing', schema, bad_required_missing, False, 'Required question question_score')

    bad_score_scope = json.loads(json.dumps(payload))
    for answer in bad_score_scope['answers']:
        if answer.get('questionType') == 'score':
            answer['value'][0]['score'] = 9
    run_payload_against_schema_case('invalid-score-out-of-scope', schema, bad_score_scope, False, 'outside schema scope')

    bad_nps_scope = json.loads(json.dumps(payload))
    for answer in bad_nps_scope['answers']:
        if answer.get('questionType') == 'nps':
            answer['value']['score'] = 11
    run_payload_against_schema_case('invalid-nps-out-of-scope', schema, bad_nps_scope, False, 'outside schema scope')

    bad_input_datatype = json.loads(json.dumps(payload))
    for answer in bad_input_datatype['answers']:
        if answer.get('questionType') == 'input':
            answer['value'][0]['dataType'] = 'text'
    run_payload_against_schema_case('invalid-input-datatype-mismatch', schema, bad_input_datatype, False, 'does not match schema option dataType')

    bad_child = json.loads(json.dumps(payload))
    bad_child['answers'][0]['value']['child'][0]['childId'] = 'child_missing'
    run_payload_against_schema_case('invalid-child-not-under-selected-option', schema, bad_child, False, 'does not exist under selected option')

    bad_exclusive = json.loads(json.dumps(payload))
    for answer in bad_exclusive['answers']:
        if answer.get('questionType') == 'checkbox':
            answer['value'] = [{'optionId': 'option_checkbox_a'}, {'optionId': 'option_checkbox_none'}]
    run_payload_against_schema_case('invalid-checkbox-exclusive-combination', schema, bad_exclusive, False, 'Exclusive option')


def test_logic_pipeline_and_interaction():
    with tempfile.TemporaryDirectory(prefix='survey-creator-contract-logic.') as tmp:
        tmp_path = Path(tmp)
        proc = subprocess.run([
            'python3', str(PIPELINE),
            '--schema', str(SCHEMAS / 'valid-logic-flow.json'),
            '--output-dir', str(tmp_path),
            '--auto-repair',
            '--fail-on-high-warning',
            '--json',
        ], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.returncode != 0:
            print(proc.stdout)
            print(proc.stderr, file=sys.stderr)
            raise AssertionError('logic pipeline returned non-zero')
        data = json.loads(proc.stdout)
        assert_case('logic-pipeline-valid', data.get('valid'), True)
        assert_case('logic-pipeline-shipReady', data.get('releaseDecision', {}).get('shipReady'), True)
        html_path = get_pipeline_output_path(data, 'html')
        repaired_schema = get_pipeline_schema(data)
        source_schema = json.loads((SCHEMAS / 'valid-logic-flow.json').read_text(encoding='utf-8'))
        id_map = build_schema_id_map(source_schema, repaired_schema)
        assert_case('logic-pipeline-html-name-uses-survey-id', html_path.name, f"{repaired_schema.get('survey', {}).get('id')}.html")
        html = html_path.read_text(encoding='utf-8')
        for marker in ['function computeLogicState()', 'function applyLogicRuntime(', 'jumpTargets', 'isQuestionHidden(', 'isOptionHidden(']:
            assert_case(f'logic-html-marker/{marker}', marker in html, True)
        payload = data.get('htmlInteractionE2E', {}).get('payload') or {}
        answers = payload.get('answers', [])
        answer_ids = {item.get('questionId') for item in answers if isinstance(item, dict)}
        assert_case('logic-followup-submitted', id_map['question_followup'] in answer_ids, True, answers)
        assert_case('logic-checkbox-submitted', id_map['question_modes'] in answer_ids, True, answers)
        logic_checkbox = next((item for item in answers if item.get('questionId') == id_map['question_modes']), None)
        assert_case('logic-auto-select-ai', logic_checkbox.get('value') == [{'optionId': id_map['option_mode_ai']}], True, logic_checkbox)


def test_logic_jump_page_pipeline_and_interaction():
    with tempfile.TemporaryDirectory(prefix='survey-creator-contract-logic-jump-page.') as tmp:
        tmp_path = Path(tmp)
        schema = json.loads((SCHEMAS / 'valid-logic-jump-page.json').read_text(encoding='utf-8'))
        middle_question = next((item for item in schema.get('questions', []) if item.get('id') == 'question_middle_optional'), None)
        assert_case('logic-jump-page-middle-is-required', middle_question.get('attribute', {}).get('required'), True, middle_question)
        proc = subprocess.run([
            'python3', str(PIPELINE),
            '--schema', str(SCHEMAS / 'valid-logic-jump-page.json'),
            '--output-dir', str(tmp_path),
            '--auto-repair',
            '--fail-on-high-warning',
            '--json',
        ], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.returncode != 0:
            print(proc.stdout)
            print(proc.stderr, file=sys.stderr)
            raise AssertionError('logic jump page pipeline returned non-zero')
        data = json.loads(proc.stdout)
        assert_case('logic-jump-page-pipeline-valid', data.get('valid'), True)
        assert_case('logic-jump-page-shipReady', data.get('releaseDecision', {}).get('shipReady'), True)
        repaired_schema = get_pipeline_schema(data)
        id_map = build_schema_id_map(schema, repaired_schema)
        html = get_pipeline_output_path(data, 'html').read_text(encoding='utf-8')
        for marker in ["action.type === 'jump_to_page'", 'jumpTargets', 'resolveScreenId(']:
            assert_case(f'logic-jump-page-html-marker/{marker}', marker in html, True)
        payload = data.get('htmlInteractionE2E', {}).get('payload') or {}
        answers = payload.get('answers', [])
        answer_ids = {item.get('questionId') for item in answers if isinstance(item, dict)}
        assert_case('logic-jump-page-entry-submitted', id_map['question_entry'] in answer_ids, True, answers)
        assert_case('logic-jump-page-target-submitted', id_map['question_target_modes'] in answer_ids, True, answers)
        assert_case('logic-jump-page-middle-required-but-skipped', id_map['question_middle_optional'] in answer_ids, False, answers)
        target_answer = next((item for item in answers if item.get('questionId') == id_map['question_target_modes']), None)
        assert_case('logic-jump-page-auto-select-ai', target_answer.get('value') == [{'optionId': id_map['option_mode_ai']}], True, target_answer)

def test_logic_end_survey_pipeline_and_interaction():
    with tempfile.TemporaryDirectory(prefix='survey-creator-contract-logic-end-survey.') as tmp:
        tmp_path = Path(tmp)
        source_schema = json.loads((SCHEMAS / 'valid-logic-end-survey.json').read_text(encoding='utf-8'))
        proc = subprocess.run([
            'python3', str(PIPELINE),
            '--schema', str(SCHEMAS / 'valid-logic-end-survey.json'),
            '--output-dir', str(tmp_path),
            '--auto-repair',
            '--fail-on-high-warning',
            '--json',
        ], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.returncode != 0:
            print(proc.stdout)
            print(proc.stderr, file=sys.stderr)
            raise AssertionError('logic end survey pipeline returned non-zero')
        data = json.loads(proc.stdout)
        assert_case('logic-end-survey-pipeline-valid', data.get('valid'), True)
        assert_case('logic-end-survey-shipReady', data.get('releaseDecision', {}).get('shipReady'), True)
        repaired_schema = get_pipeline_schema(data)
        id_map = build_schema_id_map(source_schema, repaired_schema)
        interactions = data.get('htmlInteractionE2E', {}).get('interactions') or []
        last_interaction = interactions[-1] if interactions else {}
        payload = data.get('htmlInteractionE2E', {}).get('payload') or {}
        answers = payload.get('answers', [])
        answer_ids = {item.get('questionId') for item in answers if isinstance(item, dict)}
        assert_case('logic-end-survey-gate-submitted', id_map['question_gate'] in answer_ids, True, answers)
        assert_case('logic-end-survey-required-question-omitted', id_map['question_required_detail'] in answer_ids, False, answers)
        assert_case('logic-end-survey-target-finish-reached', last_interaction.get('id'), id_map['finish_logic_end_survey_comfort'], interactions)
        redirects = data.get('htmlInteractionE2E', {}).get('redirects') or []
        assert_case('logic-end-survey-delay-redirect-fired', len(redirects) > 0, True, redirects)
        assert_case('logic-end-survey-delay-redirect-mode', redirects[-1].get('mode'), 'delay', redirects)
        assert_case('logic-end-survey-delay-redirect-url', redirects[-1].get('url'), 'https://example.com/follow-up', redirects)


def test_finish_post_submit_immediate_pipeline_and_interaction():
    with tempfile.TemporaryDirectory(prefix='survey-creator-contract-finish-post-submit-immediate.') as tmp:
        tmp_path = Path(tmp)
        source_schema = json.loads((SCHEMAS / 'valid-finish-post-submit-immediate.json').read_text(encoding='utf-8'))
        proc = subprocess.run([
            'python3', str(PIPELINE),
            '--schema', str(SCHEMAS / 'valid-finish-post-submit-immediate.json'),
            '--output-dir', str(tmp_path),
            '--auto-repair',
            '--fail-on-high-warning',
            '--json',
        ], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.returncode != 0:
            print(proc.stdout)
            print(proc.stderr, file=sys.stderr)
            raise AssertionError('finish post submit immediate pipeline returned non-zero')
        data = json.loads(proc.stdout)
        assert_case('finish-post-submit-immediate-pipeline-valid', data.get('valid'), True)
        assert_case('finish-post-submit-immediate-shipReady', data.get('releaseDecision', {}).get('shipReady'), True)
        repaired_schema = get_pipeline_schema(data)
        id_map = build_schema_id_map(source_schema, repaired_schema)
        payload = data.get('htmlInteractionE2E', {}).get('payload') or {}
        answers = payload.get('answers', [])
        answer_ids = {item.get('questionId') for item in answers if isinstance(item, dict)}
        assert_case('finish-post-submit-immediate-question-submitted', id_map['question_finish_post_submit_gate'] in answer_ids, True, answers)
        redirects = data.get('htmlInteractionE2E', {}).get('redirects') or []
        assert_case('finish-post-submit-immediate-fired', len(redirects) > 0, True, redirects)
        assert_case('finish-post-submit-immediate-mode', redirects[-1].get('mode'), 'immediate', redirects)
        assert_case('finish-post-submit-immediate-open-in', redirects[-1].get('openIn'), 'blank', redirects)
        assert_case('finish-post-submit-immediate-url', redirects[-1].get('url'), 'https://example.com/next-step', redirects)


def test_logic_hide_question_pipeline_and_interaction():
    with tempfile.TemporaryDirectory(prefix='survey-creator-contract-logic-hide-question.') as tmp:
        tmp_path = Path(tmp)
        source_schema = json.loads((SCHEMAS / 'valid-logic-hide-question-required.json').read_text(encoding='utf-8'))
        proc = subprocess.run([
            'python3', str(PIPELINE),
            '--schema', str(SCHEMAS / 'valid-logic-hide-question-required.json'),
            '--output-dir', str(tmp_path),
            '--auto-repair',
            '--fail-on-high-warning',
            '--json',
        ], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.returncode != 0:
            print(proc.stdout)
            print(proc.stderr, file=sys.stderr)
            raise AssertionError('logic hide question pipeline returned non-zero')
        data = json.loads(proc.stdout)
        assert_case('logic-hide-question-pipeline-valid', data.get('valid'), True)
        assert_case('logic-hide-question-shipReady', data.get('releaseDecision', {}).get('shipReady'), True)
        repaired_schema = get_pipeline_schema(data)
        id_map = build_schema_id_map(source_schema, repaired_schema)
        payload = data.get('htmlInteractionE2E', {}).get('payload') or {}
        answers = payload.get('answers', [])
        answer_ids = {item.get('questionId') for item in answers if isinstance(item, dict)}
        assert_case('logic-hide-question-entry-submitted', id_map['question_path'] in answer_ids, True, answers)
        assert_case('logic-hide-question-required-omitted', id_map['question_hidden_required'] in answer_ids, False, answers)
        target_answer = next((item for item in answers if item.get('questionId') == id_map['question_target_choice']), None)
        assert_case('logic-hide-question-target-submitted', target_answer is not None, True, answers)
        assert_case('logic-hide-question-auto-select-ai', target_answer.get('value') == [{'optionId': id_map['option_target_ai']}], True, target_answer)


def test_logic_show_option_pipeline_and_interaction():
    with tempfile.TemporaryDirectory(prefix='survey-creator-contract-logic-show-option.') as tmp:
        tmp_path = Path(tmp)
        source_schema = json.loads((SCHEMAS / 'valid-logic-show-option-auto-select.json').read_text(encoding='utf-8'))
        proc = subprocess.run([
            'python3', str(PIPELINE),
            '--schema', str(SCHEMAS / 'valid-logic-show-option-auto-select.json'),
            '--output-dir', str(tmp_path),
            '--auto-repair',
            '--fail-on-high-warning',
            '--json',
        ], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.returncode != 0:
            print(proc.stdout)
            print(proc.stderr, file=sys.stderr)
            raise AssertionError('logic show option pipeline returned non-zero')
        data = json.loads(proc.stdout)
        assert_case('logic-show-option-pipeline-valid', data.get('valid'), True)
        assert_case('logic-show-option-shipReady', data.get('releaseDecision', {}).get('shipReady'), True)
        repaired_schema = get_pipeline_schema(data)
        id_map = build_schema_id_map(source_schema, repaired_schema)
        payload = data.get('htmlInteractionE2E', {}).get('payload') or {}
        answers = payload.get('answers', [])
        target_answer = next((item for item in answers if item.get('questionId') == id_map['question_package']), None)
        assert_case('logic-show-option-target-submitted', target_answer is not None, True, answers)
        assert_case('logic-show-option-auto-selected-shown-option', target_answer.get('value') == [{'optionId': id_map['option_package_advanced']}], True, target_answer)


def test_logic_combo_chain_pipeline_and_interaction():
    with tempfile.TemporaryDirectory(prefix='survey-creator-contract-logic-combo-chain.') as tmp:
        tmp_path = Path(tmp)
        source_schema = json.loads((SCHEMAS / 'valid-logic-combo-chain.json').read_text(encoding='utf-8'))
        proc = subprocess.run([
            'python3', str(PIPELINE),
            '--schema', str(SCHEMAS / 'valid-logic-combo-chain.json'),
            '--output-dir', str(tmp_path),
            '--auto-repair',
            '--fail-on-high-warning',
            '--json',
        ], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.returncode != 0:
            print(proc.stdout)
            print(proc.stderr, file=sys.stderr)
            raise AssertionError('logic combo chain pipeline returned non-zero')
        data = json.loads(proc.stdout)
        assert_case('logic-combo-chain-pipeline-valid', data.get('valid'), True)
        assert_case('logic-combo-chain-shipReady', data.get('releaseDecision', {}).get('shipReady'), True)
        repaired_schema = get_pipeline_schema(data)
        id_map = build_schema_id_map(source_schema, repaired_schema)
        html = get_pipeline_output_path(data, 'html').read_text(encoding='utf-8')
        for marker in ["action.type === 'jump_to_page'", 'isQuestionUnavailable(', 'clearUnavailableState()']:
            assert_case(f'logic-combo-chain-html-marker/{marker}', marker in html, True)
        payload = data.get('htmlInteractionE2E', {}).get('payload') or {}
        answers = payload.get('answers', [])
        answer_ids = {item.get('questionId') for item in answers if isinstance(item, dict)}
        assert_case('logic-combo-chain-entry-submitted', id_map['question_route'] in answer_ids, True, answers)
        assert_case('logic-combo-chain-middle-omitted', id_map['question_middle_required_combo'] in answer_ids, False, answers)
        target_answer = next((item for item in answers if item.get('questionId') == id_map['question_target_combo']), None)
        assert_case('logic-combo-chain-target-submitted', target_answer is not None, True, answers)
        assert_case('logic-combo-chain-auto-select-ai', target_answer.get('value') == [{'optionId': id_map['option_target_ai_combo']}], True, target_answer)


def test_logic_conflict_question_last_show_pipeline_and_interaction():
    with tempfile.TemporaryDirectory(prefix='survey-creator-contract-logic-conflict-question.') as tmp:
        tmp_path = Path(tmp)
        source_schema = json.loads((SCHEMAS / 'valid-logic-conflict-question-last-show.json').read_text(encoding='utf-8'))
        proc = subprocess.run([
            'python3', str(PIPELINE),
            '--schema', str(SCHEMAS / 'valid-logic-conflict-question-last-show.json'),
            '--output-dir', str(tmp_path),
            '--auto-repair',
            '--fail-on-high-warning',
            '--json',
        ], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.returncode != 0:
            print(proc.stdout)
            print(proc.stderr, file=sys.stderr)
            raise AssertionError('logic conflict question pipeline returned non-zero')
        data = json.loads(proc.stdout)
        assert_case('logic-conflict-question-pipeline-valid', data.get('valid'), True)
        assert_case('logic-conflict-question-shipReady', data.get('releaseDecision', {}).get('shipReady'), True)
        repaired_schema = get_pipeline_schema(data)
        id_map = build_schema_id_map(source_schema, repaired_schema)
        payload = data.get('htmlInteractionE2E', {}).get('payload') or {}
        answers = payload.get('answers', [])
        answer_ids = {item.get('questionId') for item in answers if isinstance(item, dict)}
        assert_case('logic-conflict-question-gate-submitted', id_map['question_conflict_gate'] in answer_ids, True, answers)
        assert_case('logic-conflict-question-last-show-submitted', id_map['question_conflict_detail'] in answer_ids, True, answers)


def test_logic_conflict_option_last_hide_pipeline_and_interaction():
    with tempfile.TemporaryDirectory(prefix='survey-creator-contract-logic-conflict-option.') as tmp:
        tmp_path = Path(tmp)
        source_schema = json.loads((SCHEMAS / 'valid-logic-conflict-option-last-hide.json').read_text(encoding='utf-8'))
        proc = subprocess.run([
            'python3', str(PIPELINE),
            '--schema', str(SCHEMAS / 'valid-logic-conflict-option-last-hide.json'),
            '--output-dir', str(tmp_path),
            '--auto-repair',
            '--fail-on-high-warning',
            '--json',
        ], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.returncode != 0:
            print(proc.stdout)
            print(proc.stderr, file=sys.stderr)
            raise AssertionError('logic conflict option pipeline returned non-zero')
        data = json.loads(proc.stdout)
        assert_case('logic-conflict-option-pipeline-valid', data.get('valid'), True)
        assert_case('logic-conflict-option-shipReady', data.get('releaseDecision', {}).get('shipReady'), True)
        repaired_schema = get_pipeline_schema(data)
        id_map = build_schema_id_map(source_schema, repaired_schema)
        payload = data.get('htmlInteractionE2E', {}).get('payload') or {}
        answers = payload.get('answers', [])
        target_answer = next((item for item in answers if item.get('questionId') == id_map['question_option_conflict_package']), None)
        assert_case('logic-conflict-option-target-submitted', target_answer is not None, True, answers)
        assert_case('logic-conflict-option-last-hide-hidden-option-omitted', target_answer.get('value') == [{'optionId': id_map['option_option_conflict_basic']}], True, target_answer)


def test_logic_conflict_jump_last_end_pipeline_and_interaction():
    with tempfile.TemporaryDirectory(prefix='survey-creator-contract-logic-conflict-jump.') as tmp:
        tmp_path = Path(tmp)
        source_schema = json.loads((SCHEMAS / 'valid-logic-conflict-jump-last-end.json').read_text(encoding='utf-8'))
        proc = subprocess.run([
            'python3', str(PIPELINE),
            '--schema', str(SCHEMAS / 'valid-logic-conflict-jump-last-end.json'),
            '--output-dir', str(tmp_path),
            '--auto-repair',
            '--fail-on-high-warning',
            '--json',
        ], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.returncode != 0:
            print(proc.stdout)
            print(proc.stderr, file=sys.stderr)
            raise AssertionError('logic conflict jump pipeline returned non-zero')
        data = json.loads(proc.stdout)
        assert_case('logic-conflict-jump-pipeline-valid', data.get('valid'), True)
        assert_case('logic-conflict-jump-shipReady', data.get('releaseDecision', {}).get('shipReady'), True)
        repaired_schema = get_pipeline_schema(data)
        id_map = build_schema_id_map(source_schema, repaired_schema)
        interactions = data.get('htmlInteractionE2E', {}).get('interactions') or []
        visited_ids = {item.get('id') for item in interactions if isinstance(item, dict)}
        assert_case('logic-conflict-jump-last-end-target-not-visited', id_map['question_jump_target_required'] in visited_ids, False, interactions)
        payload = data.get('htmlInteractionE2E', {}).get('payload') or {}
        answers = payload.get('answers', [])
        answer_ids = {item.get('questionId') for item in answers if isinstance(item, dict)}
        assert_case('logic-conflict-jump-gate-submitted', id_map['question_jump_gate'] in answer_ids, True, answers)
        assert_case('logic-conflict-jump-middle-omitted', id_map['question_jump_middle_required'] in answer_ids, False, answers)
        assert_case('logic-conflict-jump-target-omitted', id_map['question_jump_target_required'] in answer_ids, False, answers)


def run_cache_cleanup_browser_check(html_path: Path, id_map):
    node = shutil.which("node")
    if not node:
        raise RuntimeError("Node.js is required for cache cleanup browser validation.")
    option_cleanup_yes_selector = json.dumps(f'input[value="{id_map["option_cleanup_yes"]}"]')
    option_cleanup_no_selector = json.dumps(f'input[value="{id_map["option_cleanup_no"]}"]')
    option_cleanup_detail_text_selector = json.dumps(f'[data-option-id="{id_map["option_cleanup_detail_text"]}"]')
    script = f"""
const path = require('path');
const {{ chromium }} = require('playwright');

(async () => {{
  const htmlPath = process.argv[2];
  const url = 'file://' + path.resolve(htmlPath);
  const browser = await chromium.launch({{ headless: true }});
  const page = await browser.newPage({{ viewport: {{ width: 1280, height: 900 }} }});
  const payloads = [];
  const pageErrors = [];
  page.on('pageerror', err => pageErrors.push(String(err && err.message ? err.message : err)));
  await page.addInitScript(() => {{
    localStorage.clear();
    window.__surveyPayloads = [];
    const originalLog = console.log;
    console.log = (...args) => {{
      try {{
        window.__surveyPayloads.push(args.map((arg) => JSON.parse(JSON.stringify(arg))));
      }} catch (error) {{
        window.__surveyPayloads.push(args.map(String));
      }}
      originalLog(...args);
    }};
    window.alert = () => {{}};
  }});
  await page.goto(url, {{ waitUntil: 'load', timeout: 15000 }});
  await page.waitForTimeout(200);
  await page.locator('.screen.is-active [data-next]').click();
  await page.locator({option_cleanup_yes_selector}).check();
  await page.waitForTimeout(100);
  await page.locator('.screen.is-active [data-next]').click();
  await page.locator({option_cleanup_detail_text_selector}).fill('这是一段之后必须被清理的答案');
  await page.waitForTimeout(100);
  const cacheAfterFill = await page.evaluate(() => {{
    const key = Array.from({{ length: localStorage.length }}, (_, i) => localStorage.key(i)).find((item) => item && item.startsWith('survey_step_cache_'));
    return key ? JSON.parse(localStorage.getItem(key)) : null;
  }});
  await page.locator('.screen.is-active [data-prev]').click();
  await page.locator({option_cleanup_no_selector}).check();
  await page.waitForTimeout(200);
  const cacheAfterHide = await page.evaluate(() => {{
    const key = Array.from({{ length: localStorage.length }}, (_, i) => localStorage.key(i)).find((item) => item && item.startsWith('survey_step_cache_'));
    return key ? JSON.parse(localStorage.getItem(key)) : null;
  }});
  await page.locator('.screen.is-active [data-next]').click();
  await page.locator('.screen.is-active button[type="submit"]').click();
  await page.waitForTimeout(200);
  const finalState = await page.evaluate(() => {{
    const payloads = (window.__surveyPayloads || []).map(args => args[0]).filter(item => item && typeof item === 'object' && item.surveyId && Array.isArray(item.answers));
    const cacheKeys = [];
    for (let i = 0; i < localStorage.length; i++) {{
      const key = localStorage.key(i);
      if (key && key.startsWith('survey_step_cache_')) cacheKeys.push(key);
    }}
    return {{ payload: payloads[payloads.length - 1] || null, cacheKeys }};
  }});
  await browser.close();
  process.stdout.write(JSON.stringify({{ pageErrors, cacheAfterFill, cacheAfterHide, finalState }}));
}})().catch(err => {{
  process.stdout.write(JSON.stringify({{ error: String(err && err.message ? err.message : err) }}));
  process.exit(1);
}});
"""
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as tmp:
        tmp.write(script)
        tmp_path = Path(tmp.name)
    try:
        env = os.environ.copy()
        validators_node_modules = ROOT / 'validators' / 'node_modules'
        env["NODE_PATH"] = str(validators_node_modules) + (os.pathsep + env["NODE_PATH"] if env.get("NODE_PATH") else "")
        proc = subprocess.run([node, str(tmp_path), str(html_path)], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
        try:
            data = json.loads(proc.stdout)
        except json.JSONDecodeError:
            print(proc.stdout)
            print(proc.stderr, file=sys.stderr)
            raise
        return proc.returncode, data, proc.stderr
    finally:
        try:
            tmp_path.unlink()
        except OSError:
            pass


def run_resume_checkpoint_browser_check(html_path: Path, id_map):
    node = shutil.which("node")
    if not node:
        raise RuntimeError("Node.js is required for resume checkpoint browser validation.")
    option_resume_one_a_selector = json.dumps(f'input[value="{id_map["option_resume_one_a"]}"]')
    option_resume_two_a_selector = json.dumps(f'input[value="{id_map["option_resume_two_a"]}"]')
    script = f"""
const path = require('path');
const {{ chromium }} = require('playwright');

(async () => {{
  const htmlPath = process.argv[2];
  const url = 'file://' + path.resolve(htmlPath);
  const browser = await chromium.launch({{ headless: true }});
  const page = await browser.newPage({{ viewport: {{ width: 1280, height: 900 }} }});
  const pageErrors = [];
  page.on('pageerror', err => pageErrors.push(String(err && err.message ? err.message : err)));
  await page.addInitScript(() => {{
    if (!sessionStorage.getItem('__resume_checkpoint_initialized')) {{
      localStorage.clear();
      sessionStorage.setItem('__resume_checkpoint_initialized', '1');
    }}
    window.alert = () => {{}};
  }});
  await page.goto(url, {{ waitUntil: 'load', timeout: 15000 }});
  await page.waitForTimeout(200);
  const initialResumePromptVisible = await page.locator('.resume-overlay.is-visible').count();
  await page.locator('.screen.is-active [data-next]').click();
  await page.locator({option_resume_one_a_selector}).check();
  await page.locator('.screen.is-active [data-next]').click();
  await page.locator({option_resume_two_a_selector}).check();
  await page.locator('.screen.is-active [data-next]').click();
  await page.waitForTimeout(150);
  const cacheBeforeReload = await page.evaluate(() => {{
    const key = Array.from({{ length: localStorage.length }}, (_, i) => localStorage.key(i)).find((item) => item && item.startsWith('survey_step_cache_'));
    return key ? JSON.parse(localStorage.getItem(key)) : null;
  }});

  await page.reload({{ waitUntil: 'load' }});
  await page.waitForTimeout(200);
  const resumePromptVisible = await page.locator('.resume-overlay.is-visible').count();
  const resumePromptText = resumePromptVisible ? await page.locator('.resume-dialog').innerText() : '';
  const activeScreenBeforeDecision = await page.evaluate(() => document.querySelector('.screen.is-active')?.dataset?.screenId || null);
  await page.locator('[data-resume-continue]').click();
  await page.waitForTimeout(200);
  const resumedScreenId = await page.evaluate(() => document.querySelector('.screen.is-active')?.dataset?.screenId || null);

  await page.reload({{ waitUntil: 'load' }});
  await page.waitForTimeout(200);
  await page.locator('[data-resume-restart]').click();
  await page.waitForTimeout(200);
  const restartedScreenId = await page.evaluate(() => document.querySelector('.screen.is-active')?.dataset?.screenId || null);
  const cacheAfterRestart = await page.evaluate(() => {{
    const key = Array.from({{ length: localStorage.length }}, (_, i) => localStorage.key(i)).find((item) => item && item.startsWith('survey_step_cache_'));
    return key ? JSON.parse(localStorage.getItem(key)) : null;
  }});

  await browser.close();
  process.stdout.write(JSON.stringify({{ pageErrors, initialResumePromptVisible, cacheBeforeReload, resumePromptVisible, resumePromptText, activeScreenBeforeDecision, resumedScreenId, restartedScreenId, cacheAfterRestart }}));
}})().catch(err => {{
  process.stdout.write(JSON.stringify({{ error: String(err && err.message ? err.message : err) }}));
  process.exit(1);
}});
"""
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as tmp:
        tmp.write(script)
        tmp_path = Path(tmp.name)
    try:
        env = os.environ.copy()
        validators_node_modules = ROOT / 'validators' / 'node_modules'
        env["NODE_PATH"] = str(validators_node_modules) + (os.pathsep + env["NODE_PATH"] if env.get("NODE_PATH") else "")
        proc = subprocess.run([node, str(tmp_path), str(html_path)], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
        try:
            data = json.loads(proc.stdout)
        except json.JSONDecodeError:
            print(proc.stdout)
            print(proc.stderr, file=sys.stderr)
            raise
        return proc.returncode, data, proc.stderr
    finally:
        try:
            tmp_path.unlink()
        except OSError:
            pass


def test_logic_cache_hidden_cleanup_browser_interaction():
    with tempfile.TemporaryDirectory(prefix='survey-creator-contract-logic-cache-cleanup.') as tmp:
        tmp_path = Path(tmp)
        source_schema = json.loads((SCHEMAS / 'valid-logic-cache-hidden-cleanup.json').read_text(encoding='utf-8'))
        proc = subprocess.run([
            'python3', str(PIPELINE),
            '--schema', str(SCHEMAS / 'valid-logic-cache-hidden-cleanup.json'),
            '--output-dir', str(tmp_path),
            '--auto-repair',
            '--fail-on-high-warning',
            '--json',
        ], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.returncode != 0:
            print(proc.stdout)
            print(proc.stderr, file=sys.stderr)
            raise AssertionError('logic cache cleanup pipeline returned non-zero')
        data = json.loads(proc.stdout)
        assert_case('logic-cache-cleanup-pipeline-valid', data.get('valid'), True)
        assert_case('logic-cache-cleanup-shipReady', data.get('releaseDecision', {}).get('shipReady'), True)
        repaired_schema = get_pipeline_schema(data)
        id_map = build_schema_id_map(source_schema, repaired_schema)
        code, browser_data, stderr = run_cache_cleanup_browser_check(get_pipeline_output_path(data, 'html'), id_map)
        assert_case('logic-cache-cleanup-browser-exit', code == 0, True, stderr)
        assert_case('logic-cache-cleanup-no-page-errors', browser_data.get('pageErrors'), [], browser_data)
        cache_after_fill = browser_data.get('cacheAfterFill') or {}
        assert_case('logic-cache-cleanup-detail-cached-after-fill', id_map['question_cleanup_detail'] in (cache_after_fill.get('answers') or {}), True, cache_after_fill)
        cache_after_hide = browser_data.get('cacheAfterHide') or {}
        assert_case('logic-cache-cleanup-detail-cleared-after-hide', id_map['question_cleanup_detail'] in (cache_after_hide.get('answers') or {}), False, cache_after_hide)
        payload = (browser_data.get('finalState') or {}).get('payload') or {}
        answers = payload.get('answers', [])
        answer_ids = {item.get('questionId') for item in answers if isinstance(item, dict)}
        assert_case('logic-cache-cleanup-gate-submitted', id_map['question_cleanup_gate'] in answer_ids, True, answers)
        assert_case('logic-cache-cleanup-hidden-detail-omitted', id_map['question_cleanup_detail'] in answer_ids, False, answers)
        assert_case('logic-cache-cleanup-cache-removed-after-submit', (browser_data.get('finalState') or {}).get('cacheKeys'), [], browser_data)


def test_resume_checkpoint_browser_interaction():
    with tempfile.TemporaryDirectory(prefix='survey-creator-contract-resume-checkpoint.') as tmp:
        tmp_path = Path(tmp)
        source_schema = json.loads((SCHEMAS / 'valid-resume-checkpoint.json').read_text(encoding='utf-8'))
        proc = subprocess.run([
            'python3', str(PIPELINE),
            '--schema', str(SCHEMAS / 'valid-resume-checkpoint.json'),
            '--output-dir', str(tmp_path),
            '--auto-repair',
            '--fail-on-high-warning',
            '--json',
        ], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.returncode != 0:
            print(proc.stdout)
            print(proc.stderr, file=sys.stderr)
            raise AssertionError('resume checkpoint pipeline returned non-zero')
        data = json.loads(proc.stdout)
        assert_case('resume-checkpoint-pipeline-valid', data.get('valid'), True)
        assert_case('resume-checkpoint-shipReady', data.get('releaseDecision', {}).get('shipReady'), True)
        repaired_schema = get_pipeline_schema(data)
        id_map = build_schema_id_map(source_schema, repaired_schema)
        code, browser_data, stderr = run_resume_checkpoint_browser_check(get_pipeline_output_path(data, 'html'), id_map)
        assert_case('resume-checkpoint-browser-exit', code == 0, True, stderr)
        assert_case('resume-checkpoint-no-page-errors', browser_data.get('pageErrors'), [], browser_data)
        assert_case('resume-checkpoint-no-prompt-first-visit', browser_data.get('initialResumePromptVisible') == 0, True, browser_data)
        assert_case('resume-checkpoint-cache-created', isinstance(browser_data.get('cacheBeforeReload'), dict), True, browser_data)
        assert_case('resume-checkpoint-last-screen-cached', (browser_data.get('cacheBeforeReload') or {}).get('meta', {}).get('lastScreenId'), id_map['question_resume_three'], browser_data)
        assert_case('resume-checkpoint-prompt-visible', browser_data.get('resumePromptVisible') == 1, True, browser_data)
        assert_case('resume-checkpoint-stays-on-survey-before-decision', browser_data.get('activeScreenBeforeDecision'), id_map['survey_resume_checkpoint'], browser_data)
        prompt_text = browser_data.get('resumePromptText') or ''
        assert_case('resume-checkpoint-prompt-copy-continue', '继续上次作答' in prompt_text, True, prompt_text)
        assert_case('resume-checkpoint-prompt-copy-restart', '重新开始作答' in prompt_text, True, prompt_text)
        assert_case('resume-checkpoint-resumed-screen', browser_data.get('resumedScreenId'), id_map['question_resume_three'], browser_data)
        assert_case('resume-checkpoint-restart-screen', browser_data.get('restartedScreenId'), id_map['survey_resume_checkpoint'], browser_data)
        answers_after_restart = (browser_data.get('cacheAfterRestart') or {}).get('answers') or {}
        assert_case('resume-checkpoint-restart-clears-answers', answers_after_restart, {}, browser_data)


def test_logic_input_operators_pipeline_and_interaction():
    with tempfile.TemporaryDirectory(prefix='survey-creator-contract-logic-input-operators.') as tmp:
        tmp_path = Path(tmp)
        source_schema = json.loads((SCHEMAS / 'valid-logic-input-operators.json').read_text(encoding='utf-8'))
        proc = subprocess.run([
            'python3', str(PIPELINE),
            '--schema', str(SCHEMAS / 'valid-logic-input-operators.json'),
            '--output-dir', str(tmp_path),
            '--auto-repair',
            '--fail-on-high-warning',
            '--json',
        ], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.returncode != 0:
            print(proc.stdout)
            print(proc.stderr, file=sys.stderr)
            raise AssertionError('logic input operators pipeline returned non-zero')
        data = json.loads(proc.stdout)
        assert_case('logic-input-operators-pipeline-valid', data.get('valid'), True)
        assert_case('logic-input-operators-shipReady', data.get('releaseDecision', {}).get('shipReady'), True)
        repaired_schema = get_pipeline_schema(data)
        id_map = build_schema_id_map(source_schema, repaired_schema)
        payload = data.get('htmlInteractionE2E', {}).get('payload') or {}
        answers = payload.get('answers', [])
        answer_ids = {item.get('questionId') for item in answers if isinstance(item, dict)}
        expected_ids = {
            id_map['question_text_source'],
            id_map['question_contains_target'],
            id_map['question_not_contains_target'],
            id_map['question_eq_target'],
            id_map['question_neq_target'],
            id_map['question_number_source'],
            id_map['question_gt_target'],
            id_map['question_lt_target'],
        }
        assert_case('logic-input-operators-all-targets-submitted', expected_ids.issubset(answer_ids), True, answers)


def run_not_answered_visibility_browser_check(html_path: Path, id_map):
    node = shutil.which("node")
    if not node:
        raise RuntimeError("Node.js is required for not_answered browser validation.")
    question_not_answered_target_selector = json.dumps(f'[data-screen-id="{id_map["question_not_answered_target"]}"]')
    question_future_source_selector = json.dumps(f'[data-screen-id="{id_map["question_future_source"]}"]')
    option_selection_yes_selector = json.dumps(f'input[value="{id_map["option_selection_yes"]}"]')
    script = f"""
const path = require('path');
const {{ chromium }} = require('playwright');

(async () => {{
  const htmlPath = process.argv[2];
  const url = 'file://' + path.resolve(htmlPath);
  const browser = await chromium.launch({{ headless: true }});
  const page = await browser.newPage({{ viewport: {{ width: 1280, height: 900 }} }});
  const pageErrors = [];
  page.on('pageerror', err => pageErrors.push(String(err && err.message ? err.message : err)));
  await page.addInitScript(() => {{
    localStorage.clear();
    window.alert = () => {{}};
  }});
  await page.goto(url, {{ waitUntil: 'load', timeout: 15000 }});
  await page.waitForTimeout(200);
  const initial = await page.evaluate(() => {{
    const target = document.querySelector({question_not_answered_target_selector});
    const future = document.querySelector({question_future_source_selector});
    return {{
      notAnsweredTargetHidden: target?.classList.contains('is-hidden-by-logic') || target?.dataset.logicHidden === 'true',
      futureHidden: future?.classList.contains('is-hidden-by-logic') || future?.dataset.logicHidden === 'true'
    }};
  }});
  await page.locator('.screen.is-active [data-next]').click();
  await page.locator({option_selection_yes_selector}).check();
  await page.locator('.screen.is-active [data-next]').click();
  for (let i = 0; i < 5; i++) {{
    await page.locator('.screen.is-active input.input, .screen.is-active textarea.textarea').first().fill('示例填写内容');
    await page.locator('.screen.is-active [data-next]').click();
  }}
  await page.locator('.screen.is-active input.input, .screen.is-active textarea.textarea').first().fill('填写 future source 后 not_answered 应失效');
  await page.waitForTimeout(200);
  const afterFutureAnswered = await page.evaluate(() => {{
    const target = document.querySelector({question_not_answered_target_selector});
    return {{
      notAnsweredTargetHidden: target?.classList.contains('is-hidden-by-logic') || target?.dataset.logicHidden === 'true'
    }};
  }});
  await browser.close();
  process.stdout.write(JSON.stringify({{ pageErrors, initial, afterFutureAnswered }}));
}})().catch(err => {{
  process.stdout.write(JSON.stringify({{ error: String(err && err.message ? err.message : err) }}));
  process.exit(1);
}});
"""
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as tmp:
        tmp.write(script)
        tmp_path = Path(tmp.name)
    try:
        env = os.environ.copy()
        validators_node_modules = ROOT / 'validators' / 'node_modules'
        env["NODE_PATH"] = str(validators_node_modules) + (os.pathsep + env["NODE_PATH"] if env.get("NODE_PATH") else "")
        proc = subprocess.run([node, str(tmp_path), str(html_path)], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
        try:
            data = json.loads(proc.stdout)
        except json.JSONDecodeError:
            print(proc.stdout)
            print(proc.stderr, file=sys.stderr)
            raise
        return proc.returncode, data, proc.stderr
    finally:
        try:
            tmp_path.unlink()
        except OSError:
            pass


def test_logic_selection_status_operators_pipeline_and_interaction():
    with tempfile.TemporaryDirectory(prefix='survey-creator-contract-logic-selection-status.') as tmp:
        tmp_path = Path(tmp)
        source_schema = json.loads((SCHEMAS / 'valid-logic-selection-status-operators.json').read_text(encoding='utf-8'))
        proc = subprocess.run([
            'python3', str(PIPELINE),
            '--schema', str(SCHEMAS / 'valid-logic-selection-status-operators.json'),
            '--output-dir', str(tmp_path),
            '--auto-repair',
            '--fail-on-high-warning',
            '--json',
        ], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.returncode != 0:
            print(proc.stdout)
            print(proc.stderr, file=sys.stderr)
            raise AssertionError('logic selection/status operators pipeline returned non-zero')
        data = json.loads(proc.stdout)
        assert_case('logic-selection-status-pipeline-valid', data.get('valid'), True)
        assert_case('logic-selection-status-shipReady', data.get('releaseDecision', {}).get('shipReady'), True)
        repaired_schema = get_pipeline_schema(data)
        id_map = build_schema_id_map(source_schema, repaired_schema)
        payload = data.get('htmlInteractionE2E', {}).get('payload') or {}
        answers = payload.get('answers', [])
        answer_ids = {item.get('questionId') for item in answers if isinstance(item, dict)}
        expected_ids = {
            id_map['question_selection_source'],
            id_map['question_selected_target'],
            id_map['question_not_selected_target'],
            id_map['question_exists_target'],
            id_map['question_not_exists_target'],
            id_map['question_answered_target'],
            id_map['question_future_source'],
        }
        assert_case('logic-selection-status-targets-submitted', expected_ids.issubset(answer_ids), True, answers)
        assert_case('logic-selection-status-not-answered-target-omitted-after-source-filled', id_map['question_not_answered_target'] in answer_ids, False, answers)
        code, browser_data, stderr = run_not_answered_visibility_browser_check(get_pipeline_output_path(data, 'html'), id_map)
        assert_case('logic-not-answered-browser-exit', code == 0, True, stderr)
        assert_case('logic-not-answered-no-page-errors', browser_data.get('pageErrors'), [], browser_data)
        assert_case('logic-not-answered-initial-visible', (browser_data.get('initial') or {}).get('notAnsweredTargetHidden'), False, browser_data)
        assert_case('logic-not-answered-hidden-after-source-answered', (browser_data.get('afterFutureAnswered') or {}).get('notAnsweredTargetHidden'), True, browser_data)


def test_pagination_pipeline_and_interaction():
    with tempfile.TemporaryDirectory(prefix='survey-creator-contract-pagination.') as tmp:
        tmp_path = Path(tmp)
        source_schema = json.loads((SCHEMAS / 'valid-pagination-manual-pages.json').read_text(encoding='utf-8'))
        proc = subprocess.run([
            'python3', str(PIPELINE),
            '--schema', str(SCHEMAS / 'valid-pagination-manual-pages.json'),
            '--output-dir', str(tmp_path),
            '--auto-repair',
            '--fail-on-high-warning',
            '--json',
        ], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.returncode != 0:
            print(proc.stdout)
            print(proc.stderr, file=sys.stderr)
            raise AssertionError('pagination pipeline returned non-zero')
        data = json.loads(proc.stdout)
        assert_case('pagination-pipeline-valid', data.get('valid'), True)
        assert_case('pagination-pipeline-shipReady', data.get('releaseDecision', {}).get('shipReady'), True)
        repaired_schema = get_pipeline_schema(data)
        id_map = build_schema_id_map(source_schema, repaired_schema)
        payload = data.get('htmlInteractionE2E', {}).get('payload') or {}
        answers = payload.get('answers', [])
        answer_ids = {item.get('questionId') for item in answers if isinstance(item, dict)}
        assert_case('pagination-no-separator-node-in-payload', 'page_sep_1' in answer_ids, False, answers)
        assert_case('pagination-all-questions-submitted', {id_map['question_budget'], id_map['question_features'], id_map['question_contact']}.issubset(answer_ids), True, answers)
        rendered_questions = data.get('htmlInteractionE2E', {}).get('renderedQuestions', [])
        rendered_types = {item.get('type') for item in rendered_questions if isinstance(item, dict)}
        assert_case('pagination-rendered-no-page-node', 'page' in rendered_types, False, rendered_questions)


def test_full_pipeline():
    with tempfile.TemporaryDirectory(prefix='survey-creator-contract.') as tmp:
        tmp_path = Path(tmp)
        proc = subprocess.run([
            'python3', str(PIPELINE),
            '--schema', str(SCHEMAS / 'full-all-types.json'),
            '--output-dir', str(tmp_path),
            '--auto-repair',
            '--fail-on-high-warning',
            '--json',
        ], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.returncode != 0:
            print(proc.stdout)
            print(proc.stderr, file=sys.stderr)
            raise AssertionError('full pipeline returned non-zero')
        data = json.loads(proc.stdout)
        assert_case('pipeline-valid', data.get('valid'), True)
        assert_case('pipeline-shipReady', data.get('releaseDecision', {}).get('shipReady'), True)
        html_path = get_pipeline_output_path(data, 'html')
        repaired_schema = get_pipeline_schema(data)
        assert_case('pipeline-html-name-uses-survey-id', html_path.name, f"{repaired_schema.get('survey', {}).get('id')}.html")
        html = html_path.read_text(encoding='utf-8')
        for marker in ["question.type === 'radio'", "question.type === 'checkbox'", "question.type === 'input'", "question.type === 'score'", "question.type === 'nps'", 'renderNpsQuestion', 'assemblePayload()', 'localStorage']:
            assert_case(f'html-marker/{marker}', marker in html, True)
        code, interaction_report, _ = run_json(['python3', str(VALIDATE_INTERACTION_E2E), str(html_path), '--json'])
        assert_case('interaction-e2e-exit', code == 0, True, interaction_report.get('errors'))
        assert_case('interaction-e2e-valid', interaction_report.get('valid'), True, interaction_report.get('errors'))
        submitted_types = {item.get('questionType') for item in (interaction_report.get('payload') or {}).get('answers', [])}
        assert_case('interaction-e2e-all-types-submitted', {'radio', 'checkbox', 'input', 'score', 'nps'}.issubset(submitted_types), True)
        assert_case('pipeline-e2e-desktop-viewport', data.get('htmlE2E', {}).get('viewports', {}).get('desktop', {}).get('valid'), True)
        assert_case('pipeline-e2e-mobile-viewport', data.get('htmlE2E', {}).get('viewports', {}).get('mobile', {}).get('valid'), True)
        assert_case('pipeline-interaction-desktop-viewport', data.get('htmlInteractionE2E', {}).get('viewports', {}).get('desktop', {}).get('valid'), True)
        assert_case('pipeline-interaction-mobile-viewport', data.get('htmlInteractionE2E', {}).get('viewports', {}).get('mobile', {}).get('valid'), True)
        assert_case('pipeline-accessibility-valid', data.get('htmlAccessibility', {}).get('valid'), True, data.get('htmlAccessibility', {}).get('errors'))
        assert_case('pipeline-accessibility-desktop-viewport', data.get('htmlAccessibility', {}).get('viewports', {}).get('desktop', {}).get('valid'), True)
        assert_case('pipeline-accessibility-mobile-viewport', data.get('htmlAccessibility', {}).get('viewports', {}).get('mobile', {}).get('valid'), True)


def test_interaction_payload_includes_query_extra():
    with tempfile.TemporaryDirectory(prefix='survey-creator-contract-query-extra.') as tmp:
        tmp_path = Path(tmp)
        proc = subprocess.run([
            'python3', str(PIPELINE),
            '--schema', str(SCHEMAS / 'full-all-types.json'),
            '--output-dir', str(tmp_path),
            '--auto-repair',
            '--fail-on-high-warning',
            '--json',
        ], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.returncode != 0:
            print(proc.stdout)
            print(proc.stderr, file=sys.stderr)
            raise AssertionError('query extra pipeline returned non-zero')
        data = json.loads(proc.stdout)
        html_path = get_pipeline_output_path(data, 'html')
        code, interaction_report, _ = run_json([
            'python3', str(VALIDATE_INTERACTION_E2E), str(html_path), '--json', '--viewport', 'desktop', '--query',
            'utm_source=wechat&channel=qr&tag=a&tag=b'
        ])
        assert_case('interaction-query-extra-exit', code == 0, True, interaction_report.get('errors'))
        assert_case('interaction-query-extra-valid', interaction_report.get('valid'), True, interaction_report.get('errors'))
        payload = interaction_report.get('payload') or {}
        extra = payload.get('extra') or {}
        assert_case('interaction-query-extra-object', isinstance(extra, dict), True, payload)
        assert_case('interaction-query-extra-utm_source', extra.get('utm_source'), 'wechat', payload)
        assert_case('interaction-query-extra-channel', extra.get('channel'), 'qr', payload)
        assert_case('interaction-query-extra-repeated-array', extra.get('tag'), ['a', 'b'], payload)


def test_interaction_e2e_rejects_bad_runtime_payload():
    with tempfile.TemporaryDirectory(prefix='survey-creator-contract-bad-runtime.') as tmp:
        tmp_path = Path(tmp)
        proc = subprocess.run([
            'python3', str(PIPELINE),
            '--schema', str(SCHEMAS / 'full-all-types.json'),
            '--output-dir', str(tmp_path),
            '--auto-repair',
            '--fail-on-high-warning',
            '--json',
        ], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.returncode != 0:
            print(proc.stdout)
            print(proc.stderr, file=sys.stderr)
            raise AssertionError('setup pipeline for bad-runtime test returned non-zero')
        data = json.loads(proc.stdout)
        html_path = get_pipeline_output_path(data, 'html')
        html = html_path.read_text(encoding='utf-8')
        # Break actual browser-submitted score payload while leaving static sample generation untouched.
        html = html.replace('return { optionId, score: Number(active.dataset.scoreValue) };', 'return { optionId: optionId + "_missing", score: Number(active.dataset.scoreValue) };')
        html_path.write_text(html, encoding='utf-8')
        code, interaction_report, _ = run_json(['python3', str(VALIDATE_INTERACTION_E2E), str(html_path), '--json'])
        assert_case('interaction-e2e-rejects-bad-runtime-exit', code == 0, False, interaction_report.get('errors'))
        assert_case('interaction-e2e-rejects-bad-runtime-valid', interaction_report.get('valid'), False, interaction_report.get('errors'))
        messages = ' '.join(item.get('message', '') for item in interaction_report.get('errors', []))
        assert_case('interaction-e2e-bad-runtime-optionid-detected', 'does not exist under schema question' in messages, True, messages)


def test_pipeline_release_decision_blocks_browser_payload_schema_mismatch():
    schema = json.loads((SCHEMAS / 'full-all-types.json').read_text(encoding='utf-8'))
    payload = json.loads((PAYLOADS / 'valid-all-types.json').read_text(encoding='utf-8'))
    bad_payload = json.loads(json.dumps(payload))
    for answer in bad_payload.get('answers', []):
        if answer.get('questionType') == 'score':
            answer['value'][0]['optionId'] = 'option_score_missing_from_browser'
            break
    interaction_report = {
        'viewports': {
            'desktop': {'payload': bad_payload},
            'mobile': {'payload': payload},
        }
    }
    browser_payload_report = validate_browser_payloads_against_schema(schema, interaction_report)
    assert_case('browser-payload-schema-report-valid', browser_payload_report.get('valid'), False, browser_payload_report.get('errors'))
    full_report = {
        'schema': {'valid': True, 'errors': [], 'warnings': []},
        'html': {'valid': True, 'errors': [], 'warnings': []},
        'htmlSyntax': {'valid': True, 'errors': [], 'warnings': []},
        'htmlE2E': {'valid': True, 'errors': [], 'warnings': []},
        'htmlInteractionE2E': {'valid': True, 'errors': [], 'warnings': []},
        'htmlAccessibility': {'valid': True, 'errors': [], 'warnings': []},
        'userVisible': {'valid': True, 'errors': [], 'warnings': []},
        'payload': {'valid': True, 'errors': [], 'warnings': []},
        'payloadAgainstSchema': {'valid': True, 'errors': [], 'warnings': []},
        'browserPayloadAgainstSchema': browser_payload_report,
        'summary': {'schema': {'warning_severity': {'high': 0, 'medium': 0, 'low': 0}}},
    }
    release_decision = compute_release_decision(full_report)
    assert_case('browser-payload-release-shipready', release_decision.get('shipReady'), False, release_decision)
    blocked_types = {item.get('type') for item in release_decision.get('blockedReasons', []) if isinstance(item, dict)}
    assert_case('browser-payload-release-blocked-type', 'browser-payload-schema-mismatch' in blocked_types, True, release_decision)


def test_auto_repair_html_preserves_requested_style_pack():
    schema = json.loads((SCHEMAS / 'minimal-radio.json').read_text(encoding='utf-8'))
    template_text = DEFAULT_TEMPLATE.read_text(encoding='utf-8')
    html = render_html_from_schema(schema, template_text, style_pack='consumer-campaign')
    broken_html = html.replace('function render() {', 'function render( {', 1)
    report = auto_repair_html(broken_html, style_pack='consumer-campaign')
    assert_case('auto-repair-stylepack-changed', report.get('changed'), True, report)
    assert_case('auto-repair-stylepack-valid', report.get('finalValidation', {}).get('valid'), True, report.get('finalValidation'))
    repaired_html = report.get('html', '')
    assert_case('auto-repair-stylepack-preserved', 'const surveyStylePack = "consumer-campaign";' in repaired_html, True, repaired_html[:500])
    assert_case('auto-repair-stylepack-rerender-path', any(item.get('action') == 'rerendered-from-extracted-schema' for item in report.get('appliedFixes', [])), True, report.get('appliedFixes'))


def test_schema_id_normalizer_normalizes_ids():
    schema = {
        "survey": {
            "type": "survey",
            "id": "survey_legacy",
            "title": "<h1>Legacy survey</h1>",
            "description": "<p>desc</p>",
            "attribute": {"onePageOneQuestion": True, "allowBack": True, "media": []},
        },
        "questions": [
            {
                "type": "radio",
                "id": "question_legacy",
                "title": "<h2>Question</h2>",
                "description": "<p>Choose one</p>",
                "attribute": {"required": True, "random": False, "media": []},
                "option": [
                    {"id": "option_a", "title": "<p>A</p>", "attribute": {}},
                    {
                        "id": "option_b",
                        "title": "<p>B</p>",
                        "attribute": {},
                        "child": [
                            {
                                "type": "input",
                                "id": "child_other",
                                "title": "<p>why</p>",
                                "attribute": {"dataType": "text", "required": True},
                            }
                        ],
                    },
                ],
            }
        ],
        "finish": [
            {"type": "finish", "id": "finish_done", "title": "<h2>Done</h2>", "description": "<p>Thanks</p>", "media": []}
        ],
        "logic": [
            {
                "when": {"questionId": "question_legacy", "operator": "selected", "optionId": "option_b"},
                "action": {"type": "end_survey", "targetQuestionId": "finish_done"},
            }
        ],
    }
    repaired, id_map = normalize_schema_ids(schema)
    assert_case('schema-id-normalizer-changed', len(id_map) > 0, True, id_map)
    report = auto_repair_schema(repaired)
    assert_case('schema-id-normalizer-valid-after-normalize', report.get('finalReport', {}).get('valid'), True, report.get('finalReport'))
    assert_case('schema-id-normalizer-survey-id-format', bool(re.fullmatch(r'survey-\d{10,}', repaired.get('survey', {}).get('id', ''))), True, repaired.get('survey'))
    radio_question = (repaired.get('questions') or [{}])[0]
    assert_case('schema-id-normalizer-radio-id-format', bool(re.fullmatch(r'radio-\d{6}', radio_question.get('id', ''))), True, radio_question)
    radio_options = radio_question.get('option') or []
    assert_case('schema-id-normalizer-radio-option-id-format', all(re.fullmatch(r'radio-\d{6}', item.get('id', '')) for item in radio_options), True, radio_options)
    child = ((radio_options[1].get('child') or [{}])[0]) if len(radio_options) > 1 else {}
    assert_case('schema-id-normalizer-child-id-format', bool(re.fullmatch(r'input-\d{6}', child.get('id', ''))), True, child)
    finish = (repaired.get('finish') or [{}])[0]
    assert_case('schema-id-normalizer-finish-id-format', bool(re.fullmatch(r'finish-\d{6}', finish.get('id', ''))), True, finish)
    logic = (repaired.get('logic') or [{}])[0]
    assert_case('schema-id-normalizer-logic-question-ref-remapped', logic.get('when', {}).get('questionId'), radio_question.get('id'), logic)
    assert_case('schema-id-normalizer-logic-option-ref-remapped', logic.get('when', {}).get('optionId'), radio_options[1].get('id'), logic)
    assert_case('schema-id-normalizer-logic-finish-ref-remapped', logic.get('action', {}).get('targetQuestionId'), finish.get('id'), logic)


def test_pipeline_uses_normalized_survey_id_for_output_name():
    legacy_schema = {
        "survey": {
            "type": "survey",
            "id": "legacy_survey_name",
            "title": "<h1>Legacy naming</h1>",
            "description": "<p>desc</p>",
            "attribute": {"onePageOneQuestion": True, "allowBack": True, "media": []},
        },
        "questions": [
            {
                "type": "radio",
                "id": "legacy_question",
                "title": "<h2>Question</h2>",
                "description": "<p>Pick one</p>",
                "attribute": {"required": True, "random": False, "media": []},
                "option": [
                    {"id": "legacy_option_a", "title": "<p>A</p>", "attribute": {"media": []}},
                    {"id": "legacy_option_b", "title": "<p>B</p>", "attribute": {"media": []}},
                ],
            }
        ],
        "finish": [
            {"type": "finish", "id": "legacy_finish", "title": "<h2>Done</h2>", "description": "<p>Thanks</p>", "media": []}
        ],
        "logic": [],
    }
    with tempfile.TemporaryDirectory(prefix='survey-creator-contract-output-name.') as tmp:
        tmp_path = Path(tmp)
        schema_path = tmp_path / 'legacy.schema.json'
        schema_path.write_text(json.dumps(legacy_schema, ensure_ascii=False, indent=2), encoding='utf-8')
        proc = subprocess.run([
            'python3', str(PIPELINE),
            '--schema', str(schema_path),
            '--output-dir', str(tmp_path),
            '--auto-repair',
            '--fail-on-high-warning',
            '--json',
        ], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.returncode != 0:
            print(proc.stdout)
            print(proc.stderr, file=sys.stderr)
            raise AssertionError('normalized output naming pipeline returned non-zero')
        data = json.loads(proc.stdout)
        repaired_schema = get_pipeline_schema(data)
        survey_id = repaired_schema.get('survey', {}).get('id', '')
        html_path = get_pipeline_output_path(data, 'html')
        assert_case('pipeline-output-name-normalized-survey-id-format', bool(re.fullmatch(r'survey-\d{10,}', survey_id)), True, repaired_schema.get('survey'))
        assert_case('pipeline-output-name-uses-normalized-survey-id', html_path.name, f'{survey_id}.html')



def test_accessibility_rejects_unlabeled_control():
    with tempfile.TemporaryDirectory(prefix='survey-creator-contract-a11y.') as tmp:
        tmp_path = Path(tmp)
        proc = subprocess.run([
            'python3', str(PIPELINE),
            '--schema', str(SCHEMAS / 'full-all-types.json'),
            '--output-dir', str(tmp_path),
            '--auto-repair',
            '--fail-on-high-warning',
            '--json',
        ], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.returncode != 0:
            print(proc.stdout)
            print(proc.stderr, file=sys.stderr)
            raise AssertionError('setup pipeline for a11y test returned non-zero')
        data = json.loads(proc.stdout)
        html_path = get_pipeline_output_path(data, 'html')
        html = html_path.read_text(encoding='utf-8')
        html = html.replace('<label class="option-card"><input', '<div class="option-card"><input', 1)
        html = html.replace('</label>', '</div>', 1)
        html_path.write_text(html, encoding='utf-8')
        code, report, _ = run_json(['python3', str(VALIDATE_ACCESSIBILITY), str(html_path), '--json', '--viewport', 'desktop'])
        assert_case('accessibility-rejects-unlabeled-exit', code == 0, False, report.get('errors'))
        assert_case('accessibility-rejects-unlabeled-valid', report.get('valid'), False, report.get('errors'))
        messages = ' '.join(item.get('message', '') for item in report.get('errors', []))
        assert_case('accessibility-unlabeled-detected', 'accessible name' in messages, True, messages)

def main():
    test_reference_validator_consistency()
    test_schema_cases()
    test_payload_cases()
    test_payload_extra_cases()
    test_payload_against_schema_cases()
    test_logic_pipeline_and_interaction()
    test_logic_jump_page_pipeline_and_interaction()
    test_logic_end_survey_pipeline_and_interaction()
    test_finish_post_submit_immediate_pipeline_and_interaction()
    test_logic_hide_question_pipeline_and_interaction()
    test_logic_show_option_pipeline_and_interaction()
    test_logic_combo_chain_pipeline_and_interaction()
    test_logic_conflict_question_last_show_pipeline_and_interaction()
    test_logic_conflict_option_last_hide_pipeline_and_interaction()
    test_logic_conflict_jump_last_end_pipeline_and_interaction()
    test_logic_cache_hidden_cleanup_browser_interaction()
    test_resume_checkpoint_browser_interaction()
    test_logic_input_operators_pipeline_and_interaction()
    test_logic_selection_status_operators_pipeline_and_interaction()
    test_pagination_pipeline_and_interaction()
    test_full_pipeline()
    test_interaction_payload_includes_query_extra()
    test_interaction_e2e_rejects_bad_runtime_payload()
    test_pipeline_release_decision_blocks_browser_payload_schema_mismatch()
    test_auto_repair_html_preserves_requested_style_pack()
    test_schema_id_normalizer_normalizes_ids()
    test_pipeline_uses_normalized_survey_id_for_output_name()
    test_accessibility_rejects_unlabeled_control()
    print('\n✅ survey-creator-skill contract tests passed')


if __name__ == '__main__':
    main()
