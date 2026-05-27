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

(async () => {
  const htmlPath = process.argv[2];
  const url = 'file://' + path.resolve(htmlPath);
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 960 } });
  const pageErrors = [];
  page.on('pageerror', err => pageErrors.push(String(err && err.message ? err.message : err)));
  await page.goto(url, { waitUntil: 'load', timeout: 15000 });
  await page.waitForTimeout(500);

  const result = await page.evaluate(() => {
    const root = document.body.cloneNode(true);
    root.querySelectorAll('script,style,noscript,template').forEach(node => node.remove());
    const domText = (root.textContent || '').replace(/\s+/g, ' ').trim();
    const html = document.documentElement.outerHTML;
    return {
      domText,
      html,
      hasPreviewPayloadBtn: !!document.getElementById('previewPayloadBtn'),
      coverageCount: document.querySelectorAll('.coverage').length,
    };
  });

  await browser.close();
  process.stdout.write(JSON.stringify({ ok: true, pageErrors, ...result }));
})().catch(err => {
  process.stdout.write(JSON.stringify({ ok: false, pageErrors: [], domText: '', html: '', hasPreviewPayloadBtn: false, coverageCount: 0, errors: [{ path: 'userVisible.execution', message: String(err && err.message ? err.message : err) }] }));
  process.exit(1);
});
"""

BANNED_VISIBLE_TOKENS = [
    'survey.attribute',
    'onePageOneQuestion',
    'allowBack',
    'required=true',
    'required=false',
    'random=true',
    'random=false',
    'score.attribute',
    'nps.attribute',
    'child.attribute',
    'input.option.attribute',
    'preview payload',
    '预览 payload',
    'payload 已输出到 console',
    'schema 已输出到 console',
    'schema:',
    'payload:',
]

BANNED_HTML_SNIPPETS = [
    'id="previewPayloadBtn"',
    "id='previewPayloadBtn'",
    'class="coverage"',
    "class='coverage'",
]

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


def run_browser_probe(html_path: Path):
    node = shutil.which('node')
    if not node:
        raise RuntimeError('Node.js is required for user-visible content validation.')
    with tempfile.NamedTemporaryFile('w', suffix='.js', delete=False, encoding='utf-8') as tmp:
        tmp.write(NODE_RUNNER)
        tmp_path = Path(tmp.name)
    try:
        env = os.environ.copy()
        validators_node_modules = VALIDATORS_DIR / 'node_modules'
        env['NODE_PATH'] = str(validators_node_modules) + (f":{env['NODE_PATH']}" if env.get('NODE_PATH') else '')
        proc = subprocess.run(
            [node, str(tmp_path), str(html_path)],
            capture_output=True,
            text=True,
            env=env,
            timeout=30,
        )
    finally:
        tmp_path.unlink(missing_ok=True)
    if not proc.stdout.strip():
        raise RuntimeError(proc.stderr.strip() or 'User-visible content browser probe produced no output.')
    return json.loads(proc.stdout)


def validate_user_visible_content(html_path: Path):
    reporter = Reporter()
    payload = run_browser_probe(html_path)
    if not payload.get('ok'):
        for item in payload.get('errors', []):
            reporter.error(item.get('path', 'userVisible.execution'), item.get('message', 'Unknown execution failure.'))
        return reporter.result({"metrics": {}})

    dom_text = (payload.get('domText') or '').lower()
    html = payload.get('html') or ''

    for token in BANNED_VISIBLE_TOKENS:
        if token.lower() in dom_text:
            reporter.error(f'userVisible.text.{token}', f'User-visible DOM text must not contain internal token: {token}')

    for snippet in BANNED_HTML_SNIPPETS:
        if snippet in html:
            reporter.error(f'userVisible.dom.{snippet}', f'HTML DOM must not contain debug/internal snippet: {snippet}')

    if payload.get('hasPreviewPayloadBtn'):
        reporter.error('userVisible.previewPayloadBtn', 'User-facing page must not expose previewPayloadBtn.')
    if payload.get('coverageCount', 0):
        reporter.error('userVisible.coverage', 'User-facing page must not render .coverage debug nodes.')
    for item in payload.get('pageErrors', []):
        reporter.error('userVisible.pageerror', f'Browser runtime error during user-visible content validation: {item}')

    return reporter.result({
        'metrics': {
            'domTextLength': len(dom_text),
            'coverageCount': payload.get('coverageCount', 0),
            'hasPreviewPayloadBtn': payload.get('hasPreviewPayloadBtn', False),
            'pageErrorCount': len(payload.get('pageErrors', [])),
        }
    })


def main():
    args = sys.argv[1:]
    json_output = '--json' in args
    file_arg = next((a for a in args if not a.startswith('--')), None)
    if not file_arg:
        print('Usage: validate_user_visible_content.py /absolute/path/to/file.html [--json]', file=sys.stderr)
        sys.exit(1)
    report = validate_user_visible_content(Path(file_arg))
    if json_output:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print('✅ USER-VISIBLE CONTENT CHECK PASS' if report['valid'] else '❌ USER-VISIBLE CONTENT CHECK FAIL')
        if report['errors']:
            print('\nErrors:')
            for i, item in enumerate(report['errors'], start=1):
                print(f"{i}. [{item['path']}] {item['message']}")
        if report['warnings']:
            print('\nWarnings:')
            for i, item in enumerate(report['warnings'], start=1):
                print(f"{i}. [{item['path']}] {item['message']}")
    sys.exit(0 if report['valid'] else 1)


if __name__ == '__main__':
    main()
