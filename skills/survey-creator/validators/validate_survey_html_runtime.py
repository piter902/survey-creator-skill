#!/usr/bin/env python3
import json, re, sys
from pathlib import Path

class Reporter:
    def __init__(self):
        self.errors = []
        self.warnings = []
    def error(self, path, message):
        self.errors.append({"path": path, "message": message})
    def warn(self, path, message):
        self.warnings.append({"path": path, "message": message})
    def result(self, extra=None):
        base = {"valid": len(self.errors) == 0, "errors": self.errors, "warnings": self.warnings}
        if extra:
            base.update(extra)
        return base


def has(text, pattern):
    return pattern.search(text) is not None if hasattr(pattern, "search") else pattern in text


def check_pattern(text, reporter, key, message, pattern, level="error"):
    if not has(text, pattern):
        getattr(reporter, level)(key, message)


def extract_survey_schema_literal(html):
    marker = "const surveySchema ="
    start = html.find(marker)
    if start == -1:
        return None
    start = html.find("{", start)
    if start == -1:
        return None
    depth = 0
    in_single = in_double = in_template = escaped = False
    for i in range(start, len(html)):
        ch = html[i]
        if escaped:
            escaped = False
            continue
        if ch == "\\":
            escaped = True
            continue
        if not in_double and not in_template and ch == "'":
            in_single = not in_single
            continue
        if not in_single and not in_template and ch == '"':
            in_double = not in_double
            continue
        if not in_single and not in_double and ch == "`":
            in_template = not in_template
            continue
        if in_single or in_double or in_template:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return html[start:i+1]
    return None


def validate_html_runtime(html):
    reporter = Reporter()
    check_pattern(html, reporter, "html.doctype", "HTML must include <!DOCTYPE html>.", re.compile(r"<!DOCTYPE html>", re.I))
    check_pattern(html, reporter, "html.form", "HTML must include a real <form> element.", re.compile(r"<form\b", re.I))
    check_pattern(html, reporter, "html.schema", "HTML should contain a surveySchema object.", "const surveySchema =")
    check_pattern(html, reporter, "runtime.render", "HTML should render screens from schema.", "render()")
    check_pattern(html, reporter, "runtime.assemblePayload", "HTML should define assemblePayload().", "function assemblePayload()")
    check_pattern(html, reporter, "runtime.validateQuestion", "HTML should define validateQuestion().", "function validateQuestion(")
    check_pattern(html, reporter, "runtime.bindEvents", "HTML should define bindEvents().", "function bindEvents()")
    check_pattern(html, reporter, "runtime.childVisibility", "HTML should manage child visibility.", "function updateChildVisibility()")
    check_pattern(html, reporter, "runtime.localStorageSet", "HTML should persist step cache with localStorage.setItem.", "localStorage.setItem(")
    check_pattern(html, reporter, "runtime.localStorageRemove", "HTML should clear cache with localStorage.removeItem after submit.", "localStorage.removeItem(")
    check_pattern(html, reporter, "runtime.consoleLog", "HTML should output payload with console.log.", re.compile(r"console\.log\((payload|assemblePayload\(\))\)"))
    check_pattern(html, reporter, "runtime.optionId", "HTML should preserve option ids in DOM using data-option-id.", "data-option-id")
    check_pattern(html, reporter, "runtime.childId", "HTML should preserve child ids in DOM using data-child-id.", "data-child-id")
    check_pattern(html, reporter, "runtime.exclusive", "HTML should implement checkbox exclusive logic.", "dataset.exclusive")
    check_pattern(html, reporter, "runtime.mutual", "HTML should implement checkbox mutual-exclusion logic.", "dataset.mutualExclusion")
    check_pattern(html, reporter, "runtime.submitIntercept", "HTML should intercept form submit.", "form.addEventListener('submit'")
    check_pattern(html, reporter, "runtime.changeIntercept", "HTML should react to checkbox/input changes.", "form.addEventListener('change'")
    check_pattern(html, reporter, "runtime.inputIntercept", "HTML should react to input changes for cache persistence.", "form.addEventListener('input'")

    # Explicit supported question-family runtime hooks. These checks keep the fixed renderer honest
    # as new question types are added. They are intentionally template-level checks rather than
    # business-content checks.
    check_pattern(html, reporter, "runtime.radio.collect", "HTML should collect radio answers.", "question.type === 'radio'")
    check_pattern(html, reporter, "runtime.checkbox.collect", "HTML should collect checkbox answers.", "question.type === 'checkbox'")
    check_pattern(html, reporter, "runtime.input.collect", "HTML should collect input answers.", "question.type === 'input'")
    check_pattern(html, reporter, "runtime.score.render", "HTML should define score renderer.", "function renderScoreQuestion(")
    check_pattern(html, reporter, "runtime.score.collect", "HTML should collect score answers as score rows.", "question.type === 'score'")
    check_pattern(html, reporter, "runtime.score.optionId", "Score runtime should preserve score option ids.", "data-score-option-id")
    check_pattern(html, reporter, "runtime.score.display", "Score runtime should update active score display.", "function updateScoreDisplay(")
    check_pattern(html, reporter, "runtime.nps.render", "HTML should define NPS renderer.", "function renderNpsQuestion(")
    check_pattern(html, reporter, "runtime.nps.collect", "HTML should collect NPS answer as a single object.", "question.type === 'nps'")
    check_pattern(html, reporter, "runtime.nps.optionId", "NPS runtime should preserve NPS option id.", "data-nps-option")
    check_pattern(html, reporter, "runtime.nps.descRange", "NPS runtime should resolve range-based scoreDesc values.", "function scoreDescForValue(")
    check_pattern(html, reporter, "runtime.media", "HTML should support media rendering.", "function renderMedia(")

    check_pattern(html, reporter, "runtime.logic.compute", "HTML should define computeLogicState() for conditional logic.", "function computeLogicState()")
    check_pattern(html, reporter, "runtime.logic.apply", "HTML should define applyLogicRuntime() for conditional logic.", "function applyLogicRuntime(")
    check_pattern(html, reporter, "runtime.logic.jump", "HTML should preserve jump targets in runtime logic state.", "jumpTargets")
    check_pattern(html, reporter, "runtime.logic.jumpPage", "HTML should support jump_to_page logic actions.", "action.type === 'jump_to_page'")
    check_pattern(html, reporter, "runtime.logic.optionVisibility", "HTML should toggle option visibility for logic rules.", "isOptionHidden(")
    check_pattern(html, reporter, "runtime.logic.questionVisibility", "HTML should toggle question visibility for logic rules.", "isQuestionHidden(")
    if '"Pagination"' in html or "'Pagination'" in html:
        check_pattern(html, reporter, "runtime.pagination.answerable", "Pagination support should separate answerable questions from separators.", "answerableQuestions")
        check_pattern(html, reporter, "runtime.pagination.pages", "Pagination support should build manual pages from separators.", "buildManualPagesFromSeparators(")
        check_pattern(html, reporter, "runtime.pagination.screen", "Pagination support should render page screens.", "function renderManualPage(")

    if "onePageOneQuestion" in html:
        check_pattern(html, reporter, "runtime.screens", "Step mode should define screens().", "function screens()")
        check_pattern(html, reporter, "runtime.show", "Step mode should define show().", "function show(")
        check_pattern(html, reporter, "runtime.currentQuestion", "Step mode should define currentQuestion().", "function currentQuestion()")
    if "exclusive" in html and "!== e.target" not in html:
        reporter.warn("runtime.exclusive.detail", "Exclusive logic exists but could not find explicit exclusion of the current checkbox from clearing.")
    if "mutual-exclusion" in html and "otherMutual" not in html:
        reporter.warn("runtime.mutual.detail", "mutual-exclusion appears in schema/text but grouped clearing logic was not clearly detected.")
    if "renderRich(" in html and "function sanitizeRichText(" not in html:
        reporter.warn("runtime.richtext", "Rich-text rendering detected without explicit sanitizeRichText() hook.")
    if "renderRich(" in html and "sanitizeRichText(" not in html:
        reporter.warn("runtime.richtext.sanitizer", "Rich-text rendering detected without sanitizer hook; production use should add a whitelist sanitizer.")
    schema_literal = extract_survey_schema_literal(html)
    if not schema_literal:
        reporter.warn("runtime.schema.extract", "Could not extract surveySchema literal from HTML.")
    elif "randomId()" in schema_literal:
        reporter.warn("runtime.dynamicIds", "surveySchema contains runtime-generated ids. Production surveys should pre-freeze ids before delivery to users.")
    else:
        reporter.warn("runtime.staticSchemaOnly", "Schema literal was extracted. For stronger safety, validate it separately with validate_survey_schema.py.")
    if all(x in html for x in ["dateRange", "timeRange", "dateTimeRange"]):
        check_pattern(html, reporter, "runtime.rangeObject", "Range values should serialize to { start, end }.", re.compile(r"start[\s\S]*end"))
    summary = {"checks": {
        "doctype": has(html, re.compile(r"<!DOCTYPE html>", re.I)),
        "form": has(html, re.compile(r"<form\b", re.I)),
        "schema": "const surveySchema =" in html,
        "assemblePayload": "function assemblePayload()" in html,
        "localStorage": "localStorage.setItem(" in html and "localStorage.removeItem(" in html,
        "exclusive": "dataset.exclusive" in html,
        "mutualExclusion": "dataset.mutualExclusion" in html,
        "childVisibility": "function updateChildVisibility()" in html,
        "score": "function renderScoreQuestion(" in html and "question.type === 'score'" in html,
        "nps": "function renderNpsQuestion(" in html and "question.type === 'nps'" in html,
        "media": "function renderMedia(" in html,
        "logic": "function computeLogicState()" in html and "function applyLogicRuntime(" in html,
        "pagination": "buildManualPagesFromSeparators(" in html and "answerableQuestions" in html,
    }}
    return reporter.result(summary)


def print_human(report):
    print("✅ HTML runtime contract check passed." if report["valid"] else "❌ HTML runtime contract check failed.")
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
    if not file_arg:
        print("Usage: validate_survey_html_runtime.py /absolute/path/to/file.html [--json]", file=sys.stderr)
        sys.exit(1)
    try:
        html = Path(file_arg).read_text(encoding="utf-8")
    except FileNotFoundError as e:
        print(f"Failed to read HTML file: {e}", file=sys.stderr)
        sys.exit(1)
    report = validate_html_runtime(html)
    if json_output:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_human(report)
    sys.exit(0 if report["valid"] else 1)


if __name__ == "__main__":
    main()
