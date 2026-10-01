#!/usr/bin/env python3
from __future__ import annotations
import ast, subprocess, sys
from pathlib import Path

ROOT=Path(sys.argv[1] if len(sys.argv)>1 else r"H:\EZScore_v1").resolve()
rd=lambda p:(ROOT/p).read_text(encoding="utf-8-sig")

server=rd("worker_app/server_control.py")
worker=rd("worker_app/ezscore_analysis_worker.pyw")
ci=rd(".github/workflows/ci.yml")

assert 'APP_VERSION = "R41.0G"' in worker

# Process liveness and HTTP health must be distinct.
for token in (
    "gateway_process_alive",
    "backend_process_alive",
    "local_process_alive",
    "gateway_http_healthy",
    "backend_http_healthy",
    "local_http_healthy",
):
    assert token in server, token

# Legacy keys remain for compatibility.
assert '"gateway_alive": gateway_http_healthy' in server
assert '"backend_alive": backend_http_healthy' in server
assert '"alive": local_http_healthy' in server

# UI hysteresis: 3 misses to degrade, 2 hits to recover.
assert 'def _health_degraded(self, key: str, healthy: bool)' in worker
assert 'state["bad"] >= 3' in worker
assert 'state["good"] >= 2' in worker

# Local remains ACTIF while process exists even if HTTP is degraded.
assert 'if local_process:' in worker
assert 'ACTIF · HTTP lent' in worker
assert 'PROTÉGÉ · backend arrêté' in worker
assert 'vérification HTTP' in worker

# CI F already fixed physical .env; G completes required runtime env.
assert "Prepare CI environment file" in ci
assert "DEFAULT_URI=http://localhost" in ci
assert "EZ_ANALYSIS_URL=http://127.0.0.1:8502" in ci
assert "TURNSTILE_SITE_KEY=ci-placeholder" in ci
assert "TURNSTILE_SECRET_KEY=ci-placeholder" in ci

# Critical pipeline/launcher contracts remain untouched.
assert "lv_chordia" in worker
assert "timeout=60," in worker
assert "Restauration incomplète · Worker actif" in worker

ast.parse(server)
ast.parse(worker)
for pth in (ROOT/"worker_app/server_control.py", ROOT/"worker_app/ezscore_analysis_worker.pyw"):
    subprocess.run([sys.executable,"-m","py_compile",str(pth)],check=True)

p=subprocess.run(["git","diff","--name-only"],cwd=str(ROOT),stdout=subprocess.PIPE,text=True,encoding="utf-8",check=True)
changed={x.strip() for x in p.stdout.splitlines() if x.strip()}
expected={
    ".github/workflows/ci.yml",
    "worker_app/ezscore_analysis_worker.pyw",
    "worker_app/server_control.py",
}
assert changed==expected,(sorted(changed),sorted(expected))

for forbidden in (
    "analysis/chord_timeline_analysis.py",
    "public/assets/js/chordslab.js",
    "public/assets/js/stems-mixer.js",
):
    assert forbidden not in changed

print("R41_0G_SERVER_STATUS_STABILITY_CI_CONTRACT_OK")
