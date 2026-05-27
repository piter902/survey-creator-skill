#!/usr/bin/env python3
from pathlib import Path
import argparse

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'template-src' / 'partials'
RUNTIME_SRC = ROOT / 'template-src' / 'runtime'
OUT = ROOT / 'templates' / 'base-survey-template.html'
ORDER = [
    ('head.html', ''),
    ('styles.css', '<style>\n'),
    ('body.html', '  </style>\n'),
    ('tail.html', ''),
]


def read(path: Path) -> str:
    return path.read_text(encoding='utf-8')


def read_runtime(runtime_dir: Path) -> str:
    files = sorted(runtime_dir.glob('*.js'))
    if not files:
        raise FileNotFoundError(f'No runtime modules found in {runtime_dir}')
    return ''.join(read(path) for path in files)


def build(src_dir: Path, runtime_dir: Path) -> str:
    chunks = []
    for name, prefix in ORDER:
        chunks.append(prefix)
        if name == 'tail.html':
            chunks.append('  <script>\n')
            chunks.append(read_runtime(runtime_dir))
            chunks.append('  </script>\n')
        chunks.append(read(src_dir / name))
    return ''.join(chunks)


def main():
    parser = argparse.ArgumentParser(description='Build the frozen single-file survey template from split source files.')
    parser.add_argument('--src-dir', default=str(SRC), help='Directory containing template partials')
    parser.add_argument('--runtime-dir', default=str(RUNTIME_SRC), help='Directory containing ordered runtime JS modules')
    parser.add_argument('--out', default=str(OUT), help='Output path for the built single-file template')
    args = parser.parse_args()

    src_dir = Path(args.src_dir)
    runtime_dir = Path(args.runtime_dir)
    out = Path(args.out)
    built = build(src_dir, runtime_dir)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(built, encoding='utf-8')
    print(out)


if __name__ == '__main__':
    main()
