#!/usr/bin/env python3
import json, sys
import time
from pathlib import Path

RANGE_DEFAULTS = {
    'dateRange': {'start': '2026-04-22', 'end': '2026-04-29'},
    'timeRange': {'start': '09:00', 'end': '18:00'},
    'dateTimeRange': {'start': '2026-04-22T09:00', 'end': '2026-04-22T18:00'},
}
SCALAR_DEFAULTS = {
    'email': 'name@example.com',
    'tel': '13800000000',
    'number': '42',
    'text': '示例填写内容',
    'date': '2026-04-22',
    'time': '09:00',
    'dateTime': '2026-04-22T09:00',
}


def load_schema(path_str):
    return json.loads(Path(path_str).read_text(encoding='utf-8'))


def normalize_finish(schema):
    finish = schema.get('finish')
    if isinstance(finish, dict):
        schema['finish'] = [finish]
    return schema


def example_value_for_datatype(data_type):
    if data_type in RANGE_DEFAULTS:
        return RANGE_DEFAULTS[data_type]
    return SCALAR_DEFAULTS.get(data_type or 'text', SCALAR_DEFAULTS['text'])


def build_child_answers(children):
    answers = []
    for child in children or []:
        attr = child.get('attribute') or {}
        dt = attr.get('dataType', 'text')
        answers.append({
            'childId': child['id'],
            'dataType': dt,
            'value': example_value_for_datatype(dt),
        })
    return answers


def build_answer(question):
    qtype = question.get('type')
    if qtype == 'radio':
        option = (question.get('option') or [None])[0]
        if not option:
            return None
        value = {'optionId': option['id']}
        child = build_child_answers(option.get('child'))
        if child:
            value['child'] = child
        return {'questionId': question['id'], 'questionType': 'radio', 'value': value}

    if qtype == 'checkbox':
        options = question.get('option') or []
        if not options:
            return None
        # Generate a legal sample: never combine exclusive options with others,
        # and select at most one mutual-exclusion option. Prefer normal options
        # so the sample exercises ordinary multi-select payload shape.
        normal_options = [o for o in options if not (o.get('attribute') or {}).get('exclusive') and not (o.get('attribute') or {}).get('mutual-exclusion')]
        mutual_options = [o for o in options if (o.get('attribute') or {}).get('mutual-exclusion') and not (o.get('attribute') or {}).get('exclusive')]
        exclusive_options = [o for o in options if (o.get('attribute') or {}).get('exclusive')]
        selected_options = normal_options[:2]
        if not selected_options and mutual_options:
            selected_options = mutual_options[:1]
        if not selected_options and exclusive_options:
            selected_options = exclusive_options[:1]
        selected = []
        for option in selected_options:
            item = {'optionId': option['id']}
            child = build_child_answers(option.get('child'))
            if child:
                item['child'] = child
            selected.append(item)
        return {'questionId': question['id'], 'questionType': 'checkbox', 'value': selected}

    if qtype == 'input':
        values = []
        for option in question.get('option') or []:
            attr = option.get('attribute') or {}
            dt = attr.get('dataType', 'text')
            values.append({
                'optionId': option['id'],
                'dataType': dt,
                'value': example_value_for_datatype(dt),
            })
        if not values:
            return None
        return {'questionId': question['id'], 'questionType': 'input', 'value': values}

    if qtype == 'score':
        values = []
        for option in question.get('option') or []:
            scope = (option.get('attribute') or {}).get('scope') or [1, 5]
            score = scope[-1] if isinstance(scope, list) and scope else 5
            values.append({
                'optionId': option['id'],
                'score': score,
            })
        if not values:
            return None
        return {'questionId': question['id'], 'questionType': 'score', 'value': values}

    if qtype == 'nps':
        option = (question.get('option') or [None])[0]
        if not option:
            return None
        scope = (option.get('attribute') or {}).get('scope') or [0, 10]
        score = int(scope[-1]) if isinstance(scope, list) and scope else 10
        return {'questionId': question['id'], 'questionType': 'nps', 'value': {'optionId': option['id'], 'score': score}}

    return None


def generate_payload(schema):
    schema = normalize_finish(schema)
    survey = schema.get('survey') or {}
    answers = []
    for question in schema.get('questions') or []:
        answer = build_answer(question)
        if answer:
            answers.append(answer)
    return {
        'surveyId': survey.get('id', 'survey_unknown'),
        'submittedAt': int(time.time() * 1000),
        'extra': {},
        'answers': answers,
    }


def main():
    args = sys.argv[1:]
    if not args:
        print('Usage: generate_sample_payload.py /absolute/path/to/schema.json [--out /absolute/path/to/output.json]', file=sys.stderr)
        sys.exit(1)
    schema_path = args[0]
    out_path = None
    if '--out' in args:
        idx = args.index('--out')
        try:
            out_path = args[idx + 1]
        except IndexError:
            print('--out requires a path', file=sys.stderr)
            sys.exit(1)
    payload = generate_payload(load_schema(schema_path))
    content = json.dumps(payload, ensure_ascii=False, indent=2)
    if out_path:
        Path(out_path).write_text(content, encoding='utf-8')
        print(out_path)
    else:
        print(content)


if __name__ == '__main__':
    main()
