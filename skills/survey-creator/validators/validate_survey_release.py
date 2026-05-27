#!/usr/bin/env python3
import argparse, json, sys
from pathlib import Path

from validate_survey_schema import validate_survey_schema
from validate_survey_payload import validate_survey_payload
from validate_payload_against_schema import validate_payload_against_schema
from validate_survey_html_runtime import validate_html_runtime
from validate_survey_html_accessibility import validate_html_accessibility
from validate_user_visible_content import validate_user_visible_content
from generate_sample_payload import generate_payload
from auto_repair_survey_schema import auto_repair_schema


def load_json(path_str):
    return json.loads(Path(path_str).read_text(encoding='utf-8'))


def load_text(path_str):
    return Path(path_str).read_text(encoding='utf-8')


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


def main():
    parser = argparse.ArgumentParser(description='Unified pre-release validator for survey-creator-skill outputs.')
    parser.add_argument('--schema', help='Path to schema JSON')
    parser.add_argument('--html', help='Path to generated HTML file')
    parser.add_argument('--payload', help='Path to payload JSON')
    parser.add_argument('--generate-sample-payload', action='store_true', help='Generate a payload sample from schema when --payload is not provided')
    parser.add_argument('--write-sample-payload', help='Optional output path for generated sample payload JSON')
    parser.add_argument('--auto-repair', action='store_true', help='Attempt safe semantic auto-repairs before evaluating schema-derived artifacts')
    parser.add_argument('--fail-on-high-warning', action='store_true', help='Mark validation failed when schema still has high warnings')
    parser.add_argument('--json', action='store_true', help='Print machine-readable JSON report')
    args = parser.parse_args()

    if not any([args.schema, args.html, args.payload]):
        parser.error('At least one of --schema, --html, or --payload is required.')
    if args.generate_sample_payload and not args.schema:
        parser.error('--generate-sample-payload requires --schema.')

    full_report = {'valid': True, 'schema': None, 'html': None, 'htmlAccessibility': None, 'userVisible': None, 'payload': None, 'payloadAgainstSchema': None, 'repair': None, 'summary': {}}

    try:
        schema_data = load_json(args.schema) if args.schema else None
        if args.schema:
            if args.auto_repair:
                repair_report = auto_repair_schema(schema_data)
                full_report['repair'] = {k: v for k, v in repair_report.items() if k != 'schema'}
                schema_data = repair_report['schema']
            schema_report = validate_survey_schema(schema_data)
            full_report['schema'] = schema_report
            full_report['summary']['schema'] = summarize(schema_report)
            full_report['summary']['schema']['warning_severity'] = warning_counts_by_severity(schema_report.get('warnings', []))
            full_report['valid'] = full_report['valid'] and schema_report.get('valid', False)
            if args.fail_on_high_warning and warning_counts_by_severity(schema_report.get('warnings', [])).get('high', 0) > 0:
                full_report['valid'] = False
        if args.html:
            html_report = validate_html_runtime(load_text(args.html))
            full_report['html'] = html_report
            full_report['summary']['html'] = summarize(html_report)
            full_report['valid'] = full_report['valid'] and html_report.get('valid', False)
            accessibility_report = validate_html_accessibility(Path(args.html))
            full_report['htmlAccessibility'] = accessibility_report
            full_report['summary']['htmlAccessibility'] = summarize(accessibility_report)
            full_report['valid'] = full_report['valid'] and accessibility_report.get('valid', False)
            user_visible_report = validate_user_visible_content(Path(args.html))
            full_report['userVisible'] = user_visible_report
            full_report['summary']['userVisible'] = summarize(user_visible_report)
            full_report['valid'] = full_report['valid'] and user_visible_report.get('valid', False)
        generated_payload = None
        if args.payload:
            generated_payload = load_json(args.payload)
        elif args.generate_sample_payload and schema_data is not None:
            generated_payload = generate_payload(schema_data)
            if args.write_sample_payload:
                Path(args.write_sample_payload).write_text(json.dumps(generated_payload, ensure_ascii=False, indent=2), encoding='utf-8')
        if generated_payload is not None:
            payload_report = validate_survey_payload(generated_payload)
            if args.generate_sample_payload and not args.payload:
                payload_report['generated'] = True
                if args.write_sample_payload:
                    payload_report['outputPath'] = args.write_sample_payload
            full_report['payload'] = payload_report
            full_report['summary']['payload'] = summarize(payload_report)
            full_report['valid'] = full_report['valid'] and payload_report.get('valid', False)
            if schema_data is not None:
                payload_schema_report = validate_payload_against_schema(schema_data, generated_payload)
                if args.generate_sample_payload and not args.payload:
                    payload_schema_report['generated'] = True
                full_report['payloadAgainstSchema'] = payload_schema_report
                full_report['summary']['payloadAgainstSchema'] = summarize(payload_schema_report)
                full_report['valid'] = full_report['valid'] and payload_schema_report.get('valid', False)
    except FileNotFoundError as e:
        print(f'Failed to read input: {e}', file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f'Invalid JSON: {e}', file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json.dumps(full_report, ensure_ascii=False, indent=2))
    else:
        print('✅ RELEASE CHECK PASS' if full_report['valid'] else '❌ RELEASE CHECK FAIL')
        if full_report['schema'] is not None:
            print_section('SCHEMA', full_report['schema'])
        if full_report['repair'] is not None:
            print('\n[REPAIR]')
            print(f"Stopped reason: {full_report['repair'].get('stoppedReason')}")
            print(f"Applied fixes: {len(full_report['repair'].get('appliedFixes', []))}")
        if full_report['html'] is not None:
            print_section('HTML', full_report['html'])
        if full_report.get('htmlAccessibility') is not None:
            print_section('HTML ACCESSIBILITY', full_report['htmlAccessibility'])
        if full_report.get('userVisible') is not None:
            print_section('USER VISIBLE CONTENT', full_report['userVisible'])
        if full_report['payload'] is not None:
            print_section('PAYLOAD', full_report['payload'])
        if full_report.get('payloadAgainstSchema') is not None:
            print_section('PAYLOAD AGAINST SCHEMA', full_report['payloadAgainstSchema'])
        print('\nSummary:')
        for key, value in full_report['summary'].items():
            print(f"- {key}: valid={value['valid']}, errors={value['error_count']}, warnings={value['warning_count']}")

    sys.exit(0 if full_report['valid'] else 1)


if __name__ == '__main__':
    main()
