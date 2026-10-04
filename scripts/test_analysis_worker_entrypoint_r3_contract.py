from __future__ import annotations

import ast
import importlib.util
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENTRY = ROOT / "analysis" / "worker_entrypoint.py"

assert ENTRY.is_file(), ENTRY

source = ENTRY.read_text(encoding="utf-8")
assert 'PROTOCOL = "ezscore.analysis-job.v2"' in source
assert "EZS_TARGET" in source
assert "EZS_EXPECTED_ROOT" in source
assert "cuda_required_but_unavailable" in source
assert "unsupported_job_protocol" in source
assert "job_path_outside_target_root" in source

tree = ast.parse(source)
imports = {
    node.module
    for node in ast.walk(tree)
    if isinstance(node, ast.ImportFrom) and node.module
}
assert not any((module or "").startswith("EZS_orchestrator") for module in imports)

for name in ("stems_job.py", "chords_job.py", "lyrics_job.py", "dispatch.py"):
    assert (ROOT / "analysis" / "jobs" / name).is_file(), name

dispatch = (ROOT / "analysis" / "jobs" / "dispatch.py").read_text(encoding="utf-8")
for kind in ('"stems"', '"chords"', '"lyrics"'):
    assert kind in dispatch

print("EZSCORE_ANALYSIS_ENTRYPOINT_R3_CONTRACT_OK")
