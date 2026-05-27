#!/usr/bin/env python3
import os
import socket
import time
from copy import deepcopy

PAGINATION_PREFIX = "pagination"
SURVEY_PREFIX = "survey"
CANONICAL_ID_DIGITS = 6
CANONICAL_SUFFIX_MIN = 10 ** (CANONICAL_ID_DIGITS - 1)
CANONICAL_SUFFIX_MAX = (10 ** CANONICAL_ID_DIGITS) - 1
CANONICAL_SUFFIX_SPACE = CANONICAL_SUFFIX_MAX - CANONICAL_SUFFIX_MIN + 1
SNOWFLAKE_EPOCH_MS = 1704067200000  # 2024-01-01T00:00:00Z


def canonical_prefix_for_node_type(node_type):
    if node_type == "Pagination":
        return PAGINATION_PREFIX
    return (node_type or "").strip().lower()


def canonical_id_example(prefix):
    if prefix == SURVEY_PREFIX:
        return "survey-190238471928"
    return f"{prefix}-123456"


def is_canonical_schema_id(value, expected_prefix):
    if not isinstance(value, str) or not isinstance(expected_prefix, str) or not expected_prefix:
        return False
    prefix = f"{expected_prefix}-"
    if not value.startswith(prefix):
        return False
    suffix = value[len(prefix):]
    if expected_prefix == SURVEY_PREFIX:
        return len(suffix) >= 10 and suffix.isdigit()
    return len(suffix) == CANONICAL_ID_DIGITS and suffix.isdigit()


class SnowflakeGenerator:
    def __init__(self, worker_id=None, sequence_bits=12):
        self.last_ms = -1
        self.sequence = 0
        self.sequence_bits = sequence_bits
        self.sequence_mask = (1 << sequence_bits) - 1
        if worker_id is None:
            seed = f"{socket.gethostname()}-{os.getpid()}"
            worker_id = sum(ord(ch) for ch in seed) & 0x3FF
        self.worker_id = worker_id & 0x3FF

    def next_number(self):
        now_ms = int(time.time() * 1000)
        if now_ms == self.last_ms:
            self.sequence = (self.sequence + 1) & self.sequence_mask
            if self.sequence == 0:
                while now_ms <= self.last_ms:
                    now_ms = int(time.time() * 1000)
        else:
            self.sequence = 0
        self.last_ms = now_ms
        return ((now_ms - SNOWFLAKE_EPOCH_MS) << (10 + self.sequence_bits)) | (self.worker_id << self.sequence_bits) | self.sequence


class SixDigitSnowflakeGenerator:
    def __init__(self):
        self.base = SnowflakeGenerator(sequence_bits=8)
        self.used_numbers = set()

    def _next_number(self):
        raw = self.base.next_number()
        number = CANONICAL_SUFFIX_MIN + (raw % CANONICAL_SUFFIX_SPACE)
        while number in self.used_numbers:
            raw += 1
            number = CANONICAL_SUFFIX_MIN + (raw % CANONICAL_SUFFIX_SPACE)
        self.used_numbers.add(number)
        return number

    def next_id(self, prefix):
        return f"{prefix}-{self._next_number():0{CANONICAL_ID_DIGITS}d}"


class SurveySnowflakeGenerator:
    def __init__(self):
        self.base = SnowflakeGenerator(sequence_bits=12)

    def next_id(self):
        return f"{SURVEY_PREFIX}-{self.base.next_number()}"


def collect_noncanonical_schema_id_paths(schema):
    issues = []

    def remember(path, expected_prefix, id_value):
        if not expected_prefix:
            return
        if not is_canonical_schema_id(id_value, expected_prefix):
            issues.append({
                "path": path,
                "expectedPrefix": expected_prefix,
                "actual": id_value,
            })

    survey = schema.get("survey") if isinstance(schema, dict) else None
    if isinstance(survey, dict):
        remember("survey.id", canonical_prefix_for_node_type(survey.get("type")), survey.get("id"))

    questions = schema.get("questions") if isinstance(schema, dict) and isinstance(schema.get("questions"), list) else []
    for index, question in enumerate(questions):
        if not isinstance(question, dict):
            continue
        q_type = canonical_prefix_for_node_type(question.get("type"))
        remember(f"questions[{index}].id", q_type, question.get("id"))
        for option_index, option in enumerate(question.get("option") or []):
            if not isinstance(option, dict):
                continue
            remember(f"questions[{index}].option[{option_index}].id", q_type, option.get("id"))
            for child_index, child in enumerate(option.get("child") or []):
                if not isinstance(child, dict):
                    continue
                child_prefix = canonical_prefix_for_node_type(child.get("type") or "input")
                remember(f"questions[{index}].option[{option_index}].child[{child_index}].id", child_prefix, child.get("id"))

    finish_raw = schema.get("finish") if isinstance(schema, dict) else None
    finish_nodes = finish_raw if isinstance(finish_raw, list) else ([finish_raw] if isinstance(finish_raw, dict) else [])
    for index, finish in enumerate(finish_nodes):
        if isinstance(finish, dict):
            remember(f"finish[{index}].id", canonical_prefix_for_node_type(finish.get("type") or "finish"), finish.get("id"))

    return issues


def normalize_schema_ids(schema):
    working = deepcopy(schema)
    short_generator = SixDigitSnowflakeGenerator()
    survey_generator = SurveySnowflakeGenerator()
    id_map = {}

    def remap(old_id, expected_prefix):
        if not isinstance(old_id, str) or not old_id.strip():
            return old_id
        if old_id not in id_map:
            if expected_prefix == SURVEY_PREFIX:
                id_map[old_id] = survey_generator.next_id()
            else:
                id_map[old_id] = short_generator.next_id(expected_prefix)
        return id_map[old_id]

    survey = working.get("survey") if isinstance(working, dict) else None
    if isinstance(survey, dict):
        survey["id"] = remap(survey.get("id"), canonical_prefix_for_node_type(survey.get("type") or "survey"))

    questions = working.get("questions") if isinstance(working, dict) and isinstance(working.get("questions"), list) else []
    for question in questions:
        if not isinstance(question, dict):
            continue
        q_prefix = canonical_prefix_for_node_type(question.get("type"))
        question["id"] = remap(question.get("id"), q_prefix)
        for option in question.get("option") or []:
            if not isinstance(option, dict):
                continue
            option["id"] = remap(option.get("id"), q_prefix)
            for child in option.get("child") or []:
                if not isinstance(child, dict):
                    continue
                child_prefix = canonical_prefix_for_node_type(child.get("type") or "input")
                child["id"] = remap(child.get("id"), child_prefix)

    finish_raw = working.get("finish") if isinstance(working, dict) else None
    finish_nodes = finish_raw if isinstance(finish_raw, list) else ([finish_raw] if isinstance(finish_raw, dict) else [])
    for finish in finish_nodes:
        if isinstance(finish, dict):
            finish["id"] = remap(finish.get("id"), canonical_prefix_for_node_type(finish.get("type") or "finish"))

    for rule in working.get("logic") or []:
        if not isinstance(rule, dict):
            continue
        when = rule.get("when")
        if isinstance(when, dict):
            if isinstance(when.get("questionId"), str) and when["questionId"] in id_map:
                when["questionId"] = id_map[when["questionId"]]
            if isinstance(when.get("optionId"), str) and when["optionId"] in id_map:
                when["optionId"] = id_map[when["optionId"]]
            if isinstance(when.get("optionIds"), list):
                when["optionIds"] = [id_map.get(item, item) for item in when["optionIds"]]
        action = rule.get("action")
        if isinstance(action, dict):
            if isinstance(action.get("targetQuestionId"), str) and action["targetQuestionId"] in id_map:
                action["targetQuestionId"] = id_map[action["targetQuestionId"]]
            if isinstance(action.get("targetOptionId"), str) and action["targetOptionId"] in id_map:
                action["targetOptionId"] = id_map[action["targetOptionId"]]

    return working, id_map


def remap_payload_ids(payload, id_map):
    working = deepcopy(payload)
    if not isinstance(working, dict):
        return working
    if isinstance(working.get("surveyId"), str):
        working["surveyId"] = id_map.get(working["surveyId"], working["surveyId"])
    answers = working.get("answers")
    if not isinstance(answers, list):
        return working
    for answer in answers:
        if not isinstance(answer, dict):
            continue
        if isinstance(answer.get("questionId"), str):
            answer["questionId"] = id_map.get(answer["questionId"], answer["questionId"])
        value = answer.get("value")
        if isinstance(value, dict):
            if isinstance(value.get("optionId"), str):
                value["optionId"] = id_map.get(value["optionId"], value["optionId"])
            if isinstance(value.get("child"), list):
                for child in value["child"]:
                    if isinstance(child, dict) and isinstance(child.get("childId"), str):
                        child["childId"] = id_map.get(child["childId"], child["childId"])
        elif isinstance(value, list):
            for item in value:
                if not isinstance(item, dict):
                    continue
                if isinstance(item.get("optionId"), str):
                    item["optionId"] = id_map.get(item["optionId"], item["optionId"])
                if isinstance(item.get("child"), list):
                    for child in item["child"]:
                        if isinstance(child, dict) and isinstance(child.get("childId"), str):
                            child["childId"] = id_map.get(child["childId"], child["childId"])
    return working
