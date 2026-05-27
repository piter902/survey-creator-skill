#!/usr/bin/env python3
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile

from render_survey_html import render_html_from_schema, DEFAULT_TEMPLATE
from validate_survey_html_runtime import validate_html_runtime, extract_survey_schema_literal
from validate_survey_html_e2e import validate_html_e2e


KNOWN_REPLACEMENTS = [
    (
        r"/^(https?:|mailto:|tel:|#|\\\\/)/i",
        r"/^(https?:|mailto:|tel:|#|\\/)/i",
        "fixed-malformed-safe-href-regex",
    ),
]


def run_js_syntax_check(html):
    node = shutil.which("node")
    if not node:
        return {"supported": False, "valid": False, "error": "Node.js is not installed."}
    start = html.find("<script>")
    end = html.rfind("</script>")
    if start == -1 or end == -1 or end <= start:
        return {"supported": True, "valid": False, "error": "HTML does not contain an inline <script> block."}
    script = html[start + len("<script>"):end]
    with NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as tmp:
        tmp.write(script)
        tmp_path = Path(tmp.name)
    try:
        proc = subprocess.run([node, "--check", str(tmp_path)], capture_output=True, text=True, timeout=20)
    finally:
        tmp_path.unlink(missing_ok=True)
    return {
        "supported": True,
        "valid": proc.returncode == 0,
        "error": (proc.stderr or proc.stdout).strip() if proc.returncode != 0 else None,
    }


def validate_html_bundle(html):
    syntax_report = run_js_syntax_check(html)
    with NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as tmp:
        tmp.write(html)
        tmp_path = Path(tmp.name)
    try:
        runtime_report = validate_html_runtime(html)
        e2e_report = validate_html_e2e(tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)
    return {
        "syntax": syntax_report,
        "runtime": runtime_report,
        "e2e": e2e_report,
        "valid": syntax_report.get("valid", False) and runtime_report.get("valid", False) and e2e_report.get("valid", False),
    }


def extract_style_block(html):
    match = re.search(r"<style>([\s\S]*?)</style>", html, re.I)
    return match.group(0) if match else None


def extract_topbar_block(html):
    match = re.search(r'<div class="topbar">[\s\S]*?</div>\s*<form id="surveyForm"', html)
    if not match:
        return None
    raw = match.group(0)
    return raw[:-len('<form id="surveyForm"')].rstrip()


def merge_template_with_current_shell(current_html, base_template_text):
    result = base_template_text
    style_block = extract_style_block(current_html)
    if style_block:
        result = re.sub(r"<style>[\s\S]*?</style>", style_block, result, count=1)
    topbar_block = extract_topbar_block(current_html)
    if topbar_block:
        result = re.sub(r'<div class="topbar">[\s\S]*?</div>\s*<form id="surveyForm"', topbar_block + "\n\n    <form id=\"surveyForm\"", result, count=1)
    title_match = re.search(r"<title>([\s\S]*?)</title>", current_html, re.I)
    if title_match:
        result = re.sub(r"<title>[\s\S]*?</title>", title_match.group(0), result, count=1)
    return result


def auto_repair_html(html, style_pack='consumer-minimal'):
    initial = validate_html_bundle(html)
    if initial["valid"]:
        return {
            "changed": False,
            "html": html,
            "initialValidation": initial,
            "finalValidation": initial,
            "appliedFixes": [],
            "stoppedReason": "html-already-valid",
        }

    working = html
    applied = []

    for old, new, action in KNOWN_REPLACEMENTS:
        if old in working:
            working = working.replace(old, new)
            applied.append({"action": action, "type": "string-replacement"})

    after_known = validate_html_bundle(working)
    if after_known["valid"]:
        return {
            "changed": True,
            "html": working,
            "initialValidation": initial,
            "finalValidation": after_known,
            "appliedFixes": applied,
            "stoppedReason": "fixed-by-known-replacements",
        }

    schema_literal = extract_survey_schema_literal(working)
    if schema_literal:
        try:
            schema = json.loads(schema_literal)
            base_template_text = DEFAULT_TEMPLATE.read_text(encoding="utf-8")
            merged_template = merge_template_with_current_shell(working, base_template_text)
            rerendered = render_html_from_schema(schema, merged_template, style_pack=style_pack)
            applied.append({"action": "rerendered-from-extracted-schema", "type": "template-rerender"})
            after_rerender = validate_html_bundle(rerendered)
            if after_rerender["valid"]:
                return {
                    "changed": True,
                    "html": rerendered,
                    "initialValidation": initial,
                    "finalValidation": after_rerender,
                    "appliedFixes": applied,
                    "stoppedReason": "fixed-by-rerender",
                }
            return {
                "changed": bool(applied),
                "html": rerendered,
                "initialValidation": initial,
                "finalValidation": after_rerender,
                "appliedFixes": applied,
                "stoppedReason": "rerender-did-not-fully-fix",
            }
        except Exception as exc:
            applied.append({"action": "rerender-from-schema-failed", "type": "template-rerender", "detail": str(exc)})

    final_validation = validate_html_bundle(working)
    return {
        "changed": bool(applied),
        "html": working,
        "initialValidation": initial,
        "finalValidation": final_validation,
        "appliedFixes": applied,
        "stoppedReason": "no-safe-html-fix-left",
    }


def print_human(report, out_path=None):
    print("✅ HTML AUTO REPAIR COMPLETE" if report["finalValidation"].get("valid") else "❌ HTML AUTO REPAIR INCOMPLETE")
    print(f"Stopped reason: {report['stoppedReason']}")
    print(f"Applied fixes: {len(report.get('appliedFixes', []))}")
    for idx, item in enumerate(report.get("appliedFixes", []), start=1):
        print(f"  {idx}. [{item.get('type')}] {item.get('action')}")
    if out_path:
        print(f"Output HTML: {out_path}")


def main():
    args = sys.argv[1:]
    json_output = "--json" in args
    file_arg = next((a for a in args if not a.startswith("--")), None)
    out_path = None
    if "--out" in args:
        out_idx = args.index("--out")
        if out_idx + 1 < len(args):
            out_path = args[out_idx + 1]
    style_pack = "consumer-minimal"
    if "--style-pack" in args:
        style_idx = args.index("--style-pack")
        if style_idx + 1 < len(args):
            style_pack = args[style_idx + 1]
    if not file_arg:
        print("Usage: auto_repair_survey_html.py /absolute/path/to/file.html [--out /path/to/output.html] [--json]", file=sys.stderr)
        sys.exit(1)
    html_path = Path(file_arg)
    if not html_path.exists():
        print(f"Failed to read HTML file: {html_path} does not exist", file=sys.stderr)
        sys.exit(1)

    html = html_path.read_text(encoding="utf-8")
    report = auto_repair_html(html, style_pack=style_pack)
    if out_path:
        Path(out_path).write_text(report["html"], encoding="utf-8")

    payload = {k: v for k, v in report.items() if k != "html"}
    payload["outputPath"] = out_path
    if json_output:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print_human(report, out_path=out_path)

    sys.exit(0 if report["finalValidation"].get("valid") else 1)


if __name__ == "__main__":
    main()
