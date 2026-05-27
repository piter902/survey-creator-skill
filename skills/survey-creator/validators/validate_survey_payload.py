#!/usr/bin/env python3
import json, sys
from pathlib import Path

ALLOWED_QUESTION_TYPES = {"radio", "checkbox", "input", "score", "nps"}
ALLOWED_DATA_TYPES = {"email", "tel", "number", "text", "date", "time", "dateTime", "dateRange", "timeRange", "dateTimeRange"}
RANGE_DATA_TYPES = {"dateRange", "timeRange", "dateTimeRange"}
SCALAR_DATA_TYPES = {"email", "tel", "number", "text", "date", "time", "dateTime"}


def is_plain_object(v):
    return isinstance(v, dict)


def is_non_empty_string(v):
    return isinstance(v, str) and bool(v.strip())


def is_timestamp_number(v):
    return isinstance(v, int) and not isinstance(v, bool) and v >= 0


class Reporter:
    def __init__(self):
        self.errors = []
        self.warnings = []
    def error(self, path, message):
        self.errors.append({"path": path, "message": message})
    def warn(self, path, message):
        self.warnings.append({"path": path, "message": message})
    def result(self):
        return {"valid": len(self.errors) == 0, "errors": self.errors, "warnings": self.warnings}


def assert_allowed_keys(node, allowed_keys, node_path, reporter):
    if not is_plain_object(node):
        return
    for key in node.keys():
        if key not in allowed_keys:
            reporter.error(f"{node_path}.{key}", f'Unsupported field "{key}".')


def validate_range_object(value, node_path, reporter):
    if not is_plain_object(value):
        reporter.error(node_path, "Range value must be an object with start/end.")
        return
    assert_allowed_keys(value, ["start", "end"], node_path, reporter)
    if not is_non_empty_string(value.get("start")):
        reporter.error(f"{node_path}.start", "start must be a non-empty string.")
    if not is_non_empty_string(value.get("end")):
        reporter.error(f"{node_path}.end", "end must be a non-empty string.")


def validate_child_answer(child, node_path, reporter):
    if not is_plain_object(child):
        reporter.error(node_path, "Child answer must be an object.")
        return
    assert_allowed_keys(child, ["childId", "dataType", "value"], node_path, reporter)
    if not is_non_empty_string(child.get("childId")):
        reporter.error(f"{node_path}.childId", "childId must be a non-empty string.")
    dt = child.get("dataType")
    if dt not in ALLOWED_DATA_TYPES:
        reporter.error(f"{node_path}.dataType", f'Unsupported dataType "{dt}".')
        return
    if dt in RANGE_DATA_TYPES:
        validate_range_object(child.get("value"), f"{node_path}.value", reporter)
    else:
        if not is_non_empty_string(child.get("value")):
            reporter.error(f"{node_path}.value", "Scalar child value must be a non-empty string.")


def validate_radio_value(value, node_path, reporter):
    if not is_plain_object(value):
        reporter.error(node_path, "Radio value must be an object.")
        return
    assert_allowed_keys(value, ["optionId", "child"], node_path, reporter)
    if not is_non_empty_string(value.get("optionId")):
        reporter.error(f"{node_path}.optionId", "optionId must be a non-empty string.")
    if value.get("child") is not None:
        if not isinstance(value.get("child"), list):
            reporter.error(f"{node_path}.child", "child must be an array.")
        else:
            for i, item in enumerate(value.get("child")):
                validate_child_answer(item, f"{node_path}.child[{i}]", reporter)


def validate_checkbox_value(value, node_path, reporter):
    if not isinstance(value, list) or not value:
        reporter.error(node_path, "Checkbox value must be a non-empty array.")
        return
    for i, item in enumerate(value):
        path = f"{node_path}[{i}]"
        if not is_plain_object(item):
            reporter.error(path, "Checkbox item must be an object.")
            continue
        assert_allowed_keys(item, ["optionId", "child"], path, reporter)
        if not is_non_empty_string(item.get("optionId")):
            reporter.error(f"{path}.optionId", "optionId must be a non-empty string.")
        if item.get("child") is not None:
            if not isinstance(item.get("child"), list):
                reporter.error(f"{path}.child", "child must be an array.")
            else:
                for j, child in enumerate(item.get("child")):
                    validate_child_answer(child, f"{path}.child[{j}]", reporter)


def validate_input_value(value, node_path, reporter):
    if not isinstance(value, list) or not value:
        reporter.error(node_path, "Input value must be a non-empty array.")
        return
    for i, item in enumerate(value):
        path = f"{node_path}[{i}]"
        if not is_plain_object(item):
            reporter.error(path, "Input item must be an object.")
            continue
        assert_allowed_keys(item, ["optionId", "dataType", "value"], path, reporter)
        if not is_non_empty_string(item.get("optionId")):
            reporter.error(f"{path}.optionId", "optionId must be a non-empty string.")
        dt = item.get("dataType")
        if dt not in ALLOWED_DATA_TYPES:
            reporter.error(f"{path}.dataType", f'Unsupported dataType "{dt}".')
            continue
        if dt in RANGE_DATA_TYPES:
            validate_range_object(item.get("value"), f"{path}.value", reporter)
        else:
            if not is_non_empty_string(item.get("value")):
                reporter.error(f"{path}.value", "Scalar input value must be a non-empty string.")


def validate_score_value(value, node_path, reporter):
    if not isinstance(value, list) or not value:
        reporter.error(node_path, "Score value must be a non-empty array.")
        return
    for i, item in enumerate(value):
        path = f"{node_path}[{i}]"
        if not is_plain_object(item):
            reporter.error(path, "Score item must be an object.")
            continue
        assert_allowed_keys(item, ["optionId", "score"], path, reporter)
        if not is_non_empty_string(item.get("optionId")):
            reporter.error(f"{path}.optionId", "optionId must be a non-empty string.")
        if not isinstance(item.get("score"), (int, float)) or isinstance(item.get("score"), bool):
            reporter.error(f"{path}.score", "score must be numeric.")


def validate_nps_value(value, node_path, reporter):
    if not is_plain_object(value):
        reporter.error(node_path, "NPS value must be an object.")
        return
    assert_allowed_keys(value, ["optionId", "score"], node_path, reporter)
    if not is_non_empty_string(value.get("optionId")):
        reporter.error(f"{node_path}.optionId", "optionId must be a non-empty string.")
    score = value.get("score")
    if not isinstance(score, int) or isinstance(score, bool):
        reporter.error(f"{node_path}.score", "NPS score must be an integer.")


def validate_answer(answer, node_path, reporter):
    if not is_plain_object(answer):
        reporter.error(node_path, "Answer must be an object.")
        return
    assert_allowed_keys(answer, ["questionId", "questionType", "value"], node_path, reporter)
    qid = answer.get("questionId")
    qtype = answer.get("questionType")
    if not is_non_empty_string(qid):
        reporter.error(f"{node_path}.questionId", "questionId must be a non-empty string.")
    if qtype not in ALLOWED_QUESTION_TYPES:
        reporter.error(f"{node_path}.questionType", f'Unsupported questionType "{qtype}".')
        return
    if answer.get("value") is None:
        reporter.error(f"{node_path}.value", "value is required for answered questions.")
        return
    if qtype == "radio":
        validate_radio_value(answer.get("value"), f"{node_path}.value", reporter)
    elif qtype == "checkbox":
        validate_checkbox_value(answer.get("value"), f"{node_path}.value", reporter)
    elif qtype == "input":
        validate_input_value(answer.get("value"), f"{node_path}.value", reporter)
    elif qtype == "score":
        validate_score_value(answer.get("value"), f"{node_path}.value", reporter)
    else:
        validate_nps_value(answer.get("value"), f"{node_path}.value", reporter)


def validate_survey_payload(payload):
    reporter = Reporter()
    if not is_plain_object(payload):
        reporter.error("payload", "Payload must be an object.")
        return reporter.result()
    assert_allowed_keys(payload, ["surveyId", "submittedAt", "extra", "answers"], "payload", reporter)
    if not is_non_empty_string(payload.get("surveyId")):
        reporter.error("payload.surveyId", "surveyId must be a non-empty string.")
    if not is_timestamp_number(payload.get("submittedAt")):
        reporter.error("payload.submittedAt", "submittedAt must be a non-negative integer timestamp.")
    extra = payload.get("extra")
    if extra is not None:
        if not is_plain_object(extra):
            reporter.error("payload.extra", "extra must be an object when present.")
        else:
            for key, value in extra.items():
                if not is_non_empty_string(key):
                    reporter.error("payload.extra", "extra keys must be non-empty strings.")
                    continue
                if isinstance(value, list):
                    if not value:
                        reporter.error(f"payload.extra.{key}", "extra array values must not be empty.")
                    for idx, item in enumerate(value):
                        if not is_non_empty_string(item):
                            reporter.error(f"payload.extra.{key}[{idx}]", "extra array items must be non-empty strings.")
                elif not is_non_empty_string(value):
                    reporter.error(f"payload.extra.{key}", "extra values must be non-empty strings or arrays of non-empty strings.")
    answers = payload.get("answers")
    if not isinstance(answers, list):
        reporter.error("payload.answers", "answers must be an array.")
    else:
        seen = set()
        for i, answer in enumerate(answers):
            path = f"payload.answers[{i}]"
            validate_answer(answer, path, reporter)
            if is_plain_object(answer) and is_non_empty_string(answer.get("questionId")):
                qid = answer.get("questionId")
                if qid in seen:
                    reporter.error(f"{path}.questionId", f'Duplicate questionId "{qid}" in answers.')
                seen.add(qid)
    return reporter.result()


def print_human(report):
    print("✅ Survey payload is valid." if report["valid"] else "❌ Survey payload is invalid.")
    if report["errors"]:
        print("\nErrors:")
        for i, item in enumerate(report["errors"], start=1):
            print(f"{i}. [{item['path']}] {item['message']}")
    if report["warnings"]:
        print("\nWarnings:")
        for i, item in enumerate(report["warnings"], start=1):
            print(f"{i}. [{item['path']}] {item['message']}")


def main():
    args = sys.argv[1:]
    json_output = "--json" in args
    file_arg = next((a for a in args if not a.startswith("--")), None)
    try:
        raw = Path(file_arg).read_text(encoding="utf-8") if file_arg else sys.stdin.read()
        payload = json.loads(raw)
    except FileNotFoundError as e:
        print(f"Failed to read payload input: {e}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)
    report = validate_survey_payload(payload)
    if json_output:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_human(report)
    sys.exit(0 if report["valid"] else 1)


if __name__ == "__main__":
    main()
