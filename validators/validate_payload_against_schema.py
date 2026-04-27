#!/usr/bin/env python3
"""Validate a submitted survey payload against a concrete survey schema.

This is the identity/semantic guardrail that complements validate_survey_payload.py:
- validate_survey_payload.py checks the generic submission contract shape.
- this file checks whether every submitted id/value is legal for this exact schema.
"""
import argparse
import json
import re
import sys
from pathlib import Path

from validate_survey_payload import validate_survey_payload, is_non_empty_string
from validate_survey_schema import validate_survey_schema

RANGE_DATA_TYPES = {"dateRange", "timeRange", "dateTimeRange"}
SCALAR_DATA_TYPES = {"email", "tel", "number", "text", "date", "time", "dateTime"}


class Reporter:
    def __init__(self):
        self.errors = []
        self.warnings = []

    def error(self, path, message):
        self.errors.append({"path": path, "message": message})

    def warn(self, path, message, severity="medium", code=None, suggestion=None):
        item = {"path": path, "message": message, "severity": severity}
        if code:
            item["code"] = code
        if suggestion:
            item["suggestion"] = suggestion
        self.warnings.append(item)

    def result(self):
        return {"valid": len(self.errors) == 0, "errors": self.errors, "warnings": self.warnings}


def load_json(path_str):
    return json.loads(Path(path_str).read_text(encoding="utf-8"))


def attr(node):
    return node.get("attribute") if isinstance(node, dict) and isinstance(node.get("attribute"), dict) else {}


def options(question):
    return question.get("option") if isinstance(question.get("option"), list) else []


def children(option):
    return option.get("child") if isinstance(option.get("child"), list) else []


def effective_data_type(node):
    return attr(node).get("dataType") or "text"


def normalize_schema(schema):
    finish = schema.get("finish")
    if isinstance(finish, dict):
        schema = {**schema, "finish": [finish]}
    return schema


def index_schema(schema):
    schema = normalize_schema(schema)
    question_map = {}
    for q in schema.get("questions") or []:
        if not isinstance(q, dict) or not isinstance(q.get("id"), str):
            continue
        option_map = {}
        child_by_option = {}
        for opt in options(q):
            if not isinstance(opt, dict) or not isinstance(opt.get("id"), str):
                continue
            option_map[opt["id"]] = opt
            child_by_option[opt["id"]] = {c.get("id"): c for c in children(opt) if isinstance(c, dict) and isinstance(c.get("id"), str)}
        question_map[q["id"]] = {"question": q, "options": option_map, "childrenByOption": child_by_option}
    return question_map


def is_answered_scalar(value):
    return isinstance(value, str) and bool(value.strip())


def is_answered_range(value):
    return isinstance(value, dict) and is_answered_scalar(value.get("start")) and is_answered_scalar(value.get("end"))


def validate_datatype_value(data_type, value, path, reporter):
    if data_type in RANGE_DATA_TYPES:
        if not is_answered_range(value):
            reporter.error(path, f"{data_type} value must include non-empty start/end.")
        return
    if not is_answered_scalar(value):
        reporter.error(path, f"{data_type} value must be a non-empty string.")
        return
    if data_type == "email" and not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", value):
        reporter.error(path, "email value is not a valid email-like string.")
    if data_type == "number":
        try:
            float(value)
        except (TypeError, ValueError):
            reporter.error(path, "number value must be numeric.")
    if data_type == "tel" and not re.match(r"^[0-9+()\-\s]{5,}$", value):
        reporter.error(path, "tel value is not a valid telephone-like string.")


def score_values_from_scope(scope, step):
    if not isinstance(scope, list) or len(scope) != 2:
        return None
    start, end = scope
    if not isinstance(start, (int, float)) or not isinstance(end, (int, float)):
        return None
    if step not in (0.5, 1):
        return None
    values = []
    current = float(start)
    # tolerate decimal math; cap prevents infinite loops if upstream validation is bypassed.
    for _ in range(1000):
        if current > float(end) + 1e-9:
            break
        values.append(round(current, 2))
        current += float(step)
    return values


def validate_score(score, option, path, reporter, integer_only=False):
    if not isinstance(score, (int, float)) or isinstance(score, bool):
        reporter.error(path, "score must be numeric.")
        return
    if integer_only and not isinstance(score, int):
        reporter.error(path, "score must be an integer.")
        return
    opt_attr = attr(option)
    scope = opt_attr.get("scope") or ([0, 10] if integer_only else [1, 5])
    step = 1 if integer_only else opt_attr.get("step", 1)
    legal_values = score_values_from_scope(scope, step)
    if legal_values is None:
        reporter.error(path, "Cannot validate score because schema option scope/step is invalid.")
        return
    normalized_score = round(float(score), 2)
    if normalized_score not in legal_values:
        reporter.error(path, f"score {score} is outside schema scope/step {scope} step {step}.")


def validate_child_answers(answer_children, selected_option, qid, answer_path, reporter):
    child_map = {c.get("id"): c for c in children(selected_option) if isinstance(c, dict)}
    seen = set()
    if answer_children is None:
        answer_children = []
    if not isinstance(answer_children, list):
        reporter.error(answer_path, "child must be an array when present.")
        return
    for cidx, child_answer in enumerate(answer_children):
        child_path = f"{answer_path}[{cidx}]"
        if not isinstance(child_answer, dict):
            continue
        child_id = child_answer.get("childId")
        child_schema = child_map.get(child_id)
        if not child_schema:
            reporter.error(f"{child_path}.childId", f"Submitted childId {child_id} does not exist under selected option for question {qid}.")
            continue
        if child_id in seen:
            reporter.error(f"{child_path}.childId", f"Duplicate childId {child_id} under selected option.")
        seen.add(child_id)
        expected_dt = effective_data_type(child_schema)
        if child_answer.get("dataType") != expected_dt:
            reporter.error(f"{child_path}.dataType", f"dataType {child_answer.get('dataType')} does not match schema child dataType {expected_dt}.")
        validate_datatype_value(expected_dt, child_answer.get("value"), f"{child_path}.value", reporter)
    for child_id, child_schema in child_map.items():
        if attr(child_schema).get("required") is True and child_id not in seen:
            reporter.error(answer_path, f"Required child input {child_id} is missing for selected option.")


def validate_radio_answer(answer, meta, answer_path, reporter):
    question = meta["question"]
    value = answer.get("value")
    if not isinstance(value, dict):
        return
    option_id = value.get("optionId")
    option = meta["options"].get(option_id)
    if not option:
        reporter.error(f"{answer_path}.value.optionId", f"Submitted optionId {option_id} does not exist under question {question.get('id')}.")
        return
    validate_child_answers(value.get("child"), option, question.get("id"), f"{answer_path}.value.child", reporter)


def validate_checkbox_answer(answer, meta, answer_path, reporter):
    question = meta["question"]
    value = answer.get("value")
    if not isinstance(value, list):
        return
    seen = set()
    selected_options = []
    for vidx, item in enumerate(value):
        item_path = f"{answer_path}.value[{vidx}]"
        if not isinstance(item, dict):
            continue
        option_id = item.get("optionId")
        option = meta["options"].get(option_id)
        if not option:
            reporter.error(f"{item_path}.optionId", f"Submitted optionId {option_id} does not exist under question {question.get('id')}.")
            continue
        if option_id in seen:
            reporter.error(f"{item_path}.optionId", f"Duplicate selected optionId {option_id}.")
        seen.add(option_id)
        selected_options.append(option)
        validate_child_answers(item.get("child"), option, question.get("id"), f"{item_path}.child", reporter)
    exclusive_selected = [o.get("id") for o in selected_options if attr(o).get("exclusive") is True]
    if exclusive_selected and len(selected_options) > 1:
        reporter.error(f"{answer_path}.value", f"Exclusive option(s) {exclusive_selected} cannot be submitted with other options.")
    mutual_selected = [o.get("id") for o in selected_options if attr(o).get("mutual-exclusion") is True]
    if len(mutual_selected) > 1:
        reporter.error(f"{answer_path}.value", f"Only one mutual-exclusion option can be submitted, got {mutual_selected}.")


def validate_input_answer(answer, meta, answer_path, reporter):
    question = meta["question"]
    value = answer.get("value")
    if not isinstance(value, list):
        return
    seen = set()
    for vidx, item in enumerate(value):
        item_path = f"{answer_path}.value[{vidx}]"
        if not isinstance(item, dict):
            continue
        option_id = item.get("optionId")
        option = meta["options"].get(option_id)
        if not option:
            reporter.error(f"{item_path}.optionId", f"Submitted optionId {option_id} does not exist under question {question.get('id')}.")
            continue
        if option_id in seen:
            reporter.error(f"{item_path}.optionId", f"Duplicate input optionId {option_id}.")
        seen.add(option_id)
        expected_dt = effective_data_type(option)
        if item.get("dataType") != expected_dt:
            reporter.error(f"{item_path}.dataType", f"dataType {item.get('dataType')} does not match schema option dataType {expected_dt}.")
        validate_datatype_value(expected_dt, item.get("value"), f"{item_path}.value", reporter)
    if attr(question).get("required") is True:
        for option_id in meta["options"]:
            if option_id not in seen:
                reporter.error(f"{answer_path}.value", f"Required input option {option_id} is missing.")


def validate_score_answer(answer, meta, answer_path, reporter):
    question = meta["question"]
    value = answer.get("value")
    if not isinstance(value, list):
        return
    seen = set()
    for vidx, item in enumerate(value):
        item_path = f"{answer_path}.value[{vidx}]"
        if not isinstance(item, dict):
            continue
        option_id = item.get("optionId")
        option = meta["options"].get(option_id)
        if not option:
            reporter.error(f"{item_path}.optionId", f"Submitted optionId {option_id} does not exist under question {question.get('id')}.")
            continue
        if option_id in seen:
            reporter.error(f"{item_path}.optionId", f"Duplicate score optionId {option_id}.")
        seen.add(option_id)
        validate_score(item.get("score"), option, f"{item_path}.score", reporter)
    if attr(question).get("required") is True:
        for option_id in meta["options"]:
            if option_id not in seen:
                reporter.error(f"{answer_path}.value", f"Required score option {option_id} is missing.")


def validate_nps_answer(answer, meta, answer_path, reporter):
    question = meta["question"]
    value = answer.get("value")
    if not isinstance(value, dict):
        return
    option_id = value.get("optionId")
    option = meta["options"].get(option_id)
    if not option:
        reporter.error(f"{answer_path}.value.optionId", f"Submitted optionId {option_id} does not exist under question {question.get('id')}.")
        return
    validate_score(value.get("score"), option, f"{answer_path}.value.score", reporter, integer_only=True)


def validate_payload_against_schema(schema, payload, include_base_validation=True, enforce_required_questions=True):
    reporter = Reporter()
    schema = normalize_schema(schema)

    if include_base_validation:
        schema_report = validate_survey_schema(schema)
        if not schema_report.get("valid"):
            for idx, item in enumerate(schema_report.get("errors", []), start=1):
                reporter.error(f"schema.contract[{idx}]", f"Schema is invalid: [{item.get('path')}] {item.get('message')}")
        payload_report = validate_survey_payload(payload)
        if not payload_report.get("valid"):
            for idx, item in enumerate(payload_report.get("errors", []), start=1):
                reporter.error(f"payload.contract[{idx}]", f"Payload contract is invalid: [{item.get('path')}] {item.get('message')}")
            return reporter.result()

    survey = schema.get("survey") if isinstance(schema, dict) else {}
    if not isinstance(survey, dict):
        reporter.error("schema.survey", "Schema survey must be an object.")
        return reporter.result()
    if payload.get("surveyId") != survey.get("id"):
        reporter.error("payload.surveyId", f"Payload surveyId {payload.get('surveyId')} does not match schema survey id {survey.get('id')}.")

    question_map = index_schema(schema)
    answer_map = {}
    for idx, answer in enumerate(payload.get("answers") or []):
        if not isinstance(answer, dict):
            continue
        qid = answer.get("questionId")
        answer_path = f"payload.answers[{idx}]"
        meta = question_map.get(qid)
        if not meta:
            reporter.error(f"{answer_path}.questionId", f"Submitted questionId {qid} does not exist in schema.")
            continue
        if answer.get("questionType") != meta["question"].get("type"):
            reporter.error(f"{answer_path}.questionType", f"Submitted questionType {answer.get('questionType')} does not match schema type {meta['question'].get('type')}.")
            continue
        answer_map[qid] = answer
        qtype = answer.get("questionType")
        if qtype == "radio":
            validate_radio_answer(answer, meta, answer_path, reporter)
        elif qtype == "checkbox":
            validate_checkbox_answer(answer, meta, answer_path, reporter)
        elif qtype == "input":
            validate_input_answer(answer, meta, answer_path, reporter)
        elif qtype == "score":
            validate_score_answer(answer, meta, answer_path, reporter)
        elif qtype == "nps":
            validate_nps_answer(answer, meta, answer_path, reporter)

    if enforce_required_questions:
        for qid, meta in question_map.items():
            question = meta["question"]
            if attr(question).get("required") is True and qid not in answer_map:
                reporter.error("payload.answers", f"Required question {qid} ({question.get('type')}) is missing from answers.")

    return reporter.result()


def print_human(report):
    print("✅ Payload matches schema." if report["valid"] else "❌ Payload does not match schema.")
    if report.get("errors"):
        print("\nErrors:")
        for i, item in enumerate(report["errors"], start=1):
            print(f"{i}. [{item['path']}] {item['message']}")
    if report.get("warnings"):
        print("\nWarnings:")
        for i, item in enumerate(report["warnings"], start=1):
            print(f"{i}. [{item['path']}] {item['message']}")


def main():
    parser = argparse.ArgumentParser(description="Validate a submitted survey payload against its concrete survey schema.")
    parser.add_argument("schema", help="Path to schema JSON")
    parser.add_argument("payload", help="Path to payload JSON")
    parser.add_argument("--json", action="store_true", help="Print machine-readable report")
    parser.add_argument("--skip-base-validation", action="store_true", help="Skip generic schema/payload contract validators")
    args = parser.parse_args()
    try:
        schema = load_json(args.schema)
        payload = load_json(args.payload)
    except FileNotFoundError as e:
        print(f"Failed to read input: {e}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)

    report = validate_payload_against_schema(schema, payload, include_base_validation=not args.skip_base_validation)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_human(report)
    sys.exit(0 if report["valid"] else 1)


if __name__ == "__main__":
    main()
