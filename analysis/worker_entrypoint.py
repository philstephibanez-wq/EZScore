#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

PROTOCOL = "ezscore.analysis-job.v2"
ALLOWED_TARGETS = {"dev", "prod"}


def _norm(path: Path) -> str:
    return os.path.normcase(os.path.abspath(str(path)))


def _is_under(path: Path, root: Path) -> bool:
    try:
        Path(_norm(path)).relative_to(Path(_norm(root)))
        return True
    except ValueError:
        return False


def _validate_paths(value: Any, root: Path) -> None:
    if isinstance(value, dict):
        for nested in value.values():
            _validate_paths(nested, root)
        return
    if isinstance(value, (list, tuple)):
        for nested in value:
            _validate_paths(nested, root)
        return
    if not isinstance(value, str):
        return

    # Validate only absolute drive paths carried by the job.
    if len(value) >= 3 and value[1:3] in {":\\", ":/"}:
        candidate = Path(value)
        if not _is_under(candidate, root):
            raise RuntimeError(f"job_path_outside_target_root:{value}")


def _require_cuda_if_needed(job: dict) -> None:
    if str(job.get("resource_class") or "gpu").lower() != "gpu":
        return
    try:
        import torch
    except Exception as exc:
        raise RuntimeError(f"cuda_runtime_unavailable:{exc}") from exc
    if not bool(torch.cuda.is_available()):
        raise RuntimeError("cuda_required_but_unavailable")


def validate_job(job: dict, root: Path) -> None:
    if job.get("protocol") != PROTOCOL:
        raise RuntimeError(
            f"unsupported_job_protocol:{job.get('protocol')!r};expected={PROTOCOL}"
        )

    try:
        job_id = int(job["job_id"])
    except Exception as exc:
        raise RuntimeError("invalid_job_id") from exc
    if job_id <= 0:
        raise RuntimeError("invalid_job_id")

    target = str(job.get("target") or "").lower()
    if target not in ALLOWED_TARGETS:
        raise RuntimeError(f"invalid_job_target:{target!r}")

    env_target = str(os.environ.get("EZS_TARGET") or "").lower()
    if env_target and env_target != target:
        raise RuntimeError(
            f"job_target_mismatch:envelope={target};environment={env_target}"
        )

    expected_root = os.environ.get("EZS_EXPECTED_ROOT")
    if expected_root and _norm(Path(expected_root)) != _norm(root):
        raise RuntimeError(
            f"job_root_mismatch:actual={root};expected={expected_root}"
        )

    if not str(job.get("kind") or "").strip():
        raise RuntimeError("job_kind_missing")

    _validate_paths(job.get("paths") or {}, root)
    _require_cuda_if_needed(job)


def main() -> int:
    parser = argparse.ArgumentParser(prog="EZScore analysis worker entrypoint")
    parser.add_argument("--job-file", required=True)
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    job_path = Path(args.job_file)

    try:
        job = json.loads(job_path.read_text(encoding="utf-8"))
        if not isinstance(job, dict):
            raise RuntimeError("job_envelope_must_be_object")

        validate_job(job, root)

        # Import after contract validation so invalid jobs cannot trigger analysis imports.
        analysis_dir = Path(__file__).resolve().parent
        if str(analysis_dir) not in sys.path:
            sys.path.insert(0, str(analysis_dir))
        from jobs import dispatch_job

        rc = dispatch_job(job, root)
        if rc != 0:
            print(json.dumps({
                "event": "job_exit",
                "job_id": int(job["job_id"]),
                "returncode": int(rc),
            }, ensure_ascii=False), flush=True)
            return int(rc)

        print(json.dumps({
            "event": "job_complete",
            "job_id": int(job["job_id"]),
            "kind": str(job["kind"]),
            "protocol": PROTOCOL,
        }, ensure_ascii=False), flush=True)
        return 0

    except Exception as exc:
        print(json.dumps({
            "event": "job_error",
            "error": str(exc),
            "protocol": PROTOCOL,
        }, ensure_ascii=False), file=sys.stderr, flush=True)
        return 70


if __name__ == "__main__":
    raise SystemExit(main())
