#!/usr/bin/env python3
import argparse
import json
import sys
from copy import deepcopy
from pathlib import Path

from schema_id_utils import normalize_schema_ids
from validate_survey_schema import validate_survey_schema, normalize_rich_text


EMAIL_PLACEHOLDER = "name@example.com"
TEL_PLACEHOLDER = "13800000000"
DATE_PLACEHOLDER = "YYYY-MM-DD"
TIME_PLACEHOLDER = "HH:MM"
DATETIME_PLACEHOLDER = "YYYY-MM-DD HH:MM"


def load_json(path_str):
    return json.loads(Path(path_str).read_text(encoding="utf-8"))


def parse_path(path):
    tokens = []
    i = 0
    while i < len(path):
        if path[i] == "[":
            j = path.index("]", i)
            tokens.append(int(path[i + 1 : j]))
            i = j + 1
        elif path[i] == ".":
            i += 1
        else:
            j = i
            while j < len(path) and path[j] not in ".[":
                j += 1
            tokens.append(path[i:j])
            i = j
    return tokens


def get_parent_and_key(root, path):
    tokens = parse_path(path)
    if not tokens:
        return None, None
    cursor = root
    for token in tokens[:-1]:
        cursor = cursor[token]
    return cursor, tokens[-1]


def get_value(root, path, default=None):
    try:
        tokens = parse_path(path)
        cursor = root
        for token in tokens:
            cursor = cursor[token]
        return cursor
    except Exception:
        return default


def set_value(root, path, value):
    parent, key = get_parent_and_key(root, path)
    if parent is None:
        return False
    parent[key] = value
    return True


def delete_key(root, path):
    parent, key = get_parent_and_key(root, path)
    if parent is None:
        return False
    if isinstance(parent, dict) and key in parent:
        del parent[key]
        return True
    return False


def ensure_text_html(value):
    text = normalize_rich_text(value)
    if text:
        return f"<p>{text}</p>"
    return "<p></p>"


def fallback_title_for_path(path):
    if path == "survey.title":
        return "<p>问卷调查</p>"
    if path == "finish.title" or path.startswith("finish["):
        return "<p>提交完成</p>"
    if path.startswith("questions["):
        return "<p>请完成本题</p>"
    return "<p>请补充标题</p>"


def get_question_from_warning_path(schema, warning_path):
    tokens = parse_path(warning_path)
    if len(tokens) >= 2 and tokens[0] == "questions" and isinstance(tokens[1], int):
        return schema["questions"][tokens[1]]
    return None


def repair_warning(schema, warning, applied):
    code = warning.get("code")
    path = warning.get("path")

    if code == "noncanonical-id-format":
        normalized, id_map = normalize_schema_ids(schema)
        if normalized != schema:
            schema.clear()
            schema.update(normalized)
            applied.append({
                "code": code,
                "path": path,
                "action": "normalized-schema-ids",
                "changedIdCount": len(id_map),
            })
            return True

    if code == "empty-rich-text-title" or code == "empty-finish-title" or code == "empty-question-title":
        if set_value(schema, path, fallback_title_for_path(path)):
            applied.append({"code": code, "path": path, "action": "filled-fallback-title"})
            return True

    if code == "complex-rich-text-title":
        value = get_value(schema, path)
        text = normalize_rich_text(value) or "问卷标题"
        if set_value(schema, path, f"<p>{text}</p>"):
            applied.append({"code": code, "path": path, "action": "simplified-rich-text"})
            return True

    if code == "allowback-without-step-mode":
        if set_value(schema, "survey.attribute.allowBack", False):
            applied.append({"code": code, "path": "survey.attribute.allowBack", "action": "disabled-allowBack"})
            return True

    if code == "finish-looks-like-question-copy":
        target_path = path if path and path.startswith("finish[") else "finish.description"
        if set_value(schema, target_path, "<p>感谢你的填写，提交后我们会尽快处理你的反馈。</p>"):
            applied.append({"code": code, "path": target_path, "action": "rewrote-finish-description"})
            return True

    if code == "redundant-option-random-override":
        if delete_key(schema, path):
            applied.append({"code": code, "path": path, "action": "removed-redundant-random-override"})
            return True

    if code == "multiple-exclusive-options":
        question = get_question_from_warning_path(schema, path)
        if question and isinstance(question.get("option"), list):
            seen = False
            changed = False
            for option in question["option"]:
                attr = option.get("attribute")
                if isinstance(attr, dict) and attr.get("exclusive") is True:
                    if not seen:
                        seen = True
                    else:
                        del attr["exclusive"]
                        changed = True
            if changed:
                applied.append({"code": code, "path": path, "action": "kept-first-exclusive-only"})
                return True

    if code == "exclusive-option-with-child":
        if delete_key(schema, path):
            applied.append({"code": code, "path": path, "action": "removed-exclusive-child"})
            return True

    if code == "exclusive-label-mismatch":
        # Do not auto-disable exclusive semantics from a medium wording warning.
        # Whether a catch-all checkbox option should be exclusive is a product decision;
        # leave it for manual review instead of silently changing collection logic.
        return False

    if code == "single-mutual-exclusion-option":
        question = get_question_from_warning_path(schema, path)
        if question and isinstance(question.get("option"), list):
            changed = False
            for option in question["option"]:
                attr = option.get("attribute")
                if isinstance(attr, dict) and attr.get("mutual-exclusion") is True:
                    del attr["mutual-exclusion"]
                    changed = True
            if changed:
                applied.append({"code": code, "path": path, "action": "removed-lone-mutual-exclusion"})
                return True

    if code in {"range-uses-minlength", "range-uses-maxlength"}:
        if delete_key(schema, path):
            applied.append({"code": code, "path": path, "action": "removed-range-length-constraint"})
            return True

    if code == "email-placeholder-mismatch":
        if set_value(schema, path, EMAIL_PLACEHOLDER):
            applied.append({"code": code, "path": path, "action": "normalized-email-placeholder"})
            return True

    if code == "tel-placeholder-mismatch":
        if set_value(schema, path, TEL_PLACEHOLDER):
            applied.append({"code": code, "path": path, "action": "normalized-tel-placeholder"})
            return True

    if code == "temporal-placeholder-mismatch":
        dt = get_value(schema, path.rsplit(".", 1)[0] + ".dataType")
        replacement = DATE_PLACEHOLDER
        if dt == "time":
            replacement = TIME_PLACEHOLDER
        elif dt == "dateTime":
            replacement = DATETIME_PLACEHOLDER
        if set_value(schema, path, replacement):
            applied.append({"code": code, "path": path, "action": "normalized-temporal-placeholder"})
            return True

    if code == "number-datatype-mismatch":
        attr_path = path.rsplit(".", 1)[0].replace(".title", ".attribute.dataType")
        if set_value(schema, attr_path, "text"):
            applied.append({"code": code, "path": attr_path, "action": "converted-number-to-text"})
            return True

    if code == "long-text-without-maxlength":
        target = path
        if set_value(schema, target, 500):
            applied.append({"code": code, "path": target, "action": "added-maxLength-500"})
            return True

    if code == "other-child-number-datatype":
        if set_value(schema, path, "text"):
            applied.append({"code": code, "path": path, "action": "converted-child-number-to-text"})
            return True

    if code == "child-range-datatype":
        if set_value(schema, path, "text"):
            applied.append({"code": code, "path": path, "action": "converted-child-range-to-text"})
            return True

    if code == "required-child-under-optional-parent":
        if set_value(schema, path, False):
            applied.append({"code": code, "path": path, "action": "relaxed-child-required"})
            return True

    return False


def auto_repair_schema(schema, max_rounds=3):
    working = deepcopy(schema)
    all_applied = []
    history = []

    for round_index in range(1, max_rounds + 1):
        report = validate_survey_schema(working)
        history.append({
            "round": round_index,
            "valid": report.get("valid", False),
            "errorCount": len(report.get("errors", [])),
            "warningCount": len(report.get("warnings", [])),
        })
        if not report.get("valid", False):
            return {
                "changed": bool(all_applied),
                "schema": working,
                "initialReport": validate_survey_schema(schema),
                "finalReport": report,
                "appliedFixes": all_applied,
                "history": history,
                "stoppedReason": "schema-errors-block-auto-repair",
            }
        applied_this_round = []
        for warning in report.get("warnings", []):
            repair_warning(working, warning, applied_this_round)
        if not applied_this_round:
            return {
                "changed": bool(all_applied),
                "schema": working,
                "initialReport": validate_survey_schema(schema),
                "finalReport": report,
                "appliedFixes": all_applied,
                "history": history,
                "stoppedReason": "no-more-safe-fixes",
            }
        all_applied.extend(applied_this_round)

    final_report = validate_survey_schema(working)
    return {
        "changed": bool(all_applied),
        "schema": working,
        "initialReport": validate_survey_schema(schema),
        "finalReport": final_report,
        "appliedFixes": all_applied,
        "history": history,
        "stoppedReason": "max-rounds-reached",
    }


def print_human(report, out_path=None):
    print("✅ AUTO REPAIR COMPLETE" if report["finalReport"].get("valid") else "❌ AUTO REPAIR INCOMPLETE")
    print(f"Stopped reason: {report['stoppedReason']}")
    if report["appliedFixes"]:
        print("\nApplied fixes:")
        for idx, item in enumerate(report["appliedFixes"], start=1):
            print(f"  {idx}. [{item['code']}] [{item['path']}] {item['action']}")
    else:
        print("\nApplied fixes: none")
    final_report = report["finalReport"]
    if final_report.get("warnings"):
        print("\nRemaining warnings:")
        for idx, item in enumerate(final_report["warnings"], start=1):
            severity = item.get("severity", "medium").upper()
            code = item.get("code", "no-code")
            print(f"  {idx}. [{severity}] [{code}] [{item['path']}] {item['message']}")
    if out_path:
        print(f"\nOutput schema: {out_path}")


def main():
    parser = argparse.ArgumentParser(description="Auto-repair safe semantic warnings in a survey schema.")
    parser.add_argument("schema", help="Path to source schema JSON")
    parser.add_argument("--out", help="Output repaired schema path")
    parser.add_argument("--max-rounds", type=int, default=3, help="Maximum repair passes")
    parser.add_argument("--json", action="store_true", help="Print machine-readable report")
    args = parser.parse_args()

    try:
        schema = load_json(args.schema)
    except FileNotFoundError as e:
        print(f"Failed to read schema input: {e}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)

    report = auto_repair_schema(schema, max_rounds=args.max_rounds)
    out_path = args.out
    if out_path:
        Path(out_path).write_text(json.dumps(report["schema"], ensure_ascii=False, indent=2), encoding="utf-8")

    payload = {k: v for k, v in report.items() if k != "schema"}
    payload["outputPath"] = out_path
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print_human(report, out_path=out_path)

    final_valid = report["finalReport"].get("valid", False)
    sys.exit(0 if final_valid else 1)


if __name__ == "__main__":
    main()
