#!/usr/bin/env python3
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

VALIDATORS_DIR = Path(__file__).resolve().parent


NODE_RUNNER = r"""
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

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
  page.on('console', msg => {
    if (msg.type() === 'error') consoleErrors.push(msg.text());
  });

  let gotoError = null;
  try {
    await page.goto(url, { waitUntil: 'load', timeout: 15000 });
    await page.waitForTimeout(600);
  } catch (err) {
    gotoError = String(err && err.message ? err.message : err);
  }

  let metrics = null;
  if (!gotoError) {
    metrics = await page.evaluate(() => {
      const form = document.getElementById('surveyForm');
      const screens = Array.from(document.querySelectorAll('.screen'));
      const activeScreens = screens.filter(node => node.classList.contains('is-active'));
      return {
        title: document.title || '',
        bodyTextLength: (document.body?.innerText || '').trim().length,
        formExists: !!form,
        formChildCount: form ? form.children.length : 0,
        screenCount: screens.length,
        activeScreenCount: activeScreens.length,
        rootHtmlLength: document.documentElement?.outerHTML?.length || 0
      };
    });
  }

  await browser.close();
  process.stdout.write(JSON.stringify({
    ok: !gotoError,
    gotoError,
    pageErrors,
    consoleErrors,
    viewport: { name: viewportName, width, height },
    metrics
  }));
})().catch(err => {
  process.stdout.write(JSON.stringify({
    ok: false,
    gotoError: String(err && err.message ? err.message : err),
    pageErrors: [],
    consoleErrors: [],
    viewport: { name: process.argv[5] || 'desktop', width: Number(process.argv[3] || 1440), height: Number(process.argv[4] || 960) },
    metrics: null
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

def run_browser_check(html_path: Path, viewport_name="desktop"):
    viewport = VIEWPORTS.get(viewport_name) or VIEWPORTS["desktop"]
    node = shutil.which("node")
    if not node:
        raise RuntimeError("Node.js is required for Playwright E2E validation.")

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
            timeout=40,
        )
    finally:
        tmp_path.unlink(missing_ok=True)

    stdout = proc.stdout.strip()
    if not stdout:
        raise RuntimeError(proc.stderr.strip() or "Empty Playwright E2E output.")
    try:
        return json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid Playwright E2E output: {exc}; raw={stdout[:400]}")


def validate_single_viewport(html_path: Path, viewport_name):
    reporter = Reporter()

    try:
        raw = run_browser_check(html_path, viewport_name=viewport_name)
    except Exception as exc:
        reporter.error(f"e2e.{viewport_name}.execution", f"E2E smoke test could not run: {exc}")
        return reporter.result({"executed": False, "supported": False, "viewport": {"name": viewport_name, **VIEWPORTS.get(viewport_name, {})}})

    if not raw.get("ok"):
        reporter.error(f"e2e.{viewport_name}.goto", f"Browser could not load HTML successfully: {raw.get('gotoError')}")

    for idx, message in enumerate(raw.get("pageErrors", []), start=1):
        reporter.error(f"e2e.{viewport_name}.pageerror[{idx}]", f"Page runtime error: {message}")

    for idx, message in enumerate(raw.get("consoleErrors", []), start=1):
        reporter.warn(f"e2e.{viewport_name}.console[{idx}]", f"Console error output detected: {message}")

    metrics = raw.get("metrics") or {}
    if raw.get("ok"):
        if not metrics.get("formExists"):
            reporter.error(f"e2e.{viewport_name}.dom.form", "Rendered page does not contain #surveyForm.")
        if int(metrics.get("formChildCount", 0)) <= 0:
            reporter.error(f"e2e.{viewport_name}.dom.formChildren", "Rendered form has no child nodes; page may be blank.")
        if int(metrics.get("screenCount", 0)) <= 0:
            reporter.error(f"e2e.{viewport_name}.dom.screens", "Rendered page contains no .screen nodes; survey did not mount.")
        if int(metrics.get("activeScreenCount", 0)) <= 0:
            reporter.error(f"e2e.{viewport_name}.dom.activeScreen", "Rendered page contains no active screen.")
        if int(metrics.get("bodyTextLength", 0)) <= 0:
            reporter.error(f"e2e.{viewport_name}.dom.bodyText", "Rendered page body text is empty; page appears blank.")
        if int(metrics.get("rootHtmlLength", 0)) < 300:
            reporter.warn(f"e2e.{viewport_name}.dom.shortHtml", "Rendered document HTML is unusually short.")

    return reporter.result({
        "executed": True,
        "supported": True,
        "viewport": raw.get("viewport") or {"name": viewport_name, **VIEWPORTS.get(viewport_name, {})},
        "metrics": metrics,
        "runtime": {
            "pageErrors": raw.get("pageErrors", []),
            "consoleErrors": raw.get("consoleErrors", []),
        },
    })


def validate_html_e2e(html_path: Path, viewport="all"):
    names = list(VIEWPORTS.keys()) if viewport == "all" else [viewport]
    reporter = Reporter()
    viewport_reports = {}
    for name in names:
        report = validate_single_viewport(html_path, name)
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
        "metrics": first.get("metrics", {}),
        "runtime": first.get("runtime", {"pageErrors": [], "consoleErrors": []}),
    })


def print_human(report):
    print("✅ HTML E2E smoke test passed." if report["valid"] else "❌ HTML E2E smoke test failed.")
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
        print("Usage: validate_survey_html_e2e.py /absolute/path/to/file.html [--json] [--viewport desktop|mobile|all]", file=sys.stderr)
        sys.exit(1)
    html_path = Path(file_arg)
    if not html_path.exists():
        print(f"Failed to read HTML file: {html_path} does not exist", file=sys.stderr)
        sys.exit(1)
    report = validate_html_e2e(html_path, viewport=viewport)
    if json_output:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_human(report)
    sys.exit(0 if report["valid"] else 1)


if __name__ == "__main__":
    main()
