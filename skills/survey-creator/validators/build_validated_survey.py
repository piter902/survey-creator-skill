#!/usr/bin/env python3
import argparse, json, sys
from pathlib import Path

from validate_survey_schema import validate_survey_schema
from validate_survey_html_runtime import validate_html_runtime
from validate_survey_payload import validate_survey_payload
from generate_sample_payload import generate_payload
from render_survey_html import render_html_from_schema, DEFAULT_TEMPLATE, derive_output_stem
from auto_repair_survey_schema import auto_repair_schema


def load_json(path_str):
    return json.loads(Path(path_str).read_text(encoding='utf-8'))


def summarize(report):
    return {
        'valid': report.get('valid', False),
        'error_count': len(report.get('errors', [])),
        'warning_count': len(report.get('warnings', [])),
    }


def print_section(name, report):
    status = '✅ PASS' if report.get('valid') else '❌ FAIL'
    print(f'\n[{name}] {status}')
    if report.get('errors'):
        print('Errors:')
        for i, item in enumerate(report['errors'], start=1):
            print(f"  {i}. [{item['path']}] {item['message']}")
    if report.get('warnings'):
        print('Warnings:')
        for i, item in enumerate(report['warnings'], start=1):
            severity = item.get('severity', 'medium').upper()
            code = item.get('code')
            code_text = f" [{code}]" if code else ""
            print(f"  {i}. [{severity}]{code_text} [{item['path']}] {item['message']}")


def warning_counts_by_severity(warnings):
    counts = {'high': 0, 'medium': 0, 'low': 0}
    for item in warnings or []:
        severity = item.get('severity', 'medium')
        counts[severity] = counts.get(severity, 0) + 1
    return counts


def resolve_output_path(out_arg, schema, schema_path, suffix):
    out_path = Path(out_arg)
    stem = derive_output_stem(schema, schema_path)
    if out_arg.endswith('/') or out_path.is_dir():
        out_path.mkdir(parents=True, exist_ok=True)
        return out_path / f'{stem}{suffix}'
    parent = out_path.parent
    if parent and not parent.exists():
        parent.mkdir(parents=True, exist_ok=True)
    return out_path


def build_manifest(schema, html_path, payload_path, schema_path, style_pack):
    html_file = Path(html_path)
    bundle_dir = html_file.parent

    def relative(path_str):
        return f"./{Path(path_str).name}" if path_str else ""

    return {
        "surveyId": (schema.get("survey") or {}).get("id", ""),
        "title": (schema.get("survey") or {}).get("title", ""),
        "version": "1.0.0",
        "createdAt": "",
        "stylePack": style_pack,
        "paths": {
            "html": relative(str(html_path)),
            "schema": relative(str(schema_path)) if schema_path else "",
            "samplePayload": relative(str(payload_path)) if payload_path else "",
            "report": "",
        },
        "submission": {
            "contractVersion": "default-v1",
            "endpoint": "/api/survey/submit",
            "method": "POST",
        },
        "publish": {
            "provider": "",
            "mode": "",
            "surveyUrl": "",
            "schemaUrl": "",
            "htmlStorageUrl": "",
            "publishedAt": "",
            "meta": {},
        },
        "bundle": {
            "directory": str(bundle_dir),
        },
    }


def main():
    parser = argparse.ArgumentParser(description='Schema -> HTML -> payload fully automated release pipeline for survey-creator-skill.')
    parser.add_argument('--schema', required=True, help='Path to frozen schema JSON')
    parser.add_argument('--out-html', required=True, help='Output HTML path')
    parser.add_argument('--out-payload', help='Optional generated sample payload output path')
    parser.add_argument('--out-schema', help='Optional output path for the schema actually used to render HTML')
    parser.add_argument('--template', default=str(DEFAULT_TEMPLATE), help='Optional HTML template path')
    parser.add_argument('--style-pack', default='consumer-minimal', help='Optional UI style pack name')
    parser.add_argument('--auto-repair', action='store_true', help='Attempt safe semantic auto-repairs before rendering')
    parser.add_argument('--fail-on-high-warning', action='store_true', help='Fail the build if schema still has high severity warnings after optional auto-repair')
    parser.add_argument('--json', action='store_true', help='Print machine-readable JSON report')
    args = parser.parse_args()

    full_report = {'valid': True, 'schema': None, 'html': None, 'payload': None, 'repair': None, 'summary': {}, 'output': {'html': args.out_html, 'payload': args.out_payload, 'schema': args.out_schema}}

    try:
        schema = load_json(args.schema)
    except FileNotFoundError as e:
        print(f'Failed to read schema input: {e}', file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f'Invalid JSON: {e}', file=sys.stderr)
        sys.exit(1)

    if args.auto_repair:
        repair_report = auto_repair_schema(schema)
        full_report['repair'] = {k: v for k, v in repair_report.items() if k != 'schema'}
        schema = repair_report['schema']

    out_html_path = resolve_output_path(args.out_html, schema, args.schema, '.html')
    out_payload_path = resolve_output_path(args.out_payload, schema, args.schema, '.payload.json') if args.out_payload else None
    out_schema_path = resolve_output_path(args.out_schema, schema, args.schema, '.repaired.schema.json') if args.out_schema else None
    manifest_path = out_html_path.parent / 'survey.manifest.json'
    full_report['output'] = {
        'html': str(out_html_path),
        'payload': str(out_payload_path) if out_payload_path else None,
        'schema': str(out_schema_path) if out_schema_path else None,
        'manifest': str(manifest_path),
    }

    schema_report = validate_survey_schema(schema)
    full_report['schema'] = schema_report
    full_report['summary']['schema'] = summarize(schema_report)
    full_report['summary']['schema']['warning_severity'] = warning_counts_by_severity(schema_report.get('warnings', []))
    full_report['valid'] = full_report['valid'] and schema_report.get('valid', False)

    if out_schema_path:
        out_schema_path.write_text(json.dumps(schema, ensure_ascii=False, indent=2), encoding='utf-8')

    block_on_warning = args.fail_on_high_warning and warning_counts_by_severity(schema_report.get('warnings', [])).get('high', 0) > 0
    if block_on_warning:
        full_report['valid'] = False

    if schema_report.get('valid') and not block_on_warning:
        template_text = Path(args.template).read_text(encoding='utf-8')
        html = render_html_from_schema(schema, template_text, style_pack=args.style_pack)
        out_html_path.write_text(html, encoding='utf-8')
        html_report = validate_html_runtime(html)
        full_report['html'] = html_report
        full_report['summary']['html'] = summarize(html_report)
        full_report['valid'] = full_report['valid'] and html_report.get('valid', False)

        payload = generate_payload(schema)
        if out_payload_path:
            out_payload_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
        payload_report = validate_survey_payload(payload)
        payload_report['generated'] = True
        if out_payload_path:
        payload_report['outputPath'] = str(out_payload_path)
        full_report['payload'] = payload_report
        full_report['summary']['payload'] = summarize(payload_report)
        full_report['valid'] = full_report['valid'] and payload_report.get('valid', False)

    manifest = build_manifest(schema, out_html_path, out_payload_path, out_schema_path, args.style_pack)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')

    if args.json:
        print(json.dumps(full_report, ensure_ascii=False, indent=2))
    else:
        print('✅ BUILD PIPELINE PASS' if full_report['valid'] else '❌ BUILD PIPELINE FAIL')
        if full_report['schema'] is not None:
            print_section('SCHEMA', full_report['schema'])
        if full_report['repair'] is not None:
            print('\n[REPAIR]')
            print(f"Stopped reason: {full_report['repair'].get('stoppedReason')}")
            print(f"Applied fixes: {len(full_report['repair'].get('appliedFixes', []))}")
        if full_report['html'] is not None:
            print_section('HTML', full_report['html'])
        if full_report['payload'] is not None:
            print_section('PAYLOAD', full_report['payload'])
        print('\nOutput:')
        print(f'- html: {out_html_path}')
        if out_payload_path:
            print(f'- payload: {out_payload_path}')
        if out_schema_path:
            print(f'- schema: {out_schema_path}')
        print(f'- manifest: {manifest_path}')
        print('\nSummary:')
        for key, value in full_report['summary'].items():
            print(f"- {key}: valid={value['valid']}, errors={value['error_count']}, warnings={value['warning_count']}")

    sys.exit(0 if full_report['valid'] else 1)


if __name__ == '__main__':
    main()
