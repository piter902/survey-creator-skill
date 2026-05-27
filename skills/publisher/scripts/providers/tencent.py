from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


REQUIRED_TENCENT_ARCHIVE_KEYS = ["bucket", "region", "prefix"]
REQUIRED_TENCENT_PUBLIC_WEB_KEYS = ["type", "envId", "prefix"]


def _require_keys(target: dict, keys: list[str], label: str) -> None:
    missing = [key for key in keys if not target.get(key)]
    if missing:
        raise SystemExit(f"Missing required {label} config: {', '.join(missing)}")


def build_tencent_publish_plan(manifest: dict, provider_config: dict, mode: str) -> dict:
    archive = provider_config.get("archive") or {}
    public_web = provider_config.get("publicWeb") or {}
    _require_keys(archive, REQUIRED_TENCENT_ARCHIVE_KEYS, "Tencent archive")
    if mode == "public-web":
        _require_keys(public_web, REQUIRED_TENCENT_PUBLIC_WEB_KEYS, "Tencent publicWeb")

    survey_id = manifest["surveyId"]
    archive_prefix = archive["prefix"].strip("/ ")
    archive_base = f"{archive_prefix}/{survey_id}" if archive_prefix else survey_id
    public_prefix = public_web.get("prefix", "").strip("/ ")
    public_path_prefix = f"/{public_prefix}" if public_prefix else ""
    public_path = f"{public_path_prefix}/{survey_id}.html" if public_path_prefix else f"/{survey_id}.html"

    return {
        "surveyId": survey_id,
        "provider": "tencent",
        "mode": mode,
        "archive": {
            "bucket": archive["bucket"],
            "region": archive["region"],
            "schemaObjectKey": f"{archive_base}/survey.schema.json",
            "htmlObjectKey": f"{archive_base}/survey.html",
        },
        "publicWeb": {
            "type": public_web.get("type", ""),
            "envId": public_web.get("envId", ""),
            "publicPath": public_path,
        },
    }


def _require_command(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise SystemExit(f"Required command not found: {name}")
    return path


def _run(command: list[str], *, dry_run: bool) -> dict:
    if dry_run:
        return {"command": command, "returncode": 0, "stdout": "", "stderr": "", "skipped": True}
    completed = subprocess.run(command, capture_output=True, text=True)
    if completed.returncode != 0:
        raise SystemExit(
            f"Command failed: {' '.join(command)}\nstdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    return {
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "skipped": False,
    }


def _tencent_schema_url(bucket: str, region: str, object_key: str) -> str:
    return f"https://{bucket}.cos.{region}.myqcloud.com/{object_key}"


def _tencent_hosting_url(env_id: str, public_path: str) -> str:
    return f"https://{env_id}.tcloudbaseapp.com{public_path}"


def execute_tencent_publish(
    manifest: dict,
    bundle_paths: dict[str, Path],
    provider_config: dict,
    mode: str,
    *,
    dry_run: bool,
) -> dict:
    plan = build_tencent_publish_plan(manifest, provider_config, mode)
    survey_id = manifest["surveyId"]

    archive = plan["archive"]
    public_web = plan["publicWeb"]
    cos_url = _tencent_schema_url(archive["bucket"], archive["region"], archive["schemaObjectKey"])
    html_archive_url = _tencent_schema_url(archive["bucket"], archive["region"], archive["htmlObjectKey"])
    survey_url = _tencent_hosting_url(public_web["envId"], public_web["publicPath"]) if mode == "public-web" else ""

    steps: list[dict] = []
    archive_meta: dict[str, object] = {
        "bucket": archive["bucket"],
        "region": archive["region"],
        "schemaObjectKey": archive["schemaObjectKey"],
        "htmlObjectKey": archive["htmlObjectKey"],
    }

    coscli = shutil.which("coscli")
    if coscli:
        schema_target = f"cos://{archive['bucket']}/{archive['schemaObjectKey']}"
        html_target = f"cos://{archive['bucket']}/{archive['htmlObjectKey']}"
        steps.append(_run([coscli, "cp", str(bundle_paths["schema_path"]), schema_target], dry_run=dry_run))
        steps.append(_run([coscli, "cp", str(bundle_paths["html_path"]), html_target], dry_run=dry_run))
        archive_meta["archiveStatus"] = "uploaded"
    else:
        archive_meta["archiveStatus"] = "skipped"
        archive_meta["archiveReason"] = "coscli-not-installed"

    if mode == "public-web":
        tcb = _require_command("tcb")
        public_target = public_web["publicPath"]
        steps.append(
            _run(
                [
                    tcb,
                    "hosting",
                    "deploy",
                    str(bundle_paths["html_path"]),
                    public_target,
                    "-e",
                    public_web["envId"],
                ],
                dry_run=dry_run,
            )
        )

    return {
        "publishId": f"publish-{survey_id}",
        "surveyId": survey_id,
        "provider": "tencent",
        "mode": mode,
        "surveyUrl": survey_url,
        "schemaUrl": cos_url,
        "htmlStorageUrl": html_archive_url,
        "meta": {
            **archive_meta,
            "envId": public_web["envId"],
            "publicPath": public_web["publicPath"],
            "steps": steps,
        },
    }
