#!/usr/bin/env python3
import argparse, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TEMPLATE = ROOT / 'templates' / 'base-survey-template.html'
SCHEMA_MARKER = 'const surveySchema ='
STYLE_PACK_MARKER = 'const surveyStylePack ='
FORM_MARKER = 'const form = document.getElementById'


def sanitize_output_stem(value, fallback):
    candidate = (value or '').strip()
    if not candidate:
        return fallback
    safe = ''.join(ch if ch.isalnum() or ch in ('-', '_', '.') else '-' for ch in candidate).strip('-.')
    return safe or fallback


def derive_output_stem(schema, schema_path):
    survey = schema.get('survey') if isinstance(schema, dict) else None
    survey_id = survey.get('id') if isinstance(survey, dict) else None
    return sanitize_output_stem(survey_id, Path(schema_path).stem)


def resolve_html_output_path(out_arg, schema, schema_path):
    out_path = Path(out_arg)
    if out_arg.endswith('/') or out_path.is_dir():
        out_path.mkdir(parents=True, exist_ok=True)
        return out_path / f"{derive_output_stem(schema, schema_path)}.html"
    parent = out_path.parent
    if parent and not parent.exists():
        parent.mkdir(parents=True, exist_ok=True)
    return out_path


def load_json(path_str):
    return json.loads(Path(path_str).read_text(encoding='utf-8'))


def render_html_from_schema(schema, template_text, style_pack='consumer-minimal'):
    start = template_text.find(SCHEMA_MARKER)
    if start == -1:
        raise ValueError('Template missing surveySchema marker.')
    end = template_text.find(FORM_MARKER, start)
    if end == -1:
        raise ValueError('Template missing form marker after surveySchema.')
    if STYLE_PACK_MARKER not in template_text:
        raise ValueError('Template missing surveyStylePack marker.')
    schema_js = (
        'const surveySchema = ' + json.dumps(schema, ensure_ascii=False, indent=2) + ';\n\n    ' +
        f'const surveyStylePack = {json.dumps(style_pack, ensure_ascii=False)};\n\n    '
    )
    return template_text[:start] + schema_js + template_text[end:]


def main():
    parser = argparse.ArgumentParser(description='Render self-contained survey HTML from a frozen schema.')
    parser.add_argument('--schema', required=True, help='Path to schema JSON')
    parser.add_argument('--out', required=True, help='Output HTML path')
    parser.add_argument('--template', default=str(DEFAULT_TEMPLATE), help='Optional HTML template path')
    parser.add_argument('--style-pack', default='consumer-minimal', help='Optional UI style pack name')
    args = parser.parse_args()

    try:
        schema = load_json(args.schema)
        template_text = Path(args.template).read_text(encoding='utf-8')
        html = render_html_from_schema(schema, template_text, style_pack=args.style_pack)
        output_path = resolve_html_output_path(args.out, schema, args.schema)
        output_path.write_text(html, encoding='utf-8')
        print(str(output_path))
    except FileNotFoundError as e:
        print(f'File not found: {e}', file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f'Invalid JSON: {e}', file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
