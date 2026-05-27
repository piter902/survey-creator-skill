#!/usr/bin/env python3
import argparse
import json
import re
from collections import Counter, defaultdict
from html.parser import HTMLParser
from pathlib import Path

import xlsxwriter


class HtmlTextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        if data:
            self.parts.append(data)

    def text(self):
        return " ".join("".join(self.parts).split())


def html_to_text(value):
    if not isinstance(value, str):
        return ""
    parser = HtmlTextExtractor()
    parser.feed(value)
    return parser.text()


POSITIVE_TERMS = {
    "满意", "很好", "不错", "专业", "高效", "及时", "顺畅", "清楚", "优秀", "推荐", "认可", "方便", "靠谱", "快速", "友好"
}
NEGATIVE_TERMS = {
    "不满意", "差", "很差", "慢", "延迟", "拖延", "无人", "不清楚", "不专业", "不好", "糟糕", "麻烦", "投诉", "失望", "低于预期", "未解决", "卡顿"
}
INFO_FIELD_HINTS = {
    "姓名", "手机号", "手机", "电话", "联系方式", "微信", "邮箱", "email", "公司", "企业", "联系人", "地址", "部门", "职位", "qq"
}
SENTIMENT_LABELS = {
    "strong_positive": "高度满意",
    "positive": "满意",
    "neutral": "中性",
    "negative": "不满",
    "strong_negative": "强烈不满",
}


def safe_sheet_name(name, fallback):
    cleaned = re.sub(r"[:\\\\/?*\\[\\]]", " ", name or "").strip()
    cleaned = cleaned[:31].strip()
    return cleaned or fallback


def normalize_text(value):
    return html_to_text(value).strip().lower()


def load_json_or_jsonl(path):
    raw = Path(path).read_text(encoding="utf-8").strip()
    if not raw:
        return []
    if raw.startswith("[") or raw.startswith("{"):
        data = json.loads(raw)
        return data if isinstance(data, list) else [data]
    rows = []
    for line in raw.splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def load_schema(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_optional_json(path):
    if not path:
        return None
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_analysis_config(path):
    config = load_optional_json(path)
    return config if isinstance(config, dict) else {}


def normalize_record(record):
    if isinstance(record, dict) and isinstance(record.get("payload"), dict):
        payload = record["payload"]
        meta = {k: v for k, v in record.items() if k != "payload"}
        return payload, meta
    return record, {}


def build_schema_maps(schema):
    question_map = {}
    option_map = {}
    child_map = {}
    finish_map = {}

    for finish in schema.get("finish") or []:
        if isinstance(finish, dict) and finish.get("id"):
            finish_map[finish["id"]] = finish

    for question in schema.get("questions") or []:
        qid = question.get("id")
        if not qid:
            continue
        question_map[qid] = question
        qopts = {}
        qchildren = {}
        for opt in question.get("option") or []:
            oid = opt.get("id")
            if not oid:
                continue
            qopts[oid] = opt
            for child in opt.get("child") or []:
                cid = child.get("id")
                if cid:
                    qchildren[cid] = child
        option_map[qid] = qopts
        child_map[qid] = qchildren

    return question_map, option_map, child_map, finish_map


def extract_choice_option_ids(answer):
    if not isinstance(answer, dict):
        return []
    value = answer.get("value")
    qtype = answer.get("questionType")
    if qtype in {"radio", "nps"} and isinstance(value, dict):
        oid = value.get("optionId")
        return [oid] if oid else []
    if qtype == "checkbox" and isinstance(value, list):
        return [item.get("optionId") for item in value if isinstance(item, dict) and item.get("optionId")]
    return []


def evaluate_condition(answer_map, rule):
    when = rule.get("when") or {}
    qid = when.get("questionId")
    operator = when.get("operator")
    answer = answer_map.get(qid)
    if not answer:
        return operator in {"not_answered", "not_selected", "not_exists"}

    option_id = when.get("optionId")
    option_ids = when.get("optionIds") or []
    compare_value = when.get("value")
    selected_ids = set(extract_choice_option_ids(answer))

    if operator == "answered":
        return True
    if operator == "not_answered":
        return False
    if operator == "selected":
        return option_id in selected_ids
    if operator == "not_selected":
        return option_id not in selected_ids
    if operator == "exists":
        return bool(selected_ids.intersection(option_ids))
    if operator == "not_exists":
        return not bool(selected_ids.intersection(option_ids))

    scalar_values = []
    value = answer.get("value")
    if isinstance(value, dict):
        if "score" in value:
            scalar_values.append(value["score"])
        elif "value" in value:
            scalar_values.append(value["value"])
    elif isinstance(value, list):
        for item in value:
            if not isinstance(item, dict):
                continue
            if "score" in item:
                scalar_values.append(item["score"])
            elif "value" in item:
                item_value = item["value"]
                if isinstance(item_value, dict):
                    scalar_values.append("%s ~ %s" % (item_value.get("start", ""), item_value.get("end", "")))
                else:
                    scalar_values.append(item_value)
    elif value is not None:
        scalar_values.append(value)

    if operator == "contains":
        if option_id:
            return option_id in selected_ids
        return any(compare_value in str(v) for v in scalar_values if v is not None)
    if operator == "not_contains":
        if option_id:
            return option_id not in selected_ids
        return all(compare_value not in str(v) for v in scalar_values if v is not None)
    if operator == "eq":
        return any(v == compare_value for v in scalar_values)
    if operator == "neq":
        return bool(scalar_values) and all(v != compare_value for v in scalar_values)
    if operator == "gt":
        return any(_to_float(v) is not None and _to_float(v) > _to_float(compare_value) for v in scalar_values)
    if operator == "lt":
        return any(_to_float(v) is not None and _to_float(v) < _to_float(compare_value) for v in scalar_values)
    return False


def _to_float(value):
    try:
        return float(value)
    except Exception:
        return None


def infer_logic_segments(schema, answer_map):
    result = {"finishId": None, "matchedRules": [], "shownQuestions": set()}
    for rule in schema.get("logic") or []:
        if not isinstance(rule, dict):
            continue
        if evaluate_condition(answer_map, rule):
            result["matchedRules"].append(rule.get("id"))
            action = rule.get("action") or {}
            action_type = action.get("type")
            if action_type == "show_question" and action.get("targetQuestionId"):
                result["shownQuestions"].add(action["targetQuestionId"])
            if action_type == "end_survey":
                result["finishId"] = action.get("targetQuestionId") or result["finishId"]
    return result


def flatten_answer_value(question, answer, option_lookup, child_lookup):
    if not answer:
        return "", []
    qtype = question.get("type")
    value = answer.get("value")
    details = []

    if qtype == "radio" and isinstance(value, dict):
        option = option_lookup.get(value.get("optionId")) or {}
        label = html_to_text(option.get("title")) or value.get("optionId", "")
        parts = [label]
        for child in value.get("child") or []:
            if not isinstance(child, dict):
                continue
            child_schema = child_lookup.get(child.get("childId")) or {}
            child_title = html_to_text(child_schema.get("title")) or child.get("childId", "")
            child_value = format_child_value(child.get("value"))
            parts.append(f"{child_title}: {child_value}")
            details.append({"kind": "child", "label": child_title, "value": child_value})
        return " | ".join(parts), details

    if qtype == "checkbox" and isinstance(value, list):
        labels = []
        for item in value:
            if not isinstance(item, dict):
                continue
            option = option_lookup.get(item.get("optionId")) or {}
            label = html_to_text(option.get("title")) or item.get("optionId", "")
            parts = [label]
            labels.append(label)
            details.append({"kind": "option", "label": label, "value": 1})
            for child in item.get("child") or []:
                if not isinstance(child, dict):
                    continue
                child_schema = child_lookup.get(child.get("childId")) or {}
                child_title = html_to_text(child_schema.get("title")) or child.get("childId", "")
                child_value = format_child_value(child.get("value"))
                parts.append(f"{child_title}: {child_value}")
                details.append({"kind": "child", "label": child_title, "value": child_value, "parent": label})
            labels[-1] = " | ".join(parts)
        return "; ".join(labels), details

    if qtype == "input" and isinstance(value, list):
        labels = []
        for item in value:
            if not isinstance(item, dict):
                continue
            option = option_lookup.get(item.get("optionId")) or {}
            label = html_to_text(option.get("title")) or item.get("optionId", "")
            item_value = format_child_value(item.get("value"))
            labels.append(f"{label}: {item_value}")
            details.append({"kind": "input", "label": label, "value": item_value, "dataType": item.get("dataType")})
        return "; ".join(labels), details

    if qtype == "score" and isinstance(value, list):
        labels = []
        for item in value:
            if not isinstance(item, dict):
                continue
            option = option_lookup.get(item.get("optionId")) or {}
            label = html_to_text(option.get("title")) or item.get("optionId", "")
            score = item.get("score")
            labels.append(f"{label}: {score}")
            details.append({"kind": "score", "label": label, "value": score})
        return "; ".join(labels), details

    if qtype == "nps" and isinstance(value, dict):
        option = option_lookup.get(value.get("optionId")) or {}
        label = html_to_text(option.get("title")) or value.get("optionId", "")
        score = value.get("score")
        details.append({"kind": "nps", "label": label, "value": score})
        return f"{label}: {score}", details

    return str(value), details


def format_child_value(value):
    if isinstance(value, dict):
        return "%s ~ %s" % (value.get("start", ""), value.get("end", ""))
    return "" if value is None else str(value)


def is_info_collection_field(label, data_type=None):
    if data_type and data_type in {"tel", "email", "date", "time", "dateTime", "dateRange", "timeRange", "dateTimeRange", "number"}:
        return True
    normalized = normalize_text(label)
    return any(hint.lower() in normalized for hint in INFO_FIELD_HINTS)


def should_analyze_text(question_id, label, data_type, analysis_config):
    if not isinstance(analysis_config, dict):
        analysis_config = {}
    text_config = analysis_config.get("textAnalysis") or {}
    include_questions = set(text_config.get("includeQuestionIds") or [])
    exclude_questions = set(text_config.get("excludeQuestionIds") or [])
    include_labels = [normalize_text(item) for item in (text_config.get("includeLabels") or []) if isinstance(item, str)]
    exclude_labels = [normalize_text(item) for item in (text_config.get("excludeLabels") or []) if isinstance(item, str)]

    normalized_label = normalize_text(label)

    if question_id in exclude_questions:
        return False
    if any(item and item in normalized_label for item in exclude_labels):
        return False
    if include_questions and question_id in include_questions:
        return True
    if include_labels and any(item and item in normalized_label for item in include_labels):
        return True
    return not is_info_collection_field(label, data_type)


def nps_band(score):
    if score is None:
        return "unknown"
    if score <= 6:
        return "detractor"
    if score <= 8:
        return "passive"
    return "promoter"


def extract_text_themes(values, top_n=8):
    stopwords = {
        "我们", "你们", "你", "我", "的", "了", "和", "是", "也", "就", "都", "还", "很", "更", "需要",
        "希望", "可以", "这个", "那个", "一下", "一个", "不是", "因为", "所以", "已经", "如果", "没有",
        "进行", "继续", "方便", "比较", "以及", "还有", "对于", "本次", "服务", "问题", "说明"
    }
    counter = Counter()
    for item in values:
        value = item.get("value", "")
        text = re.sub(r"[^\w\u4e00-\u9fff]+", " ", str(value))
        tokens = [token.strip().lower() for token in text.split() if len(token.strip()) >= 2]
        for token in tokens:
            if token not in stopwords:
                counter[token] += 1
    return [{"term": term, "count": count} for term, count in counter.most_common(top_n)]


def analyze_sentiment(values):
    counts = Counter({key: 0 for key in SENTIMENT_LABELS})
    samples = []
    for item in values:
        text = str(item.get("value", "")).strip()
        if not text:
            continue
        score = 0
        for term in POSITIVE_TERMS:
            if term in text:
                score += 1
        for term in NEGATIVE_TERMS:
            if term in text:
                score -= 1
        if score >= 2:
            label = "strong_positive"
        elif score == 1:
            label = "positive"
        elif score <= -2:
            label = "strong_negative"
        elif score == -1:
            label = "negative"
        else:
            label = "neutral"
        counts[label] += 1
        samples.append({"value": text, "sentiment": label, "sentimentLabel": SENTIMENT_LABELS[label]})
    total = sum(counts.values())
    dominant = None
    if total:
        dominant = counts.most_common(1)[0][0]
    return {
        "counts": dict(counts),
        "total": total,
        "dominant": dominant,
        "dominantLabel": SENTIMENT_LABELS.get(dominant, "") if dominant else None,
        "samples": samples[:20],
    }


def aggregate_finish_sentiment(valid_records, finish_map):
    grouped = defaultdict(list)
    for record in valid_records:
        finish_id = record["row"].get("finishId") or ""
        payload = record["payload"]
        answer_map = {a.get("questionId"): a for a in payload.get("answers", []) if isinstance(a, dict)}
        for answer in answer_map.values():
            value = answer.get("value")
            if isinstance(value, dict):
                child_values = value.get("child") or []
                for item in child_values:
                    if isinstance(item, dict):
                        grouped[finish_id].append({"value": item.get("value", "")})
            elif isinstance(value, list):
                for item in value:
                    if not isinstance(item, dict):
                        continue
                    if "child" in item:
                        for child in item.get("child") or []:
                            if isinstance(child, dict):
                                grouped[finish_id].append({"value": child.get("value", "")})
                    elif "dataType" in item and item.get("dataType") == "text":
                        grouped[finish_id].append({"value": item.get("value", "")})

    rows = []
    for finish_id, values in grouped.items():
        clean_values = [item for item in values if str(item.get("value", "")).strip()]
        if not clean_values:
            continue
        sentiment = analyze_sentiment(clean_values)
        finish_title = html_to_text((finish_map.get(finish_id) or {}).get("title")) or finish_id or "未命名结束页"
        rows.append({
            "finishId": finish_id,
            "finishTitle": finish_title,
            "totalTextResponses": sentiment["total"],
            "dominant": sentiment["dominant"],
            "dominantLabel": sentiment["dominantLabel"],
            "counts": sentiment["counts"],
        })
    return rows


def aggregate_extra_finish_analysis(valid_records, finish_map, keys=None):
    keys = keys or ["utm_source", "campaign"]
    grouped = {key: defaultdict(lambda: {"finishCounts": Counter(), "textValues": []}) for key in keys}

    for record in valid_records:
        finish_id = record["row"].get("finishId") or ""
        finish_title = html_to_text((finish_map.get(finish_id) or {}).get("title")) or finish_id or "未命名结束页"
        payload = record["payload"]
        extra = payload.get("extra") or {}

        text_samples = []
        for answer in payload.get("answers", []):
            if not isinstance(answer, dict):
                continue
            value = answer.get("value")
            if isinstance(value, dict):
                for child in value.get("child") or []:
                    if isinstance(child, dict) and str(child.get("value", "")).strip():
                        text_samples.append({"value": child.get("value", "")})
            elif isinstance(value, list):
                for item in value:
                    if not isinstance(item, dict):
                        continue
                    if "child" in item:
                        for child in item.get("child") or []:
                            if isinstance(child, dict) and str(child.get("value", "")).strip():
                                text_samples.append({"value": child.get("value", "")})
                    elif item.get("dataType") == "text" and str(item.get("value", "")).strip():
                        text_samples.append({"value": item.get("value", "")})

        for key in keys:
            value = extra.get(key)
            if value is None:
                continue
            values = value if isinstance(value, list) else [value]
            for one in values:
                label = str(one).strip()
                if not label:
                    continue
                bucket = grouped[key][label]
                bucket["finishCounts"][finish_title] += 1
                bucket["textValues"].extend(text_samples)

    result = []
    for key, buckets in grouped.items():
        for bucket_value, data in buckets.items():
            sentiment = analyze_sentiment(data["textValues"]) if data["textValues"] else None
            result.append({
                "extraKey": key,
                "extraValue": bucket_value,
                "finishCounts": dict(data["finishCounts"]),
                "textSentiment": sentiment,
            })
    return result


def build_analysis(schema, dataset_records, cross_config=None, analysis_config=None, max_cross_tabs=12):
    question_map, option_map, child_map, finish_map = build_schema_maps(schema)
    survey_id = schema.get("survey", {}).get("id")
    valid_records = []
    invalid_records = []
    rows = []
    question_stats = {}
    question_order = [q.get("id") for q in schema.get("questions") or [] if q.get("id")]

    for qid in question_order:
        question = question_map[qid]
        question_stats[qid] = {
            "questionId": qid,
            "questionType": question.get("type"),
            "title": html_to_text(question.get("title")),
            "description": html_to_text(question.get("description")),
            "responses": 0,
            "missing": 0,
            "optionCounts": Counter(),
            "scoreCounts": Counter(),
            "textValues": [],
            "childValues": [],
            "optionLabels": {oid: html_to_text(opt.get("title")) for oid, opt in option_map[qid].items()},
            "avgScore": None,
        }

    for index, record in enumerate(dataset_records):
        payload, meta = normalize_record(record)
        if not isinstance(payload, dict):
            invalid_records.append({"index": index, "reason": "record is not an object"})
            continue
        if payload.get("surveyId") != survey_id:
            invalid_records.append({"index": index, "reason": "surveyId mismatch"})
            continue
        answers = payload.get("answers")
        if not isinstance(answers, list):
            invalid_records.append({"index": index, "reason": "answers missing"})
            continue

        answer_map = {answer.get("questionId"): answer for answer in answers if isinstance(answer, dict) and answer.get("questionId")}
        logic_info = infer_logic_segments(schema, answer_map)
        finish_title = html_to_text((finish_map.get(logic_info["finishId"]) or {}).get("title")) if logic_info["finishId"] else ""

        base_row = {
            "submissionId": meta.get("submissionId", f"row-{index + 1}"),
            "surveyId": payload.get("surveyId"),
            "submittedAt": payload.get("submittedAt"),
            "receivedAt": meta.get("receivedAt"),
            "finishId": logic_info["finishId"] or "",
            "finishTitle": finish_title,
            "matchedLogicRules": ", ".join(logic_info["matchedRules"]),
            "extra": json.dumps(payload.get("extra", {}), ensure_ascii=False),
        }

        for qid in question_order:
            question = question_map[qid]
            answer = answer_map.get(qid)
            formatted, details = flatten_answer_value(question, answer, option_map[qid], child_map[qid])
            base_row[qid] = formatted
            stats = question_stats[qid]
            if answer:
                stats["responses"] += 1
            else:
                stats["missing"] += 1

            for detail in details:
                kind = detail.get("kind")
                if kind == "option":
                    stats["optionCounts"][detail["label"]] += 1
                elif kind == "child":
                    stats["childValues"].append({
                        "questionId": qid,
                        "label": detail["label"],
                        "value": detail["value"],
                        "parent": detail.get("parent"),
                        "isInfoCollection": not should_analyze_text(qid, detail["label"], None, analysis_config),
                    })
                elif kind == "input":
                    stats["textValues"].append({
                        "questionId": qid,
                        "label": detail["label"],
                        "value": detail["value"],
                        "dataType": detail.get("dataType"),
                        "isInfoCollection": not should_analyze_text(qid, detail["label"], detail.get("dataType"), analysis_config),
                    })
                elif kind == "score":
                    stats["scoreCounts"][f"{detail['label']}::{detail['value']}"] += 1
                elif kind == "nps":
                    stats["scoreCounts"][str(detail["value"])] += 1
                    stats.setdefault("npsBands", Counter())[nps_band(detail["value"])] += 1

            if question.get("type") == "radio":
                for oid in extract_choice_option_ids(answer):
                    label = stats["optionLabels"].get(oid, oid)
                    stats["optionCounts"][label] += 1
            elif question.get("type") == "checkbox":
                for oid in extract_choice_option_ids(answer):
                    label = stats["optionLabels"].get(oid, oid)
                    stats["optionCounts"][label] += 1
            elif question.get("type") == "score" and answer and isinstance(answer.get("value"), list):
                scores = []
                for item in answer["value"]:
                    if isinstance(item, dict) and isinstance(item.get("score"), (int, float)):
                        scores.append(float(item["score"]))
                if scores:
                    stats.setdefault("scoreSamples", []).extend(scores)
            elif question.get("type") == "nps" and answer and isinstance(answer.get("value"), dict):
                score = answer["value"].get("score")
                if isinstance(score, (int, float)):
                    stats.setdefault("scoreSamples", []).append(float(score))

        rows.append(base_row)
        valid_records.append({"payload": payload, "meta": meta, "row": base_row})

    for qid, stats in question_stats.items():
        samples = stats.get("scoreSamples") or []
        if samples:
            stats["avgScore"] = round(sum(samples) / len(samples), 2)
        analyzable_text_values = [item for item in stats["textValues"] if not item.get("isInfoCollection")]
        analyzable_child_values = [item for item in stats["childValues"] if not item.get("isInfoCollection")]
        if analyzable_text_values:
            stats["textThemes"] = extract_text_themes(analyzable_text_values)
            stats["textSentiment"] = analyze_sentiment(analyzable_text_values)
        if analyzable_child_values:
            stats["childThemes"] = extract_text_themes(analyzable_child_values)
            stats["childSentiment"] = analyze_sentiment(analyzable_child_values)

    cross_tabs = build_cross_tabs(question_map, valid_records, cross_config=cross_config, max_cross_tabs=max_cross_tabs)
    finish_sentiment_rows = aggregate_finish_sentiment(valid_records, finish_map)
    extra_finish_rows = aggregate_extra_finish_analysis(valid_records, finish_map)
    insights = build_insights(
        schema,
        question_stats,
        valid_records,
        invalid_records,
        cross_tabs,
        finish_map,
        finish_sentiment_rows,
        extra_finish_rows,
    )

    return {
        "surveyId": survey_id,
        "surveyTitle": html_to_text(schema.get("survey", {}).get("title")),
        "rows": rows,
        "validRecords": valid_records,
        "invalidRecords": invalid_records,
        "questionStats": question_stats,
        "questionOrder": question_order,
        "crossTabs": cross_tabs,
        "finishSentimentRows": finish_sentiment_rows,
        "extraFinishRows": extra_finish_rows,
        "insights": insights,
    }


def build_cross_tabs(question_map, valid_records, cross_config=None, max_cross_tabs=12):
    crosstabs = []
    radio_questions = [q for q in question_map.values() if q.get("type") == "radio"]
    score_like_questions = [q for q in question_map.values() if q.get("type") in {"score", "nps"}]
    checkbox_questions = [q for q in question_map.values() if q.get("type") == "checkbox"]
    allowed_pairs = None

    if isinstance(cross_config, dict):
        pairs = cross_config.get("pairs")
        if isinstance(pairs, list):
            allowed_pairs = set()
            for item in pairs:
                if isinstance(item, dict) and item.get("segmentQuestionId") and item.get("metricQuestionId"):
                    allowed_pairs.add((item["segmentQuestionId"], item["metricQuestionId"]))

    def pair_allowed(segment_id, metric_id):
        return allowed_pairs is None or (segment_id, metric_id) in allowed_pairs

    for radio in radio_questions:
        radio_id = radio["id"]
        for score_q in score_like_questions:
            if not pair_allowed(radio_id, score_q["id"]):
                continue
            matrix = defaultdict(list)
            for record in valid_records:
                payload = record["payload"]
                answer_map = {a.get("questionId"): a for a in payload.get("answers", []) if isinstance(a, dict)}
                radio_answer = answer_map.get(radio_id)
                score_answer = answer_map.get(score_q["id"])
                if not radio_answer or not score_answer:
                    continue
                radio_opts = extract_choice_option_ids(radio_answer)
                if not radio_opts:
                    continue
                radio_key = radio_opts[0]
                if score_q["type"] == "nps":
                    score = score_answer.get("value", {}).get("score")
                    if isinstance(score, (int, float)):
                        matrix[radio_key].append(float(score))
                else:
                    values = score_answer.get("value")
                    if isinstance(values, list):
                        scores = [float(item["score"]) for item in values if isinstance(item, dict) and isinstance(item.get("score"), (int, float))]
                        if scores:
                            matrix[radio_key].append(sum(scores) / len(scores))
            rows = []
            for key, values in matrix.items():
                rows.append({
                    "segmentId": key,
                    "segmentLabel": html_to_text(next((opt.get("title") for opt in radio.get("option") or [] if opt.get("id") == key), key)),
                    "metric": score_q["id"],
                    "metricLabel": html_to_text(score_q.get("title")),
                    "count": len(values),
                    "average": round(sum(values) / len(values), 2) if values else None,
                })
            if rows:
                crosstabs.append({
                    "type": "radio_vs_score",
                    "segmentQuestionId": radio_id,
                    "metricQuestionId": score_q["id"],
                    "title": f"{html_to_text(radio.get('title'))} x {html_to_text(score_q.get('title'))}",
                    "rows": rows,
                })
                if len(crosstabs) >= max_cross_tabs:
                    return crosstabs

    for radio in radio_questions:
        radio_id = radio["id"]
        for checkbox in checkbox_questions:
            if not pair_allowed(radio_id, checkbox["id"]):
                continue
            counts = defaultdict(Counter)
            for record in valid_records:
                payload = record["payload"]
                answer_map = {a.get("questionId"): a for a in payload.get("answers", []) if isinstance(a, dict)}
                radio_answer = answer_map.get(radio_id)
                checkbox_answer = answer_map.get(checkbox["id"])
                if not radio_answer or not checkbox_answer:
                    continue
                radio_opts = extract_choice_option_ids(radio_answer)
                checkbox_opts = extract_choice_option_ids(checkbox_answer)
                if not radio_opts or not checkbox_opts:
                    continue
                segment = radio_opts[0]
                for opt in checkbox_opts:
                    counts[segment][opt] += 1
            rows = []
            for segment, counter in counts.items():
                for opt_id, count in counter.items():
                    rows.append({
                        "segmentId": segment,
                        "segmentLabel": html_to_text(next((opt.get("title") for opt in radio.get("option") or [] if opt.get("id") == segment), segment)),
                        "optionId": opt_id,
                        "optionLabel": html_to_text(next((opt.get("title") for opt in checkbox.get("option") or [] if opt.get("id") == opt_id), opt_id)),
                        "count": count,
                    })
            if rows:
                crosstabs.append({
                    "type": "radio_vs_checkbox",
                    "segmentQuestionId": radio_id,
                    "metricQuestionId": checkbox["id"],
                    "title": f"{html_to_text(radio.get('title'))} x {html_to_text(checkbox.get('title'))}",
                    "rows": rows,
                })
                if len(crosstabs) >= max_cross_tabs:
                    return crosstabs
    return crosstabs


def build_insights(schema, question_stats, valid_records, invalid_records, cross_tabs, finish_map, finish_sentiment_rows, extra_finish_rows):
    survey_title = html_to_text(schema.get("survey", {}).get("title"))
    total = len(valid_records) + len(invalid_records)
    valid = len(valid_records)
    invalid = len(invalid_records)
    warnings = []
    if invalid:
        warnings.append(f"{invalid} 条记录被排除，因为 surveyId 不匹配或 answers 结构无效。")
    if valid < 10:
        warnings.append("有效样本量较低，建议谨慎解读百分比和均值。")

    recommendations = []
    question_findings = []
    for qid, stats in question_stats.items():
        qtitle = stats["title"] or qid
        qtype = stats["questionType"]
        if qtype in {"radio", "checkbox"} and stats["optionCounts"]:
            top_label, top_count = stats["optionCounts"].most_common(1)[0]
            question_findings.append(f"{qtitle} 中出现频次最高的是“{top_label}”，共 {top_count} 次。")
        elif qtype in {"score", "nps"} and stats.get("avgScore") is not None:
            question_findings.append(f"{qtitle} 的平均分为 {stats['avgScore']}。")
            if stats["avgScore"] < 3 and qtype == "score":
                recommendations.append(f"优先排查 {qtitle} 对应维度，当前均分偏低。")
            if qtype == "nps" and stats["avgScore"] < 7:
                recommendations.append("NPS 偏低，建议优先回看不满意路径和补充文本原因。")
        elif qtype == "input" and stats["textValues"]:
            question_findings.append(f"{qtitle} 共收集到 {len(stats['textValues'])} 条文本输入，适合进一步做人工主题归纳。")
            if stats.get("textThemes"):
                top_terms = "、".join(f"{item['term']}({item['count']})" for item in stats["textThemes"][:3])
                question_findings.append(f"{qtitle} 的高频文本主题包括：{top_terms}。")
            sentiment = stats.get("textSentiment")
            if sentiment and sentiment.get("total"):
                question_findings.append(
                    f"{qtitle} 的文本情感以 {sentiment['dominantLabel']} 为主，"
                    f"高度满意 {sentiment['counts'].get('strong_positive', 0)} 条，"
                    f"满意 {sentiment['counts'].get('positive', 0)} 条，"
                    f"中性 {sentiment['counts'].get('neutral', 0)} 条，"
                    f"不满 {sentiment['counts'].get('negative', 0)} 条，"
                    f"强烈不满 {sentiment['counts'].get('strong_negative', 0)} 条。"
                )
        if stats.get("childThemes"):
            top_terms = "、".join(f"{item['term']}({item['count']})" for item in stats["childThemes"][:3])
            if top_terms:
                question_findings.append(f"{qtitle} 的补充说明高频主题包括：{top_terms}。")
        child_sentiment = stats.get("childSentiment")
        if child_sentiment and child_sentiment.get("total"):
            question_findings.append(
                f"{qtitle} 的补充说明情感以 {child_sentiment['dominantLabel']} 为主，"
                f"高度满意 {child_sentiment['counts'].get('strong_positive', 0)} 条，"
                f"满意 {child_sentiment['counts'].get('positive', 0)} 条，"
                f"中性 {child_sentiment['counts'].get('neutral', 0)} 条，"
                f"不满 {child_sentiment['counts'].get('negative', 0)} 条，"
                f"强烈不满 {child_sentiment['counts'].get('strong_negative', 0)} 条。"
            )

    segment_findings = []
    for tab in cross_tabs[:8]:
        if tab["type"] == "radio_vs_score":
            ranked = [row for row in tab["rows"] if row.get("average") is not None]
            ranked.sort(key=lambda item: item["average"], reverse=True)
            if len(ranked) >= 2:
                best = ranked[0]
                worst = ranked[-1]
                segment_findings.append(
                    f"{tab['title']} 中，“{best['segmentLabel']}”的平均值最高为 {best['average']}，"
                    f"“{worst['segmentLabel']}”最低为 {worst['average']}。"
                )
        elif tab["type"] == "radio_vs_checkbox":
            grouped = defaultdict(list)
            for row in tab["rows"]:
                grouped[row["segmentLabel"]].append(row)
            for segment, rows in list(grouped.items())[:2]:
                top = sorted(rows, key=lambda item: item["count"], reverse=True)[0]
                segment_findings.append(f"{tab['title']} 中，“{segment}”最常提到的是“{top['optionLabel']}”（{top['count']} 次）。")

    finish_counter = Counter()
    for record in valid_records:
        finish_counter[record["row"].get("finishId") or ""] += 1
    finish_findings = []
    for finish_id, count in finish_counter.most_common():
        if not finish_id:
            continue
        finish_title = html_to_text((finish_map.get(finish_id) or {}).get("title")) or finish_id
        finish_findings.append(f"进入结束页“{finish_title}”的样本有 {count} 条。")
    for row in finish_sentiment_rows:
        finish_findings.append(
            f"结束页“{row['finishTitle']}”下的文本情绪以 {row['dominantLabel']} 为主，"
            f"高度满意 {row['counts'].get('strong_positive', 0)} 条，"
            f"满意 {row['counts'].get('positive', 0)} 条，"
            f"中性 {row['counts'].get('neutral', 0)} 条，"
            f"不满 {row['counts'].get('negative', 0)} 条，"
            f"强烈不满 {row['counts'].get('strong_negative', 0)} 条。"
        )

    channel_findings = []
    for row in extra_finish_rows:
        finish_counts = row.get("finishCounts") or {}
        if not finish_counts:
            continue
        top_finish, top_count = sorted(finish_counts.items(), key=lambda item: item[1], reverse=True)[0]
        line = f"{row['extraKey']}={row['extraValue']} 的样本最常进入结束页“{top_finish}”（{top_count} 条）。"
        sentiment = row.get("textSentiment")
        if sentiment and sentiment.get("total"):
            line += (
                f" 该来源文本情绪以 {sentiment['dominantLabel']} 为主，"
                f"不满 {sentiment['counts'].get('negative', 0)} 条，"
                f"强烈不满 {sentiment['counts'].get('strong_negative', 0)} 条。"
            )
        channel_findings.append(line)

    summary = (
        f"{survey_title or '该问卷'}共收到 {total} 条记录，其中有效 {valid} 条、无效 {invalid} 条。"
        f"本次分析以题目分布、评分结果、逻辑分流和交叉对比为主。"
    )

    if not recommendations:
        recommendations.append("当前样本没有明显异常分层，建议先扩充样本量，再结合文本题做二次归因。")

    return {
        "summary": summary,
        "sample": {"total": total, "valid": valid, "invalid": invalid},
        "questions": question_findings,
        "segments": segment_findings,
        "finishes": finish_findings,
        "channels": channel_findings,
        "warnings": warnings,
        "recommendations": recommendations,
    }


def write_workbook(output_path, analysis):
    workbook = xlsxwriter.Workbook(str(output_path))
    fmt_header = workbook.add_format({"bold": True, "bg_color": "#111111", "font_color": "#FFFFFF", "border": 1})
    fmt_wrap = workbook.add_format({"text_wrap": True, "valign": "top", "border": 1})
    fmt_num = workbook.add_format({"border": 1})
    fmt_title = workbook.add_format({"bold": True, "font_size": 14})

    summary_ws = workbook.add_worksheet("Overview")
    summary_ws.write("A1", analysis["surveyTitle"] or analysis["surveyId"], fmt_title)
    summary_ws.write("A3", "Survey ID", fmt_header)
    summary_ws.write("B3", analysis["surveyId"], fmt_wrap)
    summary_ws.write("A4", "Summary", fmt_header)
    summary_ws.write("B4", analysis["insights"]["summary"], fmt_wrap)
    sample = analysis["insights"]["sample"]
    summary_ws.write_row("A6", ["Total", "Valid", "Invalid"], fmt_header)
    summary_ws.write_row("A7", [sample["total"], sample["valid"], sample["invalid"]], fmt_num)
    summary_ws.set_column("A:A", 18)
    summary_ws.set_column("B:B", 80)

    raw_ws = workbook.add_worksheet("Responses")
    headers = ["submissionId", "surveyId", "submittedAt", "receivedAt", "finishId", "finishTitle", "matchedLogicRules", "extra"] + analysis["questionOrder"]
    for col, header in enumerate(headers):
        raw_ws.write(0, col, header, fmt_header)
    for row_index, row in enumerate(analysis["rows"], start=1):
        for col, header in enumerate(headers):
            raw_ws.write(row_index, col, row.get(header, ""), fmt_wrap)
    raw_ws.freeze_panes(1, 0)
    raw_ws.autofilter(0, 0, max(1, len(analysis["rows"])), len(headers) - 1)
    raw_ws.set_column(0, len(headers) - 1, 22)

    question_summary_ws = workbook.add_worksheet("Question Summary")
    question_summary_headers = ["questionId", "questionType", "title", "responses", "missing", "answerRate", "avgScore"]
    for col, header in enumerate(question_summary_headers):
        question_summary_ws.write(0, col, header, fmt_header)
    total_valid = max(1, len(analysis["validRecords"]))
    for row_idx, qid in enumerate(analysis["questionOrder"], start=1):
        stats = analysis["questionStats"][qid]
        question_summary_ws.write_row(
            row_idx,
            0,
            [
                qid,
                stats["questionType"],
                stats["title"],
                stats["responses"],
                stats["missing"],
                round(stats["responses"] / total_valid, 4),
                stats.get("avgScore"),
            ],
            fmt_wrap,
        )
    question_summary_ws.set_column("A:C", 24)
    question_summary_ws.set_column("D:G", 14)

    charts_ws = workbook.add_worksheet("Charts")
    charts_ws.write("A1", "Per-question charts are distributed into dedicated sheets.", fmt_wrap)

    chart_sheet_index = 0
    for qid in analysis["questionOrder"]:
        stats = analysis["questionStats"][qid]
        sheet_name = safe_sheet_name(f"Q{chart_sheet_index + 1}", f"Q{chart_sheet_index + 1}")
        ws = workbook.add_worksheet(sheet_name)
        ws.write("A1", stats["title"] or qid, fmt_title)
        ws.write("A2", qid, fmt_wrap)
        question_type = stats["questionType"]
        if question_type in {"radio", "checkbox"} and stats["optionCounts"]:
            ws.write_row("A4", ["Option", "Count"], fmt_header)
            for idx, (label, count) in enumerate(stats["optionCounts"].most_common(), start=5):
                ws.write_row(idx - 1, 0, [label, count], fmt_wrap)
            chart = workbook.add_chart({"type": "column"})
            chart.add_series({
                "name": stats["title"],
                "categories": [sheet_name, 4, 0, 4 + len(stats["optionCounts"]) - 1, 0],
                "values": [sheet_name, 4, 1, 4 + len(stats["optionCounts"]) - 1, 1],
                "data_labels": {"value": True},
            })
            chart.set_title({"name": stats["title"]})
            chart.set_style(10)
            ws.insert_chart("D4", chart, {"x_scale": 1.2, "y_scale": 1.2})
        elif question_type == "score" and stats["scoreCounts"]:
            ws.write_row("A4", ["Metric", "Count"], fmt_header)
            items = sorted(stats["scoreCounts"].items())
            for idx, (label, count) in enumerate(items, start=5):
                ws.write_row(idx - 1, 0, [label, count], fmt_wrap)
            chart = workbook.add_chart({"type": "column"})
            chart.add_series({
                "name": stats["title"],
                "categories": [sheet_name, 4, 0, 4 + len(items) - 1, 0],
                "values": [sheet_name, 4, 1, 4 + len(items) - 1, 1],
                "data_labels": {"value": True},
            })
            chart.set_title({"name": f"{stats['title']} (avg {stats.get('avgScore')})"})
            chart.set_style(11)
            ws.insert_chart("D4", chart, {"x_scale": 1.25, "y_scale": 1.2})
        elif question_type == "nps" and stats["scoreCounts"]:
            ws.write_row("A4", ["Score", "Count"], fmt_header)
            score_items = sorted(((int(label), count) for label, count in stats["scoreCounts"].items()), key=lambda item: item[0])
            for idx, (label, count) in enumerate(score_items, start=5):
                ws.write_row(idx - 1, 0, [label, count], fmt_wrap)
            chart = workbook.add_chart({"type": "line"})
            chart.add_series({
                "name": stats["title"],
                "categories": [sheet_name, 4, 0, 4 + len(score_items) - 1, 0],
                "values": [sheet_name, 4, 1, 4 + len(score_items) - 1, 1],
                "marker": {"type": "circle", "size": 7},
                "data_labels": {"value": True},
            })
            chart.set_title({"name": f"{stats['title']} (avg {stats.get('avgScore')})"})
            chart.set_style(12)
            ws.insert_chart("D4", chart, {"x_scale": 1.25, "y_scale": 1.2})
            band_counter = stats.get("npsBands") or Counter()
            if band_counter:
                start_row = 4 + len(score_items) + 3
                ws.write_row(start_row, 0, ["Band", "Count"], fmt_header)
                for offset, (label, count) in enumerate(band_counter.items(), start=1):
                    ws.write_row(start_row + offset, 0, [label, count], fmt_wrap)
        elif question_type == "input" and stats["textValues"]:
            ws.write_row("A4", ["Field", "Value"], fmt_header)
            for idx, item in enumerate(stats["textValues"][:50], start=5):
                ws.write_row(idx - 1, 0, [item["label"], item["value"]], fmt_wrap)
            themes = stats.get("textThemes") or []
            sentiment = stats.get("textSentiment")
            start_row = 5 + min(len(stats["textValues"]), 50) + 2
            if sentiment and sentiment.get("total"):
                ws.write_row(start_row, 0, ["Sentiment", "Count"], fmt_header)
                ordered = ["strong_positive", "positive", "neutral", "negative", "strong_negative"]
                for offset, label in enumerate(ordered, start=1):
                    ws.write_row(start_row + offset, 0, [SENTIMENT_LABELS[label], sentiment["counts"].get(label, 0)], fmt_wrap)
                start_row += 6
            if themes:
                ws.write_row(start_row, 0, ["Theme", "Count"], fmt_header)
                for offset, theme in enumerate(themes, start=1):
                    ws.write_row(start_row + offset, 0, [theme["term"], theme["count"]], fmt_wrap)
        else:
            ws.write("A4", "No chartable data in current dataset.", fmt_wrap)
        ws.set_column("A:A", 28)
        ws.set_column("B:B", 40)
        chart_sheet_index += 1

    cross_ws = workbook.add_worksheet("Cross Tabs")
    cross_ws.write_row("A1", ["title", "segment", "metric", "count", "average", "option"], fmt_header)
    row_cursor = 1
    for tab in analysis["crossTabs"]:
        for row in tab["rows"]:
            cross_ws.write_row(
                row_cursor,
                0,
                [
                    tab["title"],
                    row.get("segmentLabel"),
                    row.get("metricLabel") or row.get("metric"),
                    row.get("count"),
                    row.get("average"),
                    row.get("optionLabel"),
                ],
                fmt_wrap,
            )
            row_cursor += 1
    cross_ws.set_column("A:C", 28)
    cross_ws.set_column("D:F", 14)

    finish_sentiment_ws = workbook.add_worksheet("Finish Sentiment")
    finish_sentiment_ws.write_row(
        "A1",
        ["finishId", "finishTitle", "totalTextResponses", "dominant", "高度满意", "满意", "中性", "不满", "强烈不满"],
        fmt_header,
    )
    for idx, row in enumerate(analysis.get("finishSentimentRows") or [], start=2):
        finish_sentiment_ws.write_row(
            idx - 1,
            0,
            [
                row["finishId"],
                row["finishTitle"],
                row["totalTextResponses"],
                row["dominantLabel"],
                row["counts"].get("strong_positive", 0),
                row["counts"].get("positive", 0),
                row["counts"].get("neutral", 0),
                row["counts"].get("negative", 0),
                row["counts"].get("strong_negative", 0),
            ],
            fmt_wrap,
        )
    finish_sentiment_ws.set_column("A:B", 28)
    finish_sentiment_ws.set_column("C:I", 14)

    extra_ws = workbook.add_worksheet("Extra Analysis")
    extra_ws.write_row(
        "A1",
        ["extraKey", "extraValue", "topFinish", "topFinishCount", "dominantSentiment", "高度满意", "满意", "中性", "不满", "强烈不满"],
        fmt_header,
    )
    for idx, row in enumerate(analysis.get("extraFinishRows") or [], start=2):
        finish_counts = row.get("finishCounts") or {}
        top_finish = ""
        top_count = 0
        if finish_counts:
            top_finish, top_count = sorted(finish_counts.items(), key=lambda item: item[1], reverse=True)[0]
        sentiment = row.get("textSentiment") or {"counts": {}, "dominantLabel": ""}
        extra_ws.write_row(
            idx - 1,
            0,
            [
                row["extraKey"],
                row["extraValue"],
                top_finish,
                top_count,
                sentiment.get("dominantLabel", ""),
                sentiment.get("counts", {}).get("strong_positive", 0),
                sentiment.get("counts", {}).get("positive", 0),
                sentiment.get("counts", {}).get("neutral", 0),
                sentiment.get("counts", {}).get("negative", 0),
                sentiment.get("counts", {}).get("strong_negative", 0),
            ],
            fmt_wrap,
        )
    extra_ws.set_column("A:E", 24)
    extra_ws.set_column("F:J", 12)

    insights_ws = workbook.add_worksheet("Insights")
    insights_ws.set_column("A:A", 18)
    insights_ws.set_column("B:B", 90)
    row_ptr = 0
    for title, items in [
        ("Summary", [analysis["insights"]["summary"]]),
        ("Warnings", analysis["insights"]["warnings"]),
        ("Question Findings", analysis["insights"]["questions"]),
        ("Segment Findings", analysis["insights"]["segments"]),
        ("Finish Findings", analysis["insights"]["finishes"]),
        ("Channel Findings", analysis["insights"].get("channels", [])),
        ("Recommendations", analysis["insights"]["recommendations"]),
    ]:
        insights_ws.write(row_ptr, 0, title, fmt_header)
        if not items:
            insights_ws.write(row_ptr, 1, "", fmt_wrap)
            row_ptr += 1
            continue
        for item in items:
            insights_ws.write(row_ptr, 1, item, fmt_wrap)
            row_ptr += 1
        row_ptr += 1

    workbook.close()


def write_reports(output_prefix, analysis):
    report = {
        "surveyId": analysis["surveyId"],
        "summary": analysis["insights"]["summary"],
        "sample": analysis["insights"]["sample"],
        "questions": analysis["insights"]["questions"],
        "segments": analysis["insights"]["segments"],
        "finishes": analysis["insights"]["finishes"],
        "channels": analysis["insights"].get("channels", []),
        "warnings": analysis["insights"]["warnings"],
        "recommendations": analysis["insights"]["recommendations"],
    }
    json_path = output_prefix.with_suffix(".analysis.json")
    md_path = output_prefix.with_suffix(".analysis.md")
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        f"# {analysis['surveyTitle'] or analysis['surveyId']} Analysis",
        "",
        "## Overview",
        report["summary"],
        "",
        "## Sample",
        f"- Total: {report['sample']['total']}",
        f"- Valid: {report['sample']['valid']}",
        f"- Invalid: {report['sample']['invalid']}",
        "",
        "## Question Findings",
    ]
    lines.extend([f"- {item}" for item in report["questions"]] or ["- None"])
    lines.extend(["", "## Segment Findings"])
    lines.extend([f"- {item}" for item in report["segments"]] or ["- None"])
    lines.extend(["", "## Finish Findings"])
    lines.extend([f"- {item}" for item in report["finishes"]] or ["- None"])
    lines.extend(["", "## Channel Findings"])
    lines.extend([f"- {item}" for item in report.get("channels", [])] or ["- None"])
    lines.extend(["", "## Warnings"])
    lines.extend([f"- {item}" for item in report["warnings"]] or ["- None"])
    lines.extend(["", "## Recommendations"])
    lines.extend([f"- {item}" for item in report["recommendations"]] or ["- None"])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def main():
    parser = argparse.ArgumentParser(description="Analyze survey schema + answer dataset and generate workbook/report artifacts.")
    parser.add_argument("--schema", required=True, help="Path to survey schema JSON")
    parser.add_argument("--answers", required=True, help="Path to answers dataset JSON or JSONL")
    parser.add_argument("--out-dir", required=True, help="Directory for generated artifacts")
    parser.add_argument("--name", help="Optional base filename without extension")
    parser.add_argument("--cross-config", help="Optional JSON file describing explicit cross-tab pairs")
    parser.add_argument("--analysis-config", help="Optional JSON file controlling text-analysis scope and other future analysis settings")
    parser.add_argument("--max-cross-tabs", type=int, default=12, help="Maximum cross-tab tables to generate")
    args = parser.parse_args()

    schema = load_schema(args.schema)
    records = load_json_or_jsonl(args.answers)
    cross_config = load_optional_json(args.cross_config)
    analysis_config = load_analysis_config(args.analysis_config)
    analysis = build_analysis(
        schema,
        records,
        cross_config=cross_config,
        analysis_config=analysis_config,
        max_cross_tabs=max(1, args.max_cross_tabs),
    )

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    base_name = args.name or analysis["surveyId"] or "survey-analysis"
    output_prefix = out_dir / base_name

    workbook_path = output_prefix.with_suffix(".analysis.xlsx")
    write_workbook(workbook_path, analysis)
    json_path, md_path = write_reports(output_prefix, analysis)

    print(json.dumps({
        "ok": True,
        "surveyId": analysis["surveyId"],
        "workbook": str(workbook_path),
        "reportJson": str(json_path),
        "reportMarkdown": str(md_path),
        "validSubmissions": analysis["insights"]["sample"]["valid"],
        "invalidSubmissions": analysis["insights"]["sample"]["invalid"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
