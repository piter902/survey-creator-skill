#!/usr/bin/env python3
"""
Provider-neutral survey publisher entrypoint.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from providers.tencent import build_tencent_publish_plan, execute_tencent_publish


def load_manifest(manifest_path: Path) -> dict:
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def resolve_bundle_paths(manifest_path: Path, manifest: dict) -> dict[str, Path]:
    bundle_dir = manifest_path.parent
    paths = manifest.get("paths") or {}
    html_path = (bundle_dir / paths.get("html", "")).resolve()
    schema_path = (bundle_dir / paths.get("schema", "")).resolve()
    return {
        "bundle_dir": bundle_dir.resolve(),
        "html_path": html_path,
        "schema_path": schema_path,
    }


def build_publish_plan(provider: str, manifest: dict, provider_config: dict, mode: str) -> dict:
    if provider == "tencent":
        return build_tencent_publish_plan(manifest, provider_config, mode)
    raise SystemExit(f"Unsupported provider: {provider}")


def execute_publish(
    provider: str,
    manifest: dict,
    bundle_paths: dict[str, Path],
    provider_config: dict,
    mode: str,
    *,
    dry_run: bool,
) -> dict:
    if provider == "tencent":
        return execute_tencent_publish(manifest, bundle_paths, provider_config, mode, dry_run=dry_run)
    raise SystemExit(f"Unsupported provider: {provider}")


def write_publish_record(bundle_dir: Path, record: dict) -> Path:
    record_path = bundle_dir / "publish-record.json"
    record_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return record_path


def update_manifest(manifest_path: Path, manifest: dict, record: dict) -> None:
    publish = manifest.setdefault("publish", {})
    publish["provider"] = record["provider"]
    publish["mode"] = record["mode"]
    publish["surveyUrl"] = record["surveyUrl"]
    publish["schemaUrl"] = record["schemaUrl"]
    publish["htmlStorageUrl"] = record["htmlStorageUrl"]
    publish["publishedAt"] = record["publishedAt"]
    publish["meta"] = record.get("meta", {})
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, help="Absolute path to survey.manifest.json")
    parser.add_argument("--provider", required=True, help="Publisher provider name, e.g. tencent")
    parser.add_argument("--mode", default="public-web", choices=["public-web", "archive-only"])
    parser.add_argument("--config-json", required=True, help="Inline provider config JSON")
    parser.add_argument("--dry-run", action="store_true", help="Plan and emit publish record without executing upload commands")
    args = parser.parse_args()

    manifest_path = Path(args.manifest).expanduser().resolve()
    if not manifest_path.exists():
        raise SystemExit(f"Manifest not found: {manifest_path}")

    manifest = load_manifest(manifest_path)
    survey_id = manifest.get("surveyId")
    if not survey_id:
        raise SystemExit("Manifest missing required field: surveyId")

    bundle_paths = resolve_bundle_paths(manifest_path, manifest)
    if not bundle_paths["html_path"].exists():
        raise SystemExit(f"HTML file not found: {bundle_paths['html_path']}")
    if not bundle_paths["schema_path"].exists():
        raise SystemExit(f"Schema file not found: {bundle_paths['schema_path']}")

    provider_config = json.loads(args.config_json)
    plan = build_publish_plan(args.provider, manifest, provider_config, args.mode)
    publish_result = execute_publish(
        args.provider,
        manifest,
        bundle_paths,
        provider_config,
        args.mode,
        dry_run=args.dry_run,
    )
    publish_result["publishedAt"] = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    publish_result["plan"] = plan

    record_path = write_publish_record(bundle_paths["bundle_dir"], publish_result)
    update_manifest(manifest_path, manifest, publish_result)

    print(json.dumps({
        "status": "published" if not args.dry_run else "planned",
        "provider": args.provider,
        "manifest": str(manifest_path),
        "bundle": {key: str(value) for key, value in bundle_paths.items()},
        "publishRecord": str(record_path),
        "result": publish_result,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
