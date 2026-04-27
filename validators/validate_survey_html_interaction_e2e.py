#!/usr/bin/env python3
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from validate_survey_payload import validate_survey_payload
VALIDATORS_DIR = Path(__file__).resolve().parent

NODE_RUNNER = r"""
const path = require('path');
const { chromium } = require('playwright');

function valueForInput(type, index) {
  if (type === 'email') return 'name@example.com';
  if (type === 'tel') return '13800000000';
  if (type === 'number') return '42';
  if (type === 'date') return '2026-04-22';
  if (type === 'time') return index % 2 === 0 ? '09:00' : '18:00';
  if (type === 'datetime-local') return index % 2 === 0 ? '2026-04-22T09:00' : '2026-04-22T18:00';
  return '示例填写内容';
}

async function fillQuestionField(field) {
  const type = await field.getAttribute('data-schema-type');
  const questionId = await field.getAttribute('data-screen-id');
  if (!type || !questionId) return;

  if (type === 'radio') {
    let radio = field.locator(`input[type="radio"][name="${questionId}"]:not([data-has-child])`).first();
    if (!(await radio.count())) radio = field.locator(`input[type="radio"][name="${questionId}"]`).first();
    if (await radio.count()) await radio.check();
    const childControls = field.locator('.child-list.is-visible input.input, .child-list.is-visible textarea.textarea');
    const childCount = await childControls.count();
    for (let i = 0; i < childCount; i++) {
      const control = childControls.nth(i);
      const controlType = (await control.getAttribute('type')) || 'text';
      await control.fill(valueForInput(controlType, i));
    }
    return;
  }

  if (type === 'checkbox') {
    let checkbox = field.locator(`input[type="checkbox"][name="${questionId}"]:not([data-has-child])`).first();
    if (!(await checkbox.count())) checkbox = field.locator(`input[type="checkbox"][name="${questionId}"]`).first();
    if (await checkbox.count()) await checkbox.check();
    const childControls = field.locator('.child-list.is-visible input.input, .child-list.is-visible textarea.textarea');
    const childCount = await childControls.count();
    for (let i = 0; i < childCount; i++) {
      const control = childControls.nth(i);
      const controlType = (await control.getAttribute('type')) || 'text';
      await control.fill(valueForInput(controlType, i));
    }
    return;
  }

  if (type === 'input') {
    const controls = field.locator('input.input, textarea.textarea');
    const count = await controls.count();
    for (let i = 0; i < count; i++) {
      const control = controls.nth(i);
      const controlType = (await control.getAttribute('type')) || 'text';
      const rangeRole = await control.getAttribute('data-range-role');
      const effectiveIndex = rangeRole === 'start' ? 0 : rangeRole === 'end' ? 1 : i;
      await control.fill(valueForInput(controlType, effectiveIndex));
    }
    return;
  }

  if (type === 'score') {
    const rows = field.locator('[data-score-option]');
    const count = await rows.count();
    for (let i = 0; i < count; i++) {
      await rows.nth(i).locator('.score-pill').last().click();
    }
    return;
  }

  if (type === 'nps') {
    const preferred = field.locator('[data-score-value="9"]');
    if (await preferred.count()) await preferred.first().click();
    else await field.locator('.nps-pill').last().click();
  }
}

(async () => {
  const htmlPath = process.argv[2];
  const width = Number(process.argv[3] || 1440);
  const height = Number(process.argv[4] || 960);
  const viewportName = process.argv[5] || 'desktop';
  const url = 'file://' + path.resolve(htmlPath);
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width, height }, isMobile: viewportName === 'mobile' });
  const pageErrors = [];
  const consoleErrors = [];
  page.on('pageerror', err => pageErrors.push(String(err && err.message ? err.message : err)));
  page.on('console', msg => { if (msg.type() === 'error') consoleErrors.push(msg.text()); });
  await page.addInitScript(() => {
    localStorage.clear();
    window.__surveyPayloads = [];
    window.__surveyRedirects = [];
    window.__surveySubmitEvents = [];
    const originalLog = console.log;
    console.log = (...args) => {
      try {
        window.__surveyPayloads.push(args.map((arg) => JSON.parse(JSON.stringify(arg))));
      } catch (error) {
        window.__surveyPayloads.push(args.map(String));
      }
      originalLog(...args);
    };
    window.__surveyNavigate = () => {};
    window.alert = () => {};
  });

  let gotoError = null;
  try {
    await page.goto(url, { waitUntil: 'load', timeout: 15000 });
    await page.waitForTimeout(300);
  } catch (err) {
    gotoError = String(err && err.message ? err.message : err);
  }

  const interactions = [];
  let submitClicked = false;
  if (!gotoError) {
    for (let step = 0; step < 80; step++) {
      const state = await page.evaluate(() => {
        const active = document.querySelector('.screen.is-active');
        return active ? {
          type: active.dataset.schemaType,
          id: active.dataset.screenId,
          text: (active.innerText || '').slice(0, 80)
        } : null;
      });
      if (!state) throw new Error('No active screen during interaction test');
      interactions.push(state);

      if (state.type === 'survey') {
        await page.locator('.screen.is-active [data-next]').click();
        continue;
      }

      if (state.type === 'finish') {
        await page.locator('.screen.is-active button[type="submit"]').click();
        submitClicked = true;
        const waitAfterSubmit = await page.evaluate(() => {
          const events = Array.isArray(window.__surveySubmitEvents) ? window.__surveySubmitEvents : [];
          const action = events[events.length - 1]?.postSubmit;
          if (action?.mode === 'delay') return Math.min(Number(action.delayMs || 0) + 500, 5000);
          if (action?.mode === 'immediate') return 200;
          return 300;
        });
        await page.waitForTimeout(waitAfterSubmit);
        break;
      }

      if (state.type === 'page') {
        const fields = page.locator('.screen.is-active .field[data-schema-type]');
        const fieldCount = await fields.count();
        for (let i = 0; i < fieldCount; i++) {
          await fillQuestionField(fields.nth(i));
        }
      } else if (state.type === 'radio') {
        await fillQuestionField(page.locator('.screen.is-active'));
      } else if (state.type === 'checkbox') {
        await fillQuestionField(page.locator('.screen.is-active'));
      } else if (state.type === 'input') {
        await fillQuestionField(page.locator('.screen.is-active'));
      } else if (state.type === 'score') {
        await fillQuestionField(page.locator('.screen.is-active'));
      } else if (state.type === 'nps') {
        await fillQuestionField(page.locator('.screen.is-active'));
      }

      const next = page.locator('.screen.is-active [data-next]');
      if (await next.count()) await next.click();
      else throw new Error(`No next button after filling screen type ${state.type}`);
    }
  }

  const result = await page.evaluate(() => {
    const payloads = (window.__surveyPayloads || []).map(args => args[0]).filter(item => item && typeof item === 'object' && item.surveyId && Array.isArray(item.answers));
    const payload = payloads[payloads.length - 1] || null;
    const redirects = Array.isArray(window.__surveyRedirects) ? window.__surveyRedirects : [];
    const submitEvents = Array.isArray(window.__surveySubmitEvents) ? window.__surveySubmitEvents : [];
    const renderedQuestions = Array.from(document.querySelectorAll('.screen[data-schema-type], .field[data-schema-type]'))
      .map(node => ({ id: node.dataset.screenId, type: node.dataset.schemaType }))
      .filter(item => item.id && !['survey', 'survey-all', 'finish', 'page'].includes(item.type));
    const renderedQuestionTypes = renderedQuestions.map(item => item.type);
    const schemaQuestions = renderedQuestions.map((question) => {
      const screen = document.querySelector(`.screen[data-screen-id="${question.id}"]`) || document.querySelector(`.field[data-screen-id="${question.id}"]`);
      const parentScreen = screen?.closest('.screen[data-screen-id]');
      const optionIds = Array.from(new Set([
        ...Array.from(screen?.querySelectorAll('[data-option-id]') || []).map(node => node.dataset.optionId),
        ...Array.from(screen?.querySelectorAll('[data-score-option]') || []).map(node => node.dataset.scoreOption),
        ...Array.from(screen?.querySelectorAll('[data-nps-option]') || []).map(node => node.dataset.npsOption)
      ].filter(Boolean)));
      const childIds = Array.from(new Set(Array.from(screen?.querySelectorAll('[data-child-id]') || []).map(node => node.dataset.childId).filter(Boolean)));
      return { id: question.id, type: question.type, optionIds, childIds, parentScreenId: parentScreen?.dataset?.screenId || question.id };
    });
    const cacheKeys = [];
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key && key.startsWith('survey_step_cache_')) cacheKeys.push(key);
    }
    const submitStatus = document.querySelector('[data-submit-status]')?.innerText?.trim() || '';
    return { payload, redirects, submitEvents, submitStatus, renderedQuestions, renderedQuestionTypes, schemaQuestions, cacheKeys };
  });

  await browser.close();
  process.stdout.write(JSON.stringify({
    ok: !gotoError,
    gotoError,
    pageErrors,
    consoleErrors,
    interactions,
    submitClicked,
    viewport: { name: viewportName, width, height },
    result
  }));
})().catch(err => {
  process.stdout.write(JSON.stringify({
    ok: false,
    gotoError: String(err && err.message ? err.message : err),
    pageErrors: [],
    consoleErrors: [],
    interactions: [],
    submitClicked: false,
    viewport: { name: process.argv[5] || 'desktop', width: Number(process.argv[3] || 1440), height: Number(process.argv[4] || 960) },
    result: null
  }));
  process.exit(1);
});
"""


class Reporter:
    def __init__(self):
        self.errors = []
        self.warnings = []

    def error(self, path, message):
        self.errors.append({"path": path, "message": message})

    def warn(self, path, message):
        self.warnings.append({"path": path, "message": message})

    def result(self, extra=None):
        data = {"valid": len(self.errors) == 0, "errors": self.errors, "warnings": self.warnings}
        if extra:
            data.update(extra)
        return data


VIEWPORTS = {
    "desktop": {"width": 1440, "height": 960},
    "mobile": {"width": 390, "height": 844},
}

def run_browser_interaction_check(html_path: Path, viewport_name="desktop"):
    viewport = VIEWPORTS.get(viewport_name) or VIEWPORTS["desktop"]
    node = shutil.which("node")
    if not node:
        raise RuntimeError("Node.js is required for Playwright interaction E2E validation.")
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as tmp:
        tmp.write(NODE_RUNNER)
        tmp_path = Path(tmp.name)
    try:
        env = os.environ.copy()
        validators_node_modules = VALIDATORS_DIR / "node_modules"
        env["NODE_PATH"] = str(validators_node_modules) + (f":{env['NODE_PATH']}" if env.get("NODE_PATH") else "")
        proc = subprocess.run(
            [node, str(tmp_path), str(html_path), str(viewport["width"]), str(viewport["height"]), viewport_name],
            capture_output=True,
            text=True,
            cwd=str(VALIDATORS_DIR),
            env=env,
            timeout=60,
        )
    finally:
        tmp_path.unlink(missing_ok=True)
    stdout = proc.stdout.strip()
    if not stdout:
        raise RuntimeError(proc.stderr.strip() or "Empty Playwright interaction E2E output.")
    try:
        return json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid Playwright interaction E2E output: {exc}; raw={stdout[:400]}")


def validate_payload_against_schema_metadata(payload, schema_questions, reporter):
    question_map = {item.get("id"): item for item in schema_questions or [] if isinstance(item, dict)}
    for idx, answer in enumerate((payload or {}).get("answers") or []):
        if not isinstance(answer, dict):
            continue
        qid = answer.get("questionId")
        qtype = answer.get("questionType")
        meta = question_map.get(qid)
        if not meta:
            reporter.error(f"interaction.payload.answers[{idx}].questionId", f"Submitted questionId {qid} does not exist in schema.")
            continue
        if meta.get("type") != qtype:
            reporter.error(f"interaction.payload.answers[{idx}].questionType", f"Submitted questionType {qtype} does not match schema type {meta.get('type')}.")
        option_ids = set(meta.get("optionIds") or [])
        child_ids = set(meta.get("childIds") or [])

        def check_child(child, path):
            if isinstance(child, dict) and child.get("childId") not in child_ids:
                reporter.error(f"{path}.childId", f"Submitted childId {child.get('childId')} does not exist under schema question {qid}.")

        def check_option(option_id, path):
            if option_id not in option_ids:
                reporter.error(path, f"Submitted optionId {option_id} does not exist under schema question {qid}.")

        value = answer.get("value")
        if qtype == "radio" and isinstance(value, dict):
            check_option(value.get("optionId"), f"interaction.payload.answers[{idx}].value.optionId")
            for cidx, child in enumerate(value.get("child") or []):
                check_child(child, f"interaction.payload.answers[{idx}].value.child[{cidx}]")
        elif qtype == "checkbox" and isinstance(value, list):
            for vidx, item in enumerate(value):
                if not isinstance(item, dict):
                    continue
                check_option(item.get("optionId"), f"interaction.payload.answers[{idx}].value[{vidx}].optionId")
                for cidx, child in enumerate(item.get("child") or []):
                    check_child(child, f"interaction.payload.answers[{idx}].value[{vidx}].child[{cidx}]")
        elif qtype == "input" and isinstance(value, list):
            for vidx, item in enumerate(value):
                if isinstance(item, dict):
                    check_option(item.get("optionId"), f"interaction.payload.answers[{idx}].value[{vidx}].optionId")
        elif qtype == "score" and isinstance(value, list):
            for vidx, item in enumerate(value):
                if isinstance(item, dict):
                    check_option(item.get("optionId"), f"interaction.payload.answers[{idx}].value[{vidx}].optionId")
        elif qtype == "nps" and isinstance(value, dict):
            check_option(value.get("optionId"), f"interaction.payload.answers[{idx}].value.optionId")


def validate_single_viewport_interaction(html_path: Path, viewport_name):
    reporter = Reporter()
    try:
        raw = run_browser_interaction_check(html_path, viewport_name=viewport_name)
    except Exception as exc:
        reporter.error(f"interaction.{viewport_name}.execution", f"Interaction E2E test could not run: {exc}")
        return reporter.result({"executed": False, "supported": False, "viewport": {"name": viewport_name, **VIEWPORTS.get(viewport_name, {})}})

    prefix = f"interaction.{viewport_name}"
    if not raw.get("ok"):
        reporter.error(f"{prefix}.goto", f"Browser interaction test failed to load or run: {raw.get('gotoError')}")
    for idx, message in enumerate(raw.get("pageErrors", []), start=1):
        reporter.error(f"{prefix}.pageerror[{idx}]", f"Page runtime error: {message}")
    for idx, message in enumerate(raw.get("consoleErrors", []), start=1):
        reporter.warn(f"{prefix}.console[{idx}]", f"Console error output detected: {message}")
    if not raw.get("submitClicked"):
        reporter.error(f"{prefix}.submit", "Interaction test did not reach and click the submit button.")

    result = raw.get("result") or {}
    payload = result.get("payload")
    question_types = result.get("renderedQuestionTypes") or []
    if not payload:
        reporter.error(f"{prefix}.payload", "Submit did not produce a console payload object.")
    else:
        payload_report = validate_survey_payload(payload)
        if not payload_report.get("valid"):
            for idx, item in enumerate(payload_report.get("errors", []), start=1):
                reporter.error(f"{prefix}.payload.contract[{idx}]", f"Actual browser-submitted payload is invalid: [{item.get('path')}] {item.get('message')}")
        validate_payload_against_schema_metadata(payload, result.get("schemaQuestions") or [], reporter)
        # Prefix legacy metadata errors that are emitted without viewport context.
        for item in reporter.errors:
            if item.get("path", "").startswith("interaction.payload"):
                item["path"] = item["path"].replace("interaction.", f"{prefix}.", 1)
        answers = payload.get("answers") or []
        if not answers:
            reporter.error(f"{prefix}.payload.answers", "Submitted payload contains no answers after automated interaction.")
        answer_types = [item.get("questionType") for item in answers if isinstance(item, dict)]
        answer_ids = {item.get("questionId") for item in answers if isinstance(item, dict)}
        rendered_questions = result.get("renderedQuestions") or []
        visited_screen_ids = {item.get("id") for item in raw.get("interactions", []) if isinstance(item, dict) and item.get("id")}
        schema_question_meta = {item.get("id"): item for item in (result.get("schemaQuestions") or []) if isinstance(item, dict)}
        visited_question_types = set()
        for question in rendered_questions:
            qid = question.get("id")
            qtype = question.get("type")
            meta = schema_question_meta.get(qid, {})
            parent_screen_id = meta.get("parentScreenId") or qid
            if parent_screen_id not in visited_screen_ids:
                continue
            if qtype:
                visited_question_types.add(qtype)
            if qid not in answer_ids:
                reporter.error(f"{prefix}.payload.question.{qid}", f"Rendered question {qid} ({qtype}) did not appear in submitted payload.")
        for qtype in sorted(visited_question_types):
            if qtype not in answer_types:
                reporter.error(f"{prefix}.payload.{qtype}", f"Rendered question type {qtype} did not appear in submitted payload.")
        for item in answers:
            if not isinstance(item, dict):
                continue
            if item.get("questionType") == "score" and not isinstance(item.get("value"), list):
                reporter.error(f"{prefix}.payload.score", "Score payload value must be an array.")
            if item.get("questionType") == "nps" and not isinstance(item.get("value"), dict):
                reporter.error(f"{prefix}.payload.nps", "NPS payload value must be an object.")
    if result.get("cacheKeys"):
        reporter.error(f"{prefix}.cacheCleanup", f"Submit did not clear survey cache keys: {result.get('cacheKeys')}")

    return reporter.result({
        "executed": True,
        "supported": True,
        "viewport": raw.get("viewport") or {"name": viewport_name, **VIEWPORTS.get(viewport_name, {})},
        "interactions": raw.get("interactions", []),
        "payload": payload,
        "redirects": result.get("redirects") or [],
        "submitEvents": result.get("submitEvents") or [],
        "submitStatus": result.get("submitStatus") or "",
        "questionTypes": question_types,
        "renderedQuestions": result.get("renderedQuestions") or [],
        "schemaQuestions": result.get("schemaQuestions") or [],
        "runtime": {
            "pageErrors": raw.get("pageErrors", []),
            "consoleErrors": raw.get("consoleErrors", []),
        },
    })


def validate_html_interaction_e2e(html_path: Path, viewport="all"):
    names = list(VIEWPORTS.keys()) if viewport == "all" else [viewport]
    reporter = Reporter()
    viewport_reports = {}
    for name in names:
        report = validate_single_viewport_interaction(html_path, name)
        viewport_reports[name] = report
        for item in report.get("errors", []):
            reporter.errors.append(item)
        for item in report.get("warnings", []):
            reporter.warnings.append(item)

    first = viewport_reports.get(names[0], {}) if names else {}
    return reporter.result({
        "executed": any(r.get("executed") for r in viewport_reports.values()),
        "supported": all(r.get("supported", False) for r in viewport_reports.values()) if viewport_reports else False,
        "viewportMode": viewport,
        "viewports": viewport_reports,
        "interactions": first.get("interactions", []),
        "payload": first.get("payload"),
        "redirects": first.get("redirects", []),
        "submitEvents": first.get("submitEvents", []),
        "submitStatus": first.get("submitStatus", ""),
        "questionTypes": first.get("questionTypes", []),
        "renderedQuestions": first.get("renderedQuestions", []),
        "schemaQuestions": first.get("schemaQuestions", []),
        "runtime": first.get("runtime", {"pageErrors": [], "consoleErrors": []}),
    })

def print_human(report):
    print("✅ HTML interaction E2E test passed." if report["valid"] else "❌ HTML interaction E2E test failed.")
    if report.get("errors"):
        print("\nErrors:")
        for i, item in enumerate(report["errors"], start=1):
            print(f"{i}. [{item['path']}] {item['message']}")
    if report.get("warnings"):
        print("\nWarnings:")
        for i, item in enumerate(report["warnings"], start=1):
            print(f"{i}. [{item['path']}] {item['message']}")


def main():
    args = sys.argv[1:]
    json_output = "--json" in args
    viewport = "all"
    if "--viewport" in args:
        idx = args.index("--viewport")
        try:
            viewport = args[idx + 1]
        except IndexError:
            print("--viewport requires desktop, mobile, or all", file=sys.stderr)
            sys.exit(1)
    if viewport not in {"desktop", "mobile", "all"}:
        print("--viewport must be desktop, mobile, or all", file=sys.stderr)
        sys.exit(1)
    file_arg = next((a for i, a in enumerate(args) if not a.startswith("--") and (i == 0 or args[i-1] != "--viewport")), None)
    if not file_arg:
        print("Usage: validate_survey_html_interaction_e2e.py /absolute/path/to/file.html [--json] [--viewport desktop|mobile|all]", file=sys.stderr)
        sys.exit(1)
    html_path = Path(file_arg)
    if not html_path.exists():
        print(f"Failed to read HTML file: {html_path} does not exist", file=sys.stderr)
        sys.exit(1)
    report = validate_html_interaction_e2e(html_path, viewport=viewport)
    if json_output:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_human(report)
    sys.exit(0 if report["valid"] else 1)


if __name__ == "__main__":
    main()
