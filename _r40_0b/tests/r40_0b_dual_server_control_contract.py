#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import threading
import http.server
import socket
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else r"H:\EZScore_v1").resolve()


def rd(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n").replace("\r", "\n")


def check(ok: bool, label: str) -> None:
    if not ok:
        raise AssertionError(label)


def run(cmd: list[str]) -> str:
    p = subprocess.run(cmd, cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       text=True, encoding="utf-8", errors="replace", check=False)
    if p.returncode != 0:
        raise AssertionError(f"Command failed: {' '.join(cmd)}\n{p.stdout}")
    return p.stdout


worker = ROOT / "worker_app" / "ezscore_analysis_worker.pyw"
control = ROOT / "worker_app" / "server_control.py"
gateway = ROOT / "worker_app" / "online_gateway.py"
start_web = ROOT / "scripts" / "start_ezscore_web.ps1"
launch = ROOT / "scripts" / "launch_ezscore_backend.ps1"
kernel = ROOT / "src" / "Kernel.php"
for path in (worker, control, gateway, start_web, launch, kernel):
    check(path.is_file(), f"missing {path}")

w = rd(worker)
c = rd(control)
g = rd(gateway)
s = rd(start_web)
k = rd(kernel)

check('APP_VERSION = "R40.0B"' in w, "R40.0B worker version")
check('from server_control import ServerController' in w, "server control import")
check('controller.worker_url()' in w, "effective API target comes from persisted controller")
check('class ServerStatusMonitor:' in w and 'class LocalServerMonitor:' not in w, "new server monitor only")
check('ONLINE_GATEWAY_PORT = 8501' in c, "online public gateway port")
check('ONLINE_BACKEND_PORT = 8511' in c, "online backend port")
check('LOCAL_DEV_PORT = 8502' in c, "local dev port")
check('"online": {"running": True, "maintenance": False, "env": "prod"}' in c, "default online state")
check('"local": {"running": False, "env": "dev"}' in c, "local dev-only state")
check('"worker": {"target": "online"}' in c, "default worker target")
check('ezscore-server-control.json' in c, "persistent state file")
check('restart_online' in c and 'set_online_environment' in c, "online environment auto restart")
check('restore_desired' in c, "mode restoration on Worker restart")
check('legacy_pid_file' in c and 'ezscore-web.pid' in c, "R39 server migration")
check('maintenance and not is_internal' in g, "maintenance blocks public but not worker internal API")
check('self.send_response(503)' in g, "maintenance serves 503 intentionally")
check('[ValidateSet("online", "local")]' in s, "PowerShell instance contract")
check('if ($Instance -eq "local" -and $Environment -ne "dev")' in s, "local is dev only")
check('$env:APP_ENV = $Environment' in s and '$env:EZSCORE_INSTANCE = $Instance' in s, "instance environment exported")
check("'/var/cache/'.$instance.'/'.$this->environment" in k, "isolated Symfony cache")
check("'/var/log/'.$instance" in k, "isolated Symfony log")

run([sys.executable, "-m", "py_compile", str(control), str(gateway), str(worker)])
run(["php", "-l", str(kernel)])
run(["php", "bin\\console", "lint:container"])

if os.name == "nt":
    for ps1 in (start_web, launch):
        escaped = str(ps1).replace("'", "''")
        script = (
            "$tokens=$null; $errors=$null; "
            f"[System.Management.Automation.Language.Parser]::ParseFile('{escaped}',[ref]$tokens,[ref]$errors)|Out-Null; "
            "if($errors.Count -gt 0){$errors | ForEach-Object { Write-Host $_.Message }; exit 1}"
        )
        run(["powershell", "-NoProfile", "-Command", script])

# Persistence contract without starting any real process.
spec = importlib.util.spec_from_file_location("ezscore_r40_server_control", control)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)
with tempfile.TemporaryDirectory() as td:
    fake = Path(td)
    (fake / "var" / "runtime").mkdir(parents=True)
    state_path = fake / "var" / "runtime" / "ezscore-server-control.json"
    state_path.write_text(json.dumps({
        "schema_version": module.STATE_SCHEMA,
        "online": {"running": False, "maintenance": True, "env": "prod"},
        "local": {"running": False, "env": "dev"},
        "worker": {"target": "online"},
    }), encoding="utf-8")
    ctl = module.ServerController(fake)
    ctl.set_online_environment("dev")
    ctl.set_worker_target("local")
    ctl.set_maintenance(False)
    ctl2 = module.ServerController(fake)
    persisted = ctl2.snapshot_desired()
    check(persisted["online"]["env"] == "dev", "persist online env")
    check(persisted["online"]["maintenance"] is False, "persist maintenance")
    check(persisted["worker"]["target"] == "local", "persist worker target")
    check(persisted["local"]["env"] == "dev", "local remains dev")


# Gateway contract: public proxy works, maintenance yields intentional 503,
# and the gateway health endpoint remains available while maintenance is ON.
class _BackendHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        payload = b"R40_GATEWAY_BACKEND_OK"
        self.send_response(200)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)
    def log_message(self, *args):
        pass

def _free_port() -> int:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port

backend_port = _free_port()
gateway_port = _free_port()
backend = http.server.ThreadingHTTPServer(("127.0.0.1", backend_port), _BackendHandler)
threading.Thread(target=backend.serve_forever, daemon=True).start()
with tempfile.TemporaryDirectory() as td_gateway:
    groot = Path(td_gateway)
    (groot / "var" / "runtime").mkdir(parents=True)
    gateway_cfg = groot / "var" / "runtime" / "online-gateway.json"
    gateway_cfg.write_text(json.dumps({
        "maintenance": False,
        "backend_host": "127.0.0.1",
        "backend_port": backend_port,
    }), encoding="utf-8")
    gp = subprocess.Popen([sys.executable, str(gateway), "--root", str(groot), "--port", str(gateway_port)],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        health = f"http://127.0.0.1:{gateway_port}/__ezscore_gateway_health"
        deadline = time.monotonic() + 5
        while True:
            try:
                if urllib.request.urlopen(health, timeout=0.3).status == 200:
                    break
            except Exception:
                if time.monotonic() >= deadline:
                    raise AssertionError("gateway did not start")
                time.sleep(0.1)
        proxied = urllib.request.urlopen(f"http://127.0.0.1:{gateway_port}/fr/login", timeout=1).read()
        check(proxied == b"R40_GATEWAY_BACKEND_OK", "gateway proxies ONLINE backend")
        gateway_cfg.write_text(json.dumps({
            "maintenance": True,
            "backend_host": "127.0.0.1",
            "backend_port": backend_port,
        }), encoding="utf-8")
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{gateway_port}/fr/login", timeout=1)
            raise AssertionError("maintenance should return 503")
        except urllib.error.HTTPError as exc:
            check(exc.code == 503, "maintenance intentional 503")
        check(urllib.request.urlopen(health, timeout=1).status == 200, "gateway health survives maintenance")
    finally:
        gp.terminate()
        try:
            gp.wait(timeout=5)
        except subprocess.TimeoutExpired:
            gp.kill()
        backend.shutdown()

print("R40_0B_DUAL_SERVER_CONTROL_CONTRACT_OK")
