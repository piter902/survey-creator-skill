#!/usr/bin/env python3
import json, re, sys
from pathlib import Path

ALLOWED_MEDIA_TYPES = {"image", "audio", "video"}
ALLOWED_QUESTION_TYPES = {"radio", "checkbox", "input", "score", "nps"}
PAGINATION_TYPE = "Pagination"
ALLOWED_DATA_TYPES = {"email", "tel", "number", "text", "date", "time", "dateTime", "dateRange", "timeRange", "dateTimeRange"}
ALLOWED_LOGIC_OPERATORS = {"selected", "not_selected", "contains", "not_contains", "exists", "not_exists", "answered", "not_answered", "eq", "neq", "gt", "lt"}
ALLOWED_LOGIC_ACTIONS = {"show_question", "hide_question", "show_option", "hide_option", "auto_select_option", "jump_to_question", "jump_to_page", "end_survey"}
ID_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*$")
MEDIA_URL_PATTERN = re.compile(r"^(https?://|data:(image|audio|video)/)", re.I)


def is_plain_object(v):
    return isinstance(v, dict)


def is_non_empty_string(v):
    return isinstance(v, str) and bool(v.strip())


def is_bool(v):
    return isinstance(v, bool)


def is_integer_like(v):
    return isinstance(v, int) or (isinstance(v, str) and v.isdigit())


class Reporter:
    def __init__(self):
        self.errors = []
        self.warnings = []

    def error(self, path, message):
        self.errors.append({"path": path, "message": message})

    def warn(self, path, message, severity="medium", code=None, suggestion=None, fix_hint=None):
        item = {"path": path, "message": message, "severity": severity}
        if code:
            item["code"] = code
        if suggestion:
            item["suggestion"] = suggestion
        if fix_hint:
            item["fixHint"] = fix_hint
        self.warnings.append(item)

    def result(self, normalized=None):
        return {
            "valid": len(self.errors) == 0,
            "errors": self.errors,
            "warnings": self.warnings,
            "normalized": normalized,
        }


def assert_allowed_keys(node, allowed_keys, node_path, reporter):
    if not is_plain_object(node):
        return
    for key in node.keys():
        if key not in allowed_keys:
            reporter.error(f"{node_path}.{key}", f'Unsupported field "{key}".')


def validate_media_list(media, node_path, reporter, required=False):
    if media is None:
        if required:
            reporter.error(node_path, "Media must be an array.")
        return
    if not isinstance(media, list):
        reporter.error(node_path, "Media must be an array.")
        return
    for i, item in enumerate(media):
        item_path = f"{node_path}[{i}]"
        if not is_plain_object(item):
            reporter.error(item_path, "Media item must be an object.")
            continue
        assert_allowed_keys(item, ["type", "url"], item_path, reporter)
        if item.get("type") not in ALLOWED_MEDIA_TYPES:
            reporter.error(f"{item_path}.type", "Media type must be image, audio, or video.")
        if not is_non_empty_string(item.get("url")):
            reporter.error(f"{item_path}.url", "Media url must be a non-empty string.")
        elif not MEDIA_URL_PATTERN.match(item.get("url")):
            reporter.error(f"{item_path}.url", "Media url must start with http://, https://, or a data:image/audio/video URL.")


def validate_rich_text_string(value, node_path, reporter, required=True):
    if value is None:
        if required:
            reporter.error(node_path, "Field is required and must be a string.")
        return
    if not isinstance(value, str):
        reporter.error(node_path, "Field must be a string.")


def normalize_rich_text(value):
    if not isinstance(value, str):
        return ""
    import re
    plain = re.sub(r"<[^>]+>", "", value)
    plain = plain.replace("&nbsp;", " ")
    return " ".join(plain.split()).strip()

def has_meaningful_rich_text(value):
    return bool(normalize_rich_text(value))


def rich_text_tag_count(value):
    if not isinstance(value, str):
        return 0
    import re
    return len(re.findall(r"<[^>]+>", value))


def looks_like_other_label(value):
    plain = normalize_rich_text(value).lower()
    tokens = ["其他", "其它", "other", "please specify", "please describe", "补充", "说明", "以上都不", "都不明显", "没有明显", "无明显", "都没有", "不适用", "暂无", "無", "无特别", "暂无特别", "没有特别", "none", "not applicable", "none of the above"]
    return any(token in plain for token in tokens)


def looks_like_long_form_prompt(value):
    plain = normalize_rich_text(value)
    return len(plain) >= 24 or any(token in plain for token in ["请详细", "请描述", "why", "原因", "建议", "意见", "详细说明"])


def looks_like_email_placeholder(value):
    plain = normalize_rich_text(value).lower()
    return "@" in plain or "email" in plain or "邮箱" in plain


def looks_like_tel_placeholder(value):
    plain = normalize_rich_text(value).lower()
    return any(token in plain for token in ["phone", "mobile", "tel", "手机号", "联系电话", "电话"])


def looks_like_date_placeholder(value):
    plain = normalize_rich_text(value).lower()
    return any(token in plain for token in ["yyyy", "mm", "dd", "日期", "date", "时间", "time"])


def is_range_type(data_type):
    return data_type in {"dateRange", "timeRange", "dateTimeRange"}



def register_id(id_value, path_name, reporter, id_map):
    if not is_non_empty_string(id_value):
        reporter.error(path_name, "id must be a non-empty string.")
        return
    if not ID_PATTERN.match(id_value):
        reporter.error(path_name, "id must start with a letter and contain only letters, numbers, underscores, or hyphens.")
        return
    if id_value in id_map:
        reporter.error(path_name, f'Duplicate id "{id_value}" already used at {id_map[id_value]}.')
    else:
        id_map[id_value] = path_name


def validate_input_like_attribute(attr, node_path, reporter):
    if not is_plain_object(attr):
        reporter.error(node_path, "attribute must be an object.")
        return
    assert_allowed_keys(attr, ["required", "placeholder", "maxLength", "minLength", "dataType", "media"], node_path, reporter)
    if attr.get("required") is not None and not is_bool(attr.get("required")):
        reporter.error(f"{node_path}.required", "required must be boolean.")
    if attr.get("placeholder") is not None and not isinstance(attr.get("placeholder"), str):
        reporter.error(f"{node_path}.placeholder", "placeholder must be a string.")
    if attr.get("maxLength") is not None and not is_integer_like(attr.get("maxLength")):
        reporter.error(f"{node_path}.maxLength", "maxLength must be an integer or numeric string.")
    if attr.get("minLength") is not None and not is_integer_like(attr.get("minLength")):
        reporter.error(f"{node_path}.minLength", "minLength must be an integer or numeric string.")
    if attr.get("dataType") is not None and attr.get("dataType") not in ALLOWED_DATA_TYPES:
        reporter.error(f"{node_path}.dataType", f'Unsupported dataType "{attr.get("dataType")}".')
    if attr.get("media") is not None:
        validate_media_list(attr.get("media"), f"{node_path}.media", reporter)
    if is_integer_like(attr.get("maxLength")) and is_integer_like(attr.get("minLength")):
        if int(attr.get("maxLength")) < int(attr.get("minLength")):
            reporter.error(node_path, "maxLength cannot be smaller than minLength.")


def validate_child(child, child_path, reporter, id_map):
    if not is_plain_object(child):
        reporter.error(child_path, "Child must be an object.")
        return
    assert_allowed_keys(child, ["type", "id", "title", "attribute"], child_path, reporter)
    if child.get("type") != "input":
        reporter.error(f"{child_path}.type", 'Child type must be input.')
    register_id(child.get("id"), f"{child_path}.id", reporter, id_map)
    validate_rich_text_string(child.get("title"), f"{child_path}.title", reporter, True)
    if child.get("attribute") is not None:
        validate_input_like_attribute(child.get("attribute"), f"{child_path}.attribute", reporter)


def validate_option_attribute(question_type, attr, path_name, reporter):
    if not is_plain_object(attr):
        reporter.error(path_name, "attribute must be an object.")
        return
    keys = ["random", "media"] + (["exclusive", "mutual-exclusion"] if question_type == "checkbox" else [])
    assert_allowed_keys(attr, keys, path_name, reporter)
    if attr.get("random") is not None and not is_bool(attr.get("random")):
        reporter.error(f"{path_name}.random", "random must be boolean.")
    if attr.get("media") is not None:
        validate_media_list(attr.get("media"), f"{path_name}.media", reporter)
    if question_type == "checkbox":
        if attr.get("exclusive") is not None and not is_bool(attr.get("exclusive")):
            reporter.error(f"{path_name}.exclusive", "exclusive must be boolean.")
        if attr.get("mutual-exclusion") is not None and not is_bool(attr.get("mutual-exclusion")):
            reporter.error(f"{path_name}.mutual-exclusion", "mutual-exclusion must be boolean.")
        if attr.get("exclusive") is True and attr.get("mutual-exclusion") is True:
            reporter.error(path_name, "exclusive and mutual-exclusion cannot both be true on the same option.")


def validate_question_base(question, question_path, reporter, id_map):
    if not is_plain_object(question):
        reporter.error(question_path, "Question must be an object.")
        return False
    register_id(question.get("id"), f"{question_path}.id", reporter, id_map)
    validate_rich_text_string(question.get("title"), f"{question_path}.title", reporter, True)
    validate_rich_text_string(question.get("description"), f"{question_path}.description", reporter, False)
    return True


def validate_selection_question(question, question_path, reporter, id_map):
    q_type = question.get("type")
    assert_allowed_keys(question, ["type", "id", "title", "description", "attribute", "option"], question_path, reporter)
    if not validate_question_base(question, question_path, reporter, id_map):
        return
    attr = question.get("attribute")
    if not is_plain_object(attr):
        reporter.error(f"{question_path}.attribute", "attribute must be an object.")
    else:
        assert_allowed_keys(attr, ["required", "random", "media"], f"{question_path}.attribute", reporter)
        if attr.get("required") is not None and not is_bool(attr.get("required")):
            reporter.error(f"{question_path}.attribute.required", "required must be boolean.")
        if attr.get("media") is not None:
            validate_media_list(attr.get("media"), f"{question_path}.attribute.media", reporter)
        if attr.get("random") is not None and not is_bool(attr.get("random")):
            reporter.error(f"{question_path}.attribute.random", "random must be boolean.")
    options = question.get("option")
    if not isinstance(options, list) or not options:
        reporter.error(f"{question_path}.option", "option must be a non-empty array.")
        return
    for i, option in enumerate(options):
        option_path = f"{question_path}.option[{i}]"
        if not is_plain_object(option):
            reporter.error(option_path, "Option must be an object.")
            continue
        assert_allowed_keys(option, ["title", "id", "child", "attribute"], option_path, reporter)
        register_id(option.get("id"), f"{option_path}.id", reporter, id_map)
        validate_rich_text_string(option.get("title"), f"{option_path}.title", reporter, True)
        if option.get("attribute") is not None:
            validate_option_attribute(q_type, option.get("attribute"), f"{option_path}.attribute", reporter)
        if option.get("child") is not None:
            children = option.get("child")
            if not isinstance(children, list) or not children:
                reporter.error(f"{option_path}.child", "child must be a non-empty array when present.")
            else:
                for j, child in enumerate(children):
                    validate_child(child, f"{option_path}.child[{j}]", reporter, id_map)


def validate_input_question(question, question_path, reporter, id_map):
    assert_allowed_keys(question, ["type", "id", "title", "description", "attribute", "option"], question_path, reporter)
    if not validate_question_base(question, question_path, reporter, id_map):
        return
    attr = question.get("attribute")
    if not is_plain_object(attr):
        reporter.error(f"{question_path}.attribute", "attribute must be an object.")
    else:
        assert_allowed_keys(attr, ["required", "media"], f"{question_path}.attribute", reporter)
        if attr.get("required") is not None and not is_bool(attr.get("required")):
            reporter.error(f"{question_path}.attribute.required", "required must be boolean.")
        if attr.get("media") is not None:
            validate_media_list(attr.get("media"), f"{question_path}.attribute.media", reporter)
    options = question.get("option")
    if not isinstance(options, list) or not options:
        reporter.error(f"{question_path}.option", "option must be a non-empty array.")
        return
    for i, option in enumerate(options):
        option_path = f"{question_path}.option[{i}]"
        if not is_plain_object(option):
            reporter.error(option_path, "Option must be an object.")
            continue
        assert_allowed_keys(option, ["title", "id", "attribute"], option_path, reporter)
        register_id(option.get("id"), f"{option_path}.id", reporter, id_map)
        validate_rich_text_string(option.get("title"), f"{option_path}.title", reporter, True)
        validate_input_like_attribute(option.get("attribute"), f"{option_path}.attribute", reporter)


def is_number_like(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def validate_score_question(question, question_path, reporter, id_map):
    assert_allowed_keys(question, ["type", "id", "title", "description", "attribute", "option"], question_path, reporter)
    if not validate_question_base(question, question_path, reporter, id_map):
        return
    attr = question.get("attribute")
    if not is_plain_object(attr):
        reporter.error(f"{question_path}.attribute", "attribute must be an object.")
    else:
        assert_allowed_keys(attr, ["required", "media"], f"{question_path}.attribute", reporter)
        if attr.get("required") is not None and not is_bool(attr.get("required")):
            reporter.error(f"{question_path}.attribute.required", "required must be boolean.")
        if attr.get("media") is not None:
            validate_media_list(attr.get("media"), f"{question_path}.attribute.media", reporter)
    options = question.get("option")
    if not isinstance(options, list) or not options:
        reporter.error(f"{question_path}.option", "option must be a non-empty array.")
        return
    for i, option in enumerate(options):
        option_path = f"{question_path}.option[{i}]"
        if not is_plain_object(option):
            reporter.error(option_path, "Option must be an object.")
            continue
        assert_allowed_keys(option, ["title", "id", "attribute"], option_path, reporter)
        register_id(option.get("id"), f"{option_path}.id", reporter, id_map)
        validate_rich_text_string(option.get("title"), f"{option_path}.title", reporter, True)
        option_attr = option.get("attribute")
        if not is_plain_object(option_attr):
            reporter.error(f"{option_path}.attribute", "attribute must be an object.")
            continue
        assert_allowed_keys(option_attr, ["scope", "step", "scoreDesc", "media"], f"{option_path}.attribute", reporter)
        scope = option_attr.get("scope")
        if not isinstance(scope, list) or len(scope) != 2 or not all(is_number_like(x) for x in scope):
            reporter.error(f"{option_path}.attribute.scope", "scope must be a [min, max] numeric array.")
        elif float(scope[0]) >= float(scope[1]):
            reporter.error(f"{option_path}.attribute.scope", "scope min must be smaller than max.")
        step = option_attr.get("step")
        if step not in {0.5, 1}:
            reporter.error(f"{option_path}.attribute.step", "step must be 0.5 or 1.")
        if option_attr.get("media") is not None:
            validate_media_list(option_attr.get("media"), f"{option_path}.attribute.media", reporter)
        score_desc = option_attr.get("scoreDesc")
        if score_desc is not None:
            if not is_plain_object(score_desc):
                reporter.error(f"{option_path}.attribute.scoreDesc", "scoreDesc must be an object keyed by score string.")
            else:
                if isinstance(scope, list) and len(scope) == 2 and all(is_number_like(x) for x in scope) and step in {0.5, 1}:
                    valid_scores = set()
                    cur = float(scope[0])
                    max_v = float(scope[1])
                    while cur <= max_v + 1e-9:
                        valid_scores.add(str(int(cur)) if float(cur).is_integer() else str(cur))
                        cur += float(step)
                    for key, value in score_desc.items():
                        if key not in valid_scores:
                            reporter.error(f"{option_path}.attribute.scoreDesc.{key}", "scoreDesc key is outside the allowed scope/step values.")
                        if not isinstance(value, str):
                            reporter.error(f"{option_path}.attribute.scoreDesc.{key}", "scoreDesc value must be string.")


def nps_range_desc_matches(key, scope):
    if not isinstance(key, str) or "-" not in key:
        return False, None
    left, right = key.split("-", 1)
    try:
        start = int(left)
        end = int(right)
    except ValueError:
        return False, None
    if start > end:
        return False, None
    if not isinstance(scope, list) or len(scope) != 2 or not all(is_number_like(x) for x in scope):
        return False, None
    return int(scope[0]) <= start <= end <= int(scope[1]), (start, end)


def validate_nps_question(question, question_path, reporter, id_map):
    assert_allowed_keys(question, ["type", "id", "title", "description", "attribute", "option"], question_path, reporter)
    if not validate_question_base(question, question_path, reporter, id_map):
        return
    attr = question.get("attribute")
    if not is_plain_object(attr):
        reporter.error(f"{question_path}.attribute", "attribute must be an object.")
    else:
        assert_allowed_keys(attr, ["required", "media"], f"{question_path}.attribute", reporter)
        if attr.get("required") is not None and not is_bool(attr.get("required")):
            reporter.error(f"{question_path}.attribute.required", "required must be boolean.")
        if attr.get("media") is not None:
            validate_media_list(attr.get("media"), f"{question_path}.attribute.media", reporter)
    options = question.get("option")
    if not isinstance(options, list) or not options:
        reporter.error(f"{question_path}.option", "option must be a non-empty array.")
        return
    for i, option in enumerate(options):
        option_path = f"{question_path}.option[{i}]"
        if not is_plain_object(option):
            reporter.error(option_path, "Option must be an object.")
            continue
        assert_allowed_keys(option, ["id", "attribute"], option_path, reporter)
        register_id(option.get("id"), f"{option_path}.id", reporter, id_map)
        option_attr = option.get("attribute")
        if not is_plain_object(option_attr):
            reporter.error(f"{option_path}.attribute", "attribute must be an object.")
            continue
        assert_allowed_keys(option_attr, ["scope", "scoreDesc", "media"], f"{option_path}.attribute", reporter)
        scope = option_attr.get("scope")
        if not isinstance(scope, list) or len(scope) != 2 or not all(is_number_like(x) for x in scope):
            reporter.error(f"{option_path}.attribute.scope", "scope must be a [min, max] numeric array.")
        elif float(scope[0]) >= float(scope[1]):
            reporter.error(f"{option_path}.attribute.scope", "scope min must be smaller than max.")
        elif int(scope[0]) != float(scope[0]) or int(scope[1]) != float(scope[1]):
            reporter.error(f"{option_path}.attribute.scope", "NPS scope values must be integers.")
        if option_attr.get("media") is not None:
            validate_media_list(option_attr.get("media"), f"{option_path}.attribute.media", reporter)
        score_desc = option_attr.get("scoreDesc")
        if score_desc is not None:
            if not is_plain_object(score_desc):
                reporter.error(f"{option_path}.attribute.scoreDesc", "scoreDesc must be an object keyed by score ranges such as 0-6.")
            else:
                for key, value in score_desc.items():
                    ok, _ = nps_range_desc_matches(key, scope)
                    if not ok:
                        reporter.error(f"{option_path}.attribute.scoreDesc.{key}", "scoreDesc key must be a valid range within scope, such as 0-6.")
                    if not isinstance(value, str):
                            reporter.error(f"{option_path}.attribute.scoreDesc.{key}", "scoreDesc value must be string.")


def validate_pagination_node(question, question_path, reporter, id_map):
    assert_allowed_keys(question, ["type", "id"], question_path, reporter)
    if question.get("type") != PAGINATION_TYPE:
        reporter.error(f"{question_path}.type", f'{PAGINATION_TYPE} node type must equal "{PAGINATION_TYPE}".')
    register_id(question.get("id"), f"{question_path}.id", reporter, id_map)



def normalize_finish_nodes(finish, reporter=None):
    if is_plain_object(finish):
        if reporter:
            reporter.warn(
                "finish",
                "finish object has been normalized to a one-item array; prefer finish: [{...}] as the canonical shape.",
                "low",
                "legacy-finish-object",
                "Wrap the finish node in an array so future logic can target specific ending screens.",
                'Change "finish": {...} to "finish": [{...}].',
            )
        return [finish]
    if isinstance(finish, list):
        if not finish:
            if reporter:
                reporter.error("finish", "finish must contain at least one finish object.")
            return []
        return finish
    if reporter:
        reporter.error("finish", "finish must be an array of finish objects.")
    return []


def collect_schema_maps(schema):
    question_map = {}
    option_map = {}
    for question in schema.get("questions") or []:
        if not is_plain_object(question) or not is_non_empty_string(question.get("id")):
            continue
        if question.get("type") == PAGINATION_TYPE:
            continue
        qid = question.get("id")
        question_map[qid] = question
        per_question = {}
        for option in question.get("option") or []:
            if is_plain_object(option) and is_non_empty_string(option.get("id")):
                per_question[option.get("id")] = option
        option_map[qid] = per_question
    finish_map = {}
    for finish in normalize_finish_nodes(schema.get("finish")):
        if is_plain_object(finish) and is_non_empty_string(finish.get("id")):
            finish_map[finish.get("id")] = finish
    return question_map, option_map, finish_map


def validate_logic_rule(rule, rule_path, reporter, question_map, option_map, finish_map):
    if not is_plain_object(rule):
        reporter.error(rule_path, "logic rule must be an object.")
        return
    assert_allowed_keys(rule, ["id", "when", "action"], rule_path, reporter)
    if rule.get("id") is not None and not is_non_empty_string(rule.get("id")):
        reporter.error(f"{rule_path}.id", "logic rule id must be a non-empty string when present.")

    when = rule.get("when")
    if not is_plain_object(when):
        reporter.error(f"{rule_path}.when", "logic.when must be an object.")
    else:
        assert_allowed_keys(when, ["questionId", "operator", "value", "optionId", "optionIds"], f"{rule_path}.when", reporter)
        question_id = when.get("questionId")
        operator = when.get("operator")
        if not is_non_empty_string(question_id):
            reporter.error(f"{rule_path}.when.questionId", "logic.when.questionId must be a non-empty string.")
        elif question_id not in question_map:
            reporter.error(f"{rule_path}.when.questionId", f'logic source questionId "{question_id}" does not exist.')
        if operator not in ALLOWED_LOGIC_OPERATORS:
            reporter.error(f"{rule_path}.when.operator", f'Unsupported logic operator "{operator}".')
        if operator in {"selected", "not_selected"}:
            if not is_non_empty_string(when.get("optionId")):
                reporter.error(f"{rule_path}.when.optionId", f'{operator} requires when.optionId.')
            elif question_id in option_map and when.get("optionId") not in option_map.get(question_id, {}):
                reporter.error(f"{rule_path}.when.optionId", f'Option "{when.get("optionId")}" does not exist under source question {question_id}.')
        if operator in {"exists", "not_exists"}:
            option_ids = when.get("optionIds")
            if not isinstance(option_ids, list) or not option_ids or not all(is_non_empty_string(v) for v in option_ids):
                reporter.error(f"{rule_path}.when.optionIds", f'{operator} requires a non-empty optionIds string array.')
            else:
                for idx, option_id in enumerate(option_ids):
                    if question_id in option_map and option_id not in option_map.get(question_id, {}):
                        reporter.error(f"{rule_path}.when.optionIds[{idx}]", f'Option "{option_id}" does not exist under source question {question_id}.')
        if operator in {"contains", "not_contains"}:
            if when.get("value") is None and when.get("optionId") is None:
                reporter.error(f"{rule_path}.when", f'{operator} requires when.value or when.optionId.')
            if when.get("optionId") is not None and not is_non_empty_string(when.get("optionId")):
                reporter.error(f"{rule_path}.when.optionId", "when.optionId must be a non-empty string.")
        if operator in {"eq", "neq", "gt", "lt"} and when.get("value") is None:
            reporter.error(f"{rule_path}.when.value", f'{operator} requires when.value.')
        if operator in {"answered", "not_answered"}:
            for extra_key in ["value", "optionId", "optionIds"]:
                if when.get(extra_key) is not None:
                    reporter.warn(f"{rule_path}.when.{extra_key}", f'{operator} ignores {extra_key}; remove it for clarity.', "low", "logic-extra-condition-field", "Remove unused condition fields for answered/not_answered rules.", "Keep only questionId and operator for answered/not_answered.")

    action = rule.get("action")
    if not is_plain_object(action):
        reporter.error(f"{rule_path}.action", "logic.action must be an object.")
        return
    assert_allowed_keys(action, ["type", "targetQuestionId", "targetOptionId"], f"{rule_path}.action", reporter)
    action_type = action.get("type")
    if action_type not in ALLOWED_LOGIC_ACTIONS:
        reporter.error(f"{rule_path}.action.type", f'Unsupported logic action "{action_type}".')
        return
    if action_type in {"show_question", "hide_question", "jump_to_question", "jump_to_page"}:
        target_qid = action.get("targetQuestionId")
        if not is_non_empty_string(target_qid):
            reporter.error(f"{rule_path}.action.targetQuestionId", f'{action_type} requires action.targetQuestionId.')
        elif target_qid not in question_map:
            reporter.error(f"{rule_path}.action.targetQuestionId", f'Target question "{target_qid}" does not exist.')
    if action_type in {"show_option", "hide_option", "auto_select_option"}:
        target_qid = action.get("targetQuestionId")
        target_oid = action.get("targetOptionId")
        if not is_non_empty_string(target_qid):
            reporter.error(f"{rule_path}.action.targetQuestionId", f'{action_type} requires action.targetQuestionId.')
        elif target_qid not in question_map:
            reporter.error(f"{rule_path}.action.targetQuestionId", f'Target question "{target_qid}" does not exist.')
        if not is_non_empty_string(target_oid):
            reporter.error(f"{rule_path}.action.targetOptionId", f'{action_type} requires action.targetOptionId.')
        elif target_qid in option_map and target_oid not in option_map.get(target_qid, {}):
            reporter.error(f"{rule_path}.action.targetOptionId", f'Target option "{target_oid}" does not exist under target question {target_qid}.')
        if action_type == "auto_select_option" and target_qid in question_map:
            target_question = question_map.get(target_qid) or {}
            if target_question.get("type") not in {"radio", "checkbox"}:
                reporter.error(f"{rule_path}.action.targetQuestionId", "auto_select_option can only target radio or checkbox questions.")
    if action_type == "end_survey":
        target_finish_id = action.get("targetQuestionId")
        if target_finish_id is not None:
            if not is_non_empty_string(target_finish_id):
                reporter.error(f"{rule_path}.action.targetQuestionId", "end_survey targetQuestionId must be a non-empty finish id when provided.")
            elif target_finish_id not in finish_map:
                reporter.error(f"{rule_path}.action.targetQuestionId", f'end_survey target finish "{target_finish_id}" does not exist.')
        if action.get("targetOptionId") is not None:
            reporter.warn(f"{rule_path}.action.targetOptionId", "end_survey ignores targetOptionId; remove it for clarity.", "low", "logic-extra-action-field", "Remove unused targetOptionId for end_survey rules.", "Keep only action.type or optionally action.targetQuestionId pointing to a finish id.")


def validate_logic_rules(schema, reporter):
    logic = schema.get("logic")
    if logic is None:
        return
    if not isinstance(logic, list):
        reporter.error("logic", "logic must be an array when present.")
        return
    question_map, option_map, finish_map = collect_schema_maps(schema)
    seen_ids = set()
    for idx, rule in enumerate(logic):
        path = f"logic[{idx}]"
        validate_logic_rule(rule, path, reporter, question_map, option_map, finish_map)
        if is_plain_object(rule) and is_non_empty_string(rule.get("id")):
            if rule.get("id") in seen_ids:
                reporter.error(f"{path}.id", f'Duplicate logic rule id "{rule.get("id")}".')
            seen_ids.add(rule.get("id"))


def validate_survey_node(survey, reporter, id_map):
    path = "survey"
    if not is_plain_object(survey):
        reporter.error(path, "survey must be an object.")
        return
    assert_allowed_keys(survey, ["type", "id", "title", "description", "attribute"], path, reporter)
    if survey.get("type") != "survey":
        reporter.error(f"{path}.type", 'survey.type must equal "survey".')
    register_id(survey.get("id"), f"{path}.id", reporter, id_map)
    validate_rich_text_string(survey.get("title"), f"{path}.title", reporter, True)
    validate_rich_text_string(survey.get("description"), f"{path}.description", reporter, False)
    attr = survey.get("attribute")
    if not is_plain_object(attr):
        reporter.error(f"{path}.attribute", "survey.attribute must be an object.")
        return
    assert_allowed_keys(attr, ["onePageOneQuestion", "allowBack", "media"], f"{path}.attribute", reporter)
    if not is_bool(attr.get("onePageOneQuestion")):
        reporter.error(f"{path}.attribute.onePageOneQuestion", "onePageOneQuestion must be boolean.")
    if not is_bool(attr.get("allowBack")):
        reporter.error(f"{path}.attribute.allowBack", "allowBack must be boolean.")
    if attr.get("media") is not None:
        validate_media_list(attr.get("media"), f"{path}.attribute.media", reporter)


def validate_finish_nodes(finish_raw, reporter, id_map):
    finish_nodes = normalize_finish_nodes(finish_raw, reporter)
    normalized = []
    for idx, finish in enumerate(finish_nodes):
        path = f"finish[{idx}]"
        if not is_plain_object(finish):
            reporter.error(path, "finish item must be an object.")
            continue
        assert_allowed_keys(finish, ["type", "id", "title", "description", "media"], path, reporter)
        if finish.get("type") != "finish":
            reporter.error(f"{path}.type", 'finish.type must equal "finish".')
        if finish.get("id") is not None:
            register_id(finish.get("id"), f"{path}.id", reporter, id_map)
        validate_rich_text_string(finish.get("title"), f"{path}.title", reporter, True)
        validate_rich_text_string(finish.get("description"), f"{path}.description", reporter, False)
        if finish.get("media") is not None:
            validate_media_list(finish.get("media"), f"{path}.media", reporter)
        normalized.append(finish)
    return normalized


def semantic_lint(schema, reporter):
    survey = schema.get("survey") if is_plain_object(schema) else None
    questions = schema.get("questions") if is_plain_object(schema) and isinstance(schema.get("questions"), list) else []
    finish = schema.get("finish") if is_plain_object(schema) else None

    if is_plain_object(survey):
        if not has_meaningful_rich_text(survey.get("title")):
            reporter.warn("survey.title", "survey.title is structurally valid but semantically empty.", "high", "empty-rich-text-title", "Write a meaningful survey heading that tells the respondent what this survey is about.", "Replace empty tags or whitespace-only HTML with a real title string.")
        if rich_text_tag_count(survey.get("title")) > 20:
            reporter.warn("survey.title", "survey.title contains unusually complex rich text; keep welcome titles lightweight.", "medium", "complex-rich-text-title", "Simplify the title and move decorative or long-form content into description.", "Reduce nested tags and keep the intro title short.")
        if isinstance(survey.get("description"), str) and len(survey.get("description")) > 3000:
            reporter.warn("survey.description", "survey.description is unusually long for a welcome block.", "medium", "long-survey-description", "Shorten the intro copy and keep details concise.", "Move detailed instructions to question descriptions or help text.")
        if survey.get("attribute", {}).get("allowBack") is True and survey.get("attribute", {}).get("onePageOneQuestion") is not True:
            reporter.warn("survey.attribute.allowBack", "allowBack is enabled while onePageOneQuestion is false; back navigation usually only matters in step mode.", "low", "allowback-without-step-mode", "Either enable onePageOneQuestion or disable allowBack.", "Keep allowBack=true only when each question is rendered as an individual step.")

    finish_nodes = normalize_finish_nodes(finish)
    for idx, finish_node in enumerate(finish_nodes):
        if not is_plain_object(finish_node):
            continue
        finish_path = f"finish[{idx}]"
        if not has_meaningful_rich_text(finish_node.get("title")):
            reporter.warn(f"{finish_path}.title", "finish.title is structurally valid but semantically empty.", "high", "empty-finish-title", "Use a completion-oriented title such as thank-you, submitted, or next-step confirmation.", "Replace empty HTML with a meaningful finish heading.")
        desc = finish_node.get("description")
        if isinstance(desc, str):
            lower = desc.lower()
            if any(token in lower for token in ["必填", "单选", "多选", "下一页", "question", "题目"]):
                reporter.warn(f"{finish_path}.description", "finish.description may contain question-like or flow-control copy; finish should usually be end-state messaging.", "medium", "finish-looks-like-question-copy", "Rewrite the finish description as completion feedback or next-step guidance.", "Remove question instructions, pagination hints, and required-field wording from the finish block.")

    pagination_indices = []
    for i, question in enumerate(questions):
        if is_plain_object(question) and question.get("type") == PAGINATION_TYPE:
            pagination_indices.append(i)

    if pagination_indices:
        if pagination_indices[0] == 0:
            reporter.warn("questions[0]", "The first node is Pagination; it has no practical effect at the beginning.", "low", "leading-pagination", "Remove the leading Pagination node.", "Start with an answerable question before any Pagination separator.")
        if pagination_indices[-1] == len(questions) - 1:
            reporter.warn(f"questions[{pagination_indices[-1]}]", "The last node is Pagination; it has no practical effect at the end.", "low", "trailing-pagination", "Remove the trailing Pagination node.", "End the question list with an answerable question.")
        for idx in pagination_indices:
            if idx + 1 < len(questions) and is_plain_object(questions[idx + 1]) and questions[idx + 1].get("type") == PAGINATION_TYPE:
                reporter.warn(f"questions[{idx + 1}]", "Consecutive Pagination nodes detected; only one separator is needed.", "low", "duplicate-pagination", "Remove the redundant Pagination node.", "Use a single Pagination node between page groups.")

    for i, question in enumerate(questions):
        q_path = f"questions[{i}]"
        q_type = question.get("type") if is_plain_object(question) else None
        if q_type == PAGINATION_TYPE:
            continue
        options = question.get("option") if is_plain_object(question) and isinstance(question.get("option"), list) else []
        question_attr = question.get("attribute") if is_plain_object(question) and is_plain_object(question.get("attribute")) else {}
        title = question.get("title") if is_plain_object(question) else None
        if not has_meaningful_rich_text(title):
            reporter.warn(f"{q_path}.title", "Question title is structurally valid but semantically empty.", "high", "empty-question-title", "Provide a concrete question prompt the respondent can answer.", "Replace empty or whitespace-only rich text with a meaningful question title.")
        if isinstance(question.get("description"), str) and len(question.get("description")) > 2000:
            reporter.warn(f"{q_path}.description", "Question description is unusually long; consider simplifying instructions.", "medium", "long-question-description", "Shorten the question helper copy and move extra context elsewhere.", "Keep descriptions focused on just the guidance needed to answer the question.")

        if q_type in {"radio", "checkbox"} and len(options) < 2:
            reporter.warn(f"{q_path}.option", f"{q_type} question has fewer than 2 options; this is usually not a meaningful selection question.", "high", "too-few-selection-options", "Add more meaningful options or convert the question to input.", "Selection questions should usually offer at least two choices.")

        if q_type == "radio":
            other_count = 0
            for j, option in enumerate(options):
                opt_title = option.get("title", "") if is_plain_object(option) else ""
                attr = option.get("attribute") if is_plain_object(option) else {}
                if looks_like_other_label(opt_title):
                    other_count += 1
                if is_plain_object(attr) and attr.get("random") is False and question_attr.get("random") is not True:
                    reporter.warn(f"{q_path}.option[{j}].attribute.random", "Option-level random=false is redundant because the parent radio question is not randomized.", "low", "redundant-option-random-override", "Remove the redundant option-level random=false override.", "Keep option.attribute.random=false only when the parent question has attribute.random=true.")
                if option.get("child") and not looks_like_other_label(opt_title):
                    reporter.warn(f"{q_path}.option[{j}].child", "Radio option has child inputs but its label does not look like an explanation-triggering option such as 'Other'; verify this is intentional.", "medium", "radio-child-on-normal-option", "Verify whether this child input belongs on a conditional explanation option.", "Prefer child inputs on options like 'Other, please specify' rather than ordinary options.")
            if other_count > 1:
                reporter.warn(f"{q_path}.option", "Multiple 'other' style radio options detected; usually only one is needed.", "medium", "multiple-other-options", "Collapse duplicate 'Other' style options into one.", "Keep a single explanation-style fallback option and attach child inputs there if needed.")
            if question_attr.get("required") is False and len(options) == 2:
                reporter.warn(f"{q_path}.attribute.required", "Optional radio with very few options may create ambiguous skipped answers; consider whether it should be required or include an explicit 'skip' option.", "low", "optional-radio-ambiguous-skip", "Consider making the question required or adding an explicit skip / not sure option.", "Optional two-option radios can make blank answers hard to interpret analytically.")

        if q_type == "checkbox":
            exclusive_indices = []
            mutual_indices = []
            for j, option in enumerate(options):
                attr = option.get("attribute") if is_plain_object(option) else None
                if is_plain_object(attr):
                    if attr.get("exclusive") is True:
                        exclusive_indices.append(j)
                    if attr.get("mutual-exclusion") is True:
                        mutual_indices.append(j)
                    if attr.get("random") is False and question_attr.get("random") is not True:
                        reporter.warn(f"{q_path}.option[{j}].attribute.random", "Option-level random=false is redundant because the parent checkbox question is not randomized.", "low", "redundant-option-random-override", "Remove the redundant option-level random=false override.", "Keep option.attribute.random=false only when the parent question has attribute.random=true.")
            if len(exclusive_indices) > 1:
                reporter.warn(f"{q_path}.option", "Multiple exclusive options detected; usually a checkbox question should have at most one exclusive option.", "high", "multiple-exclusive-options", "Reduce exclusive options to one catch-all answer.", "Use exclusive only for a single option like 'None of the above' or 'Not applicable'.")
            if options and len(mutual_indices) == len(options):
                reporter.warn(f"{q_path}.option", "All checkbox options are marked mutual-exclusion; this usually indicates the question should be radio instead.", "high", "all-options-mutual-exclusion", "Convert this checkbox to radio or narrow mutual-exclusion to a smaller subset.", "Mutual exclusion is intended for a subgroup, not every option.")
            if exclusive_indices:
                for j in exclusive_indices:
                    option = options[j]
                    if is_plain_object(option) and option.get("child"):
                        reporter.warn(f"{q_path}.option[{j}].child", "Exclusive option contains child inputs; this is usually confusing in real questionnaires.", "high", "exclusive-option-with-child", "Remove the child input or move it to a non-exclusive explanation option.", "Exclusive options should usually act as terminal catch-all answers.")
                    if is_plain_object(option) and not looks_like_other_label(option.get("title")):
                        reporter.warn(f"{q_path}.option[{j}].title", "Exclusive option label does not look like 'none/applicable/other' style copy; verify the exclusive semantics are correct.", "medium", "exclusive-label-mismatch", "Check whether this option should really be exclusive.", "Exclusive options usually read like 'None', 'Not applicable', or a catch-all alternative.")
            if len(mutual_indices) == 1:
                reporter.warn(f"{q_path}.option", "Only one mutual-exclusion option is defined; mutual exclusion only has effect when two or more options participate.", "low", "single-mutual-exclusion-option", "Either remove mutual-exclusion or add the second participating option.", "Mutual exclusion is only meaningful when multiple options share it.")

        if q_type == "input":
            if question_attr.get("required") is True and not options:
                reporter.warn(f"{q_path}", "Required input question has no option definitions.", "high", "required-input-without-options", "Define at least one input option field for the required question.", "Input questions must describe their field(s) in option[].")
            for j, option in enumerate(options):
                attr = option.get("attribute") if is_plain_object(option) else None
                if is_plain_object(attr):
                    dt = attr.get("dataType")
                    placeholder = attr.get("placeholder")
                    if dt in {"dateRange", "timeRange", "dateTimeRange"} and is_integer_like(attr.get("minLength")):
                        reporter.warn(f"{q_path}.option[{j}].attribute.minLength", "Range input uses minLength; range fields are usually better constrained semantically than by string length.", "medium", "range-uses-minlength", "Remove minLength from range fields and validate start/end semantics instead.", "Use semantic checks on start/end presence rather than string length for range types.")
                    if is_range_type(dt) and is_integer_like(attr.get("maxLength")):
                        reporter.warn(f"{q_path}.option[{j}].attribute.maxLength", "Range input uses maxLength; range fields are usually better constrained semantically than by string length.", "medium", "range-uses-maxlength", "Remove maxLength from range fields and validate start/end semantics instead.", "Use semantic checks on start/end presence rather than string length for range types.")
                    if dt == "email" and isinstance(placeholder, str) and not looks_like_email_placeholder(placeholder):
                        reporter.warn(f"{q_path}.option[{j}].attribute.placeholder", "Email field placeholder does not look like an email example or mailbox hint.", "low", "email-placeholder-mismatch", "Use an email-like placeholder such as name@example.com.", "Match placeholder copy to the expected datatype to reduce respondent confusion.")
                    if dt == "tel" and isinstance(placeholder, str) and not looks_like_tel_placeholder(placeholder):
                        reporter.warn(f"{q_path}.option[{j}].attribute.placeholder", "Telephone field placeholder does not look like a phone hint.", "low", "tel-placeholder-mismatch", "Use a phone-like placeholder such as 13800000000 or +86.", "Make placeholder match the telephone datatype.")
                    if dt in {"date", "time", "dateTime"} and isinstance(placeholder, str) and placeholder.strip() and not looks_like_date_placeholder(placeholder):
                        reporter.warn(f"{q_path}.option[{j}].attribute.placeholder", "Date/time field placeholder may be misleading for a structured temporal input.", "low", "temporal-placeholder-mismatch", "Use a date/time hint or leave the placeholder empty if the browser control already conveys format.", "Avoid generic text placeholders for structured date/time fields.")
                    if dt == "number" and looks_like_long_form_prompt(option.get("title")):
                        reporter.warn(f"{q_path}.option[{j}].title", "Number field title looks like a long-form prompt; verify the datatype is not too restrictive.", "medium", "number-datatype-mismatch", "Check whether this field should be text instead of number.", "Long-form prompts usually need text inputs, not numeric-only constraints.")
                    if dt == "text" and looks_like_long_form_prompt(option.get("title")) and not is_integer_like(attr.get("maxLength")):
                        reporter.warn(f"{q_path}.option[{j}].attribute.maxLength", "Long-form text prompt has no maxLength guidance; consider whether an upper bound is needed for downstream data quality.", "low", "long-text-without-maxlength", "Consider whether downstream systems need an upper length limit.", "Add maxLength if storage, moderation, or analytics pipelines expect bounded text.")

        if q_type in {"radio", "checkbox"}:
            for j, option in enumerate(options):
                if not is_plain_object(option):
                    continue
                if option.get("child"):
                    children = option.get("child") if isinstance(option.get("child"), list) else []
                    for k, child in enumerate(children):
                        child_attr = child.get("attribute") if is_plain_object(child) else None
                        if is_plain_object(child_attr):
                            dt = child_attr.get("dataType")
                            if dt == "number" and looks_like_other_label(option.get("title")):
                                reporter.warn(f"{q_path}.option[{j}].child[{k}].attribute.dataType", "An 'other/specify' child usually expects free text rather than number; verify the child datatype.", "medium", "other-child-number-datatype", "Change the child datatype to text unless the business rule truly requires numeric input.", "Explanation-style child fields are usually textual.")
                            if is_range_type(dt):
                                reporter.warn(f"{q_path}.option[{j}].child[{k}].attribute.dataType", "Selection-option child inputs usually work best as simple follow-up fields; range child inputs may be hard to complete inline.", "medium", "child-range-datatype", "Use a simpler child datatype or promote the follow-up into its own question.", "Inline child fields should stay lightweight.")
                            if child_attr.get("required") is True and question_attr.get("required") is not True:
                                reporter.warn(f"{q_path}.option[{j}].child[{k}].attribute.required", "Child input is required while the parent question is optional; verify this does not create a confusing validation path.", "medium", "required-child-under-optional-parent", "Make the parent required or relax the child requirement if that fits the business intent.", "Required child inputs under optional parents can confuse respondents and complicate validation.")
        if q_type == "score":
            if len(options) < 1:
                reporter.warn(f"{q_path}.option", "Score question has no score rows.", "high", "score-without-options", "Add at least one score row.", "Each score question should contain at least one option row.")
            scopes = []
            for j, option in enumerate(options):
                if not is_plain_object(option):
                    continue
                opt_attr = option.get("attribute") if is_plain_object(option.get("attribute")) else {}
                scope = opt_attr.get("scope")
                step = opt_attr.get("step")
                if isinstance(scope, list) and len(scope) == 2:
                    scopes.append(tuple(scope))
                if step == 0.5 and isinstance(scope, list) and len(scope) == 2 and float(scope[1]) - float(scope[0]) > 10:
                    reporter.warn(f"{q_path}.option[{j}].attribute.step", "Half-step score with a wide scope may create too many rating choices.", "medium", "score-half-step-wide-range", "Consider using step=1 or narrowing the score scope.", "Too many rating points can reduce answer quality on mobile.")
            if len(set(scopes)) > 1:
                reporter.warn(f"{q_path}.option", "Score question mixes different scopes across options; verify this is intentional.", "medium", "score-mixed-scope", "Prefer a consistent scope across one score question.", "Mixed score ranges are harder for respondents to compare.")

        if q_type == "nps":
            if len(options) != 1:
                reporter.warn(f"{q_path}.option", "NPS questions should usually contain exactly one option scale configuration.", "medium", "nps-option-count", "Keep one option item for the NPS scale unless the business rule requires otherwise.", "Use score questions for multi-dimensional rating.")
            for j, option in enumerate(options):
                if not is_plain_object(option):
                    continue
                opt_attr = option.get("attribute") if is_plain_object(option.get("attribute")) else {}
                scope = opt_attr.get("scope")
                if isinstance(scope, list) and len(scope) == 2 and tuple(scope) != (0, 10):
                    reporter.warn(f"{q_path}.option[{j}].attribute.scope", "NPS normally uses the standard 0-10 scale; verify this custom scope is intentional.", "medium", "nps-nonstandard-scope", "Prefer scope [0, 10] for standard NPS.", "Changing the NPS range may break benchmark comparability.")


def validate_survey_schema(schema):
    reporter = Reporter()
    id_map = {}
    if not is_plain_object(schema):
        reporter.error("schema", "Top-level schema must be an object with survey/questions/finish.")
        return reporter.result(None)
    assert_allowed_keys(schema, ["survey", "questions", "finish", "logic"], "schema", reporter)
    validate_survey_node(schema.get("survey"), reporter, id_map)
    questions = schema.get("questions")
    one_page_one_question = False
    if is_plain_object(schema.get("survey")) and is_plain_object(schema.get("survey", {}).get("attribute")):
        one_page_one_question = schema["survey"]["attribute"].get("onePageOneQuestion") is True
    if not isinstance(questions, list):
        reporter.error("questions", "questions must be an array.")
    else:
        for i, question in enumerate(questions):
            q_path = f"questions[{i}]"
            if not is_plain_object(question):
                reporter.error(q_path, "Question must be an object.")
                continue
            if question.get("type") == PAGINATION_TYPE:
                if one_page_one_question:
                    reporter.error(f"{q_path}.type", "Pagination is mutually exclusive with survey.attribute.onePageOneQuestion=true. Remove Pagination or set onePageOneQuestion=false.")
                validate_pagination_node(question, q_path, reporter, id_map)
                continue
            if question.get("type") not in ALLOWED_QUESTION_TYPES:
                reporter.error(f"{q_path}.type", f'Unsupported question type "{question.get("type")}".')
                continue
            if question.get("type") in {"radio", "checkbox"}:
                validate_selection_question(question, q_path, reporter, id_map)
            elif question.get("type") == "input":
                validate_input_question(question, q_path, reporter, id_map)
            elif question.get("type") == "score":
                validate_score_question(question, q_path, reporter, id_map)
            elif question.get("type") == "nps":
                validate_nps_question(question, q_path, reporter, id_map)
    normalized_finish = validate_finish_nodes(schema.get("finish"), reporter, id_map)
    validate_logic_rules(schema, reporter)
    semantic_lint(schema, reporter)
    return reporter.result({
        "survey": schema.get("survey"),
        "questions": questions if isinstance(questions, list) else [],
        "finish": normalized_finish,
        "logic": schema.get("logic") if isinstance(schema.get("logic"), list) else [],
    })


def read_input(file_arg=None):
    if file_arg:
        return Path(file_arg).read_text(encoding="utf-8")
    return sys.stdin.read()


def print_human(report):
    print("✅ Survey schema is valid." if report["valid"] else "❌ Survey schema is invalid.")
    if report["errors"]:
        print("\nErrors:")
        for i, item in enumerate(report["errors"], start=1):
            print(f"{i}. [{item['path']}] {item['message']}")
    if report["warnings"]:
        print("\nWarnings:")
        for i, item in enumerate(report["warnings"], start=1):
            severity = item.get("severity", "medium").upper()
            code = item.get("code")
            code_text = f" [{code}]" if code else ""
            print(f"{i}. [{severity}]{code_text} [{item['path']}] {item['message']}")
            if item.get("suggestion"):
                print(f"   suggestion: {item['suggestion']}")
            if item.get("fixHint"):
                print(f"   fixHint: {item['fixHint']}")


def main():
    args = sys.argv[1:]
    json_output = "--json" in args
    file_arg = next((a for a in args if not a.startswith("--")), None)
    try:
        schema = json.loads(read_input(file_arg))
    except FileNotFoundError as e:
        print(f"Failed to read schema input: {e}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)
    report = validate_survey_schema(schema)
    if json_output:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_human(report)
    sys.exit(0 if report["valid"] else 1)


if __name__ == "__main__":
    main()
