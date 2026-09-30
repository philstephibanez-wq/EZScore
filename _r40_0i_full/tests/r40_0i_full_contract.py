#!/usr/bin/env python3
from __future__ import annotations
import ast, subprocess, sys
from pathlib import Path
ROOT=Path(sys.argv[1] if len(sys.argv)>1 else r"H:\EZScore_v1").resolve()
server=(ROOT/"worker_app/server_control.py").read_text(encoding="utf-8")
gateway=(ROOT/"worker_app/online_gateway.py").read_text(encoding="utf-8")
worker=(ROOT/"worker_app/ezscore_analysis_worker.pyw").read_text(encoding="utf-8")
launch=(ROOT/"scripts/launch_ezscore_backend.ps1").read_text(encoding="utf-8")
hta=(ROOT/"EZScore-Launcher.hta").read_text(encoding="utf-8")
assert 'ONLINE_GATEWAY_PORT = 8501' in server
assert 'ONLINE_BACKEND_PORT = 8511' in server
assert 'LOCAL_DEV_PORT = 8502' in server
assert 'APP_VERSION = "R40.0I"' in worker
assert 'self._lock' not in server
assert 'self._state_lock = threading.RLock()' in server
assert 'self._online_lock = threading.RLock()' in server
assert 'self._local_lock = threading.RLock()' in server
assert 'WEB_SCRIPT_TIMEOUT_SECONDS = 15.0' in server
assert 'proc = subprocess.Popen(' in server
assert '"protocol": "ezscore.online-gateway.v3"' in gateway
assert '"ATTENTE SERVEUR"' in worker
assert 'analysis-worker-bootstrap.json' in worker
assert 'Start-Sleep -Seconds 2' not in launch
assert '-Port 8501' not in hta
ast.parse(server); ast.parse(gateway); ast.parse(worker)
for p in (ROOT/"worker_app/server_control.py",ROOT/"worker_app/online_gateway.py",ROOT/"worker_app/ezscore_analysis_worker.pyw"):
    subprocess.run([sys.executable,"-m","py_compile",str(p)],check=True)
print("R40_0I_FULL_SERVER_CONTROL_SPLASH_CONTRACT_OK")
