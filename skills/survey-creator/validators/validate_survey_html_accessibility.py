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
const path = require('path');
const { chromium } = require('playwright');

function textOf(node) {
  return (node?.innerText || node?.textContent || '').replace(/\s+/g, ' ').trim();
}

function hasAccessibleName(el) {
  const aria = el.getAttribute('aria-label') || '';
  if (aria.trim()) return true;
  const labelledBy = el.getAttribute('aria-labelledby') || '';
  if (labelledBy.trim()) {
    const text = labelledBy.split(/\s+/).map(id => textOf(document.getElementById(id))).join(' ').trim();
    if (text) return true;
  }
  const title = el.getAttribute('title') || '';
  if (title.trim()) return true;
  const label = el.closest('label');
  if (label && textOf(label)) return true;
  const id = el.getAttribute('id');
  if (id) {
    const explicit = document.querySelector(`label[for="${CSS.escape(id)}"]`);
    if (explicit && textOf(explicit)) return true;
  }
  const field = el.closest('.field');
  if (field && textOf(field.querySelector('.field-label'))) return true;
  return false;
}

function isVisible(el) {
  const style = window.getComputedStyle(el);
  const rect = el.getBoundingClientRect();
  return style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 0 && rect.height > 0;
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
  page.on('pageerror', err => pageErrors.push(String(err && err.message ? err.message : err)));
  await page.goto(url, { waitUntil: 'load', timeout: 15000 });
  await page.waitForTimeout(500);

  const result = await page.evaluate(() => {
    function textOf(node) {
      return (node?.innerText || node?.textContent || '').replace(/\s+/g, ' ').trim();
    }
    function hasAccessibleName(el) {
      const aria = el.getAttribute('aria-label') || '';
      if (aria.trim()) return true;
      const labelledBy = el.getAttribute('aria-labelledby') || '';
      if (labelledBy.trim()) {
        const text = labelledBy.split(/\s+/).map(id => textOf(document.getElementById(id))).join(' ').trim();
        if (text) return true;
      }
      const title = el.getAttribute('title') || '';
      if (title.trim()) return true;
      const label = el.closest('label');
      if (label && textOf(label)) return true;
      const id = el.getAttribute('id');
      if (id) {
        const explicit = document.querySelector(`label[for="${CSS.escape(id)}"]`);
        if (explicit && textOf(explicit)) return true;
      }
      const field = el.closest('.field');
      if (field && textOf(field.querySelector('.field-label'))) return true;
      return false;
    }
    function isVisible(el) {
      const style = window.getComputedStyle(el);
      const rect = el.getBoundingClientRect();
      return style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 0 && rect.height > 0;
    }
    const errors = [];
    const warnings = [];
    const html = document.documentElement;
    if (!html.getAttribute('lang')) errors.push({ path: 'a11y.document.lang', message: 'Document <html> must include lang.' });
    if (!document.title || !document.title.trim()) errors.push({ path: 'a11y.document.title', message: 'Document must include a non-empty title.' });

    const form = document.getElementById('surveyForm');
    if (!form) errors.push({ path: 'a11y.form', message: 'Survey form #surveyForm is missing.' });

    document.querySelectorAll('button').forEach((button, index) => {
      if (!textOf(button) && !(button.getAttribute('aria-label') || '').trim()) {
        errors.push({ path: `a11y.button[${index}]`, message: 'Button must have a visible or aria label.' });
      }
      if (button.disabled) return;
      const rect = button.getBoundingClientRect();
      if (isVisible(button) && (rect.width < 24 || rect.height < 24)) {
        warnings.push({ path: `a11y.button[${index}]`, message: `Button target is smaller than 24px (${Math.round(rect.width)}x${Math.round(rect.height)}).`, severity: 'medium' });
      }
    });

    document.querySelectorAll('input, textarea, select').forEach((control, index) => {
      const type = (control.getAttribute('type') || '').toLowerCase();
      if (type === 'hidden') return;
      if (!hasAccessibleName(control)) {
        errors.push({ path: `a11y.control[${index}]`, message: `${control.tagName.toLowerCase()} control must have an accessible name.` });
      }
    });

    document.querySelectorAll('img').forEach((img, index) => {
      if (!img.hasAttribute('alt')) errors.push({ path: `a11y.img[${index}]`, message: 'Image must include alt text, even when decorative.' });
      else if ((img.getAttribute('alt') || '').trim().toLowerCase() === 'media') warnings.push({ path: `a11y.img[${index}]`, message: 'Image alt text is generic; consider scenario-specific alt text when media is meaningful.', severity: 'low' });
    });

    document.querySelectorAll('audio, video').forEach((media, index) => {
      if (!media.hasAttribute('controls')) errors.push({ path: `a11y.media[${index}]`, message: `${media.tagName.toLowerCase()} media must expose controls.` });
    });

    document.querySelectorAll('.error').forEach((error, index) => {
      if (!error.getAttribute('role') && !error.getAttribute('aria-live')) {
        warnings.push({ path: `a11y.error[${index}]`, message: 'Validation error message should use role="alert" or aria-live.', severity: 'medium' });
      }
    });

    document.querySelectorAll('.score-pill').forEach((button, index) => {
      if (!button.hasAttribute('aria-pressed')) {
        errors.push({ path: `a11y.scorePill[${index}]`, message: 'Score/NPS toggle buttons must expose aria-pressed state.' });
      }
    });

    const activeScreens = Array.from(document.querySelectorAll('.screen.is-active'));
    if (!activeScreens.length) errors.push({ path: 'a11y.activeScreen', message: 'There must be an active screen for keyboard and screen-reader flow.' });

    return {
      errors,
      warnings,
      metrics: {
        controlCount: document.querySelectorAll('input, textarea, select').length,
        buttonCount: document.querySelectorAll('button').length,
        imageCount: document.querySelectorAll('img').length,
        errorCount: document.querySelectorAll('.error').length,
        scorePillCount: document.querySelectorAll('.score-pill').length,
      }
    };
  });

  await browser.close();
  process.stdout.write(JSON.stringify({ ok: true, viewport: { name: viewportName, width, height }, pageErrors, ...result }));
})().catch(err => {
  process.stdout.write(JSON.stringify({ ok: false, viewport: { name: process.argv[5] || 'desktop', width: Number(process.argv[3] || 1440), height: Number(process.argv[4] || 960) }, pageErrors: [], errors: [{ path: 'a11y.execution', message: String(err && err.message ? err.message : err) }], warnings: [], metrics: {} }));
  process.exit(1);
});
"""

VIEWPORTS = {
    "desktop": {"width": 1440, "height": 960},
    "mobile": {"width": 390, "height": 844},
}


class Reporter:
    def __init__(self):
        self.errors = []
        self.warnings = []

    def error(self, path, message):
        self.errors.append({"path": path, "message": message})

    def warn(self, path, message, severity="medium"):
        self.warnings.append({"path": path, "message": message, "severity": severity})

    def result(self, extra=None):
        data = {"valid": len(self.errors) == 0, "errors": self.errors, "warnings": self.warnings}
        if extra:
            data.update(extra)
        return data


def run_browser_accessibility_check(html_path: Path, viewport_name="desktop"):
    node = shutil.which("node")
    if not node:
        raise RuntimeError("Node.js is required for accessibility validation.")
    viewport = VIEWPORTS.get(viewport_name) or VIEWPORTS["desktop"]
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
        raise RuntimeError(proc.stderr.strip() or "Empty accessibility validator output.")
    try:
        return json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid accessibility validator output: {exc}; raw={stdout[:400]}")


def validate_single_viewport_accessibility(html_path: Path, viewport_name):
    reporter = Reporter()
    try:
        raw = run_browser_accessibility_check(html_path, viewport_name=viewport_name)
    except Exception as exc:
        reporter.error(f"a11y.{viewport_name}.execution", f"Accessibility check could not run: {exc}")
        return reporter.result({"executed": False, "supported": False, "viewport": {"name": viewport_name, **VIEWPORTS.get(viewport_name, {})}})

    if not raw.get("ok"):
        reporter.error(f"a11y.{viewport_name}.load", "Accessibility browser check failed to load or execute.")
    for item in raw.get("errors", []):
        reporter.error(f"a11y.{viewport_name}.{item.get('path', 'unknown')}", item.get("message", "Accessibility error."))
    for item in raw.get("warnings", []):
        reporter.warn(f"a11y.{viewport_name}.{item.get('path', 'unknown')}", item.get("message", "Accessibility warning."), item.get("severity", "medium"))
    for idx, message in enumerate(raw.get("pageErrors", []), start=1):
        reporter.error(f"a11y.{viewport_name}.pageerror[{idx}]", f"Page runtime error: {message}")

    return reporter.result({
        "executed": True,
        "supported": True,
        "viewport": raw.get("viewport") or {"name": viewport_name, **VIEWPORTS.get(viewport_name, {})},
        "metrics": raw.get("metrics", {}),
    })


def validate_html_accessibility(html_path: Path, viewport="all"):
    names = list(VIEWPORTS.keys()) if viewport == "all" else [viewport]
    reporter = Reporter()
    viewport_reports = {}
    for name in names:
        report = validate_single_viewport_accessibility(html_path, name)
        viewport_reports[name] = report
        reporter.errors.extend(report.get("errors", []))
        reporter.warnings.extend(report.get("warnings", []))
    first = viewport_reports.get(names[0], {}) if names else {}
    return reporter.result({
        "executed": any(r.get("executed") for r in viewport_reports.values()),
        "supported": all(r.get("supported", False) for r in viewport_reports.values()) if viewport_reports else False,
        "viewportMode": viewport,
        "viewports": viewport_reports,
        "metrics": first.get("metrics", {}),
    })


def print_human(report):
    print("✅ HTML accessibility check passed." if report["valid"] else "❌ HTML accessibility check failed.")
    if report.get("errors"):
        print("\nErrors:")
        for i, item in enumerate(report["errors"], start=1):
            print(f"{i}. [{item['path']}] {item['message']}")
    if report.get("warnings"):
        print("\nWarnings:")
        for i, item in enumerate(report["warnings"], start=1):
            severity = item.get("severity", "medium").upper()
            print(f"{i}. [{severity}] [{item['path']}] {item['message']}")


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
        print("Usage: validate_survey_html_accessibility.py /absolute/path/to/file.html [--json] [--viewport desktop|mobile|all]", file=sys.stderr)
        sys.exit(1)
    html_path = Path(file_arg)
    if not html_path.exists():
        print(f"Failed to read HTML file: {html_path} does not exist", file=sys.stderr)
        sys.exit(1)
    report = validate_html_accessibility(html_path, viewport=viewport)
    if json_output:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_human(report)
    sys.exit(0 if report["valid"] else 1)


if __name__ == "__main__":
    main()
