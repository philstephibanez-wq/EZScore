#!/usr/bin/env python3
from __future__ import annotations

import ast, subprocess, sys
from pathlib import Path

BASE_COMMIT = '2ce7da1213788bb8d37c14073001aa872fb024c9'
ROOT = Path(sys.argv[1] if len(sys.argv)>1 else r'H:\EZScore_v1').resolve()
RELS = {
  'server':'worker_app/server_control.py',
  'worker':'worker_app/ezscore_analysis_worker.pyw',
  'ci':'.github/workflows/ci.yml',
}
FILES={k:ROOT/v for k,v in RELS.items()}

def git(*args):
    return subprocess.run(['git',*args],cwd=str(ROOT),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',errors='replace',check=False)

def git_show(rel):
    p=git('show',f'HEAD:{rel}')
    if p.returncode!=0: raise RuntimeError(f'git show HEAD:{rel} failed: {p.stderr.strip()}')
    return p.stdout.replace('\r\n','\n').replace('\r','\n').lstrip('\ufeff')

def rep(text,old,new,label):
    n=text.count(old)
    if n!=1: raise RuntimeError(f'{label}: expected 1 anchor, found {n}')
    return text.replace(old,new,1)

def write_atomic(path,text):
    tmp=path.with_suffix(path.suffix+'.r41g.tmp')
    tmp.write_text(text,encoding='utf-8',newline='\n')
    tmp.replace(path)

def guard():
    h=git('rev-parse','HEAD')
    if h.returncode!=0: raise RuntimeError('git rev-parse HEAD failed')
    actual=h.stdout.strip()
    if actual!=BASE_COMMIT: raise RuntimeError(f'HEAD={actual}; expected {BASE_COMMIT}. STOP.')
    if git('diff','--quiet').returncode!=0: raise RuntimeError('Tracked working-tree changes detected. STOP.')
    if git('diff','--cached','--quiet').returncode!=0: raise RuntimeError('Staged changes detected. STOP.')

def main():
    guard()
    original={k:p.read_bytes() for k,p in FILES.items()}
    src={k:git_show(v) for k,v in RELS.items()}
    baseline=[
      ('APP_VERSION = "R41.0F"' in src['worker'],'worker R41.0F'),
      ('gateway_is_alive = bool(' in src['server'],'server health baseline'),
      ('def _apply_server_snapshot(self, data: dict)' in src['worker'],'snapshot baseline'),
      ('DEFAULT_URI=' not in src['ci'],'CI DEFAULT_URI not yet present'),
    ]
    bad=[name for ok,name in baseline if not ok]
    if bad: raise RuntimeError('R41.0G baseline mismatch: '+', '.join(bad)+'. STOP.')
    try:
        server=src['server']
        server=rep(server,'    def status(self) -> dict:\n        desired = self.snapshot_desired()\n        gateway_pid = _read_pid(self.online_gateway_pid)\n        backend_pid = _read_pid(self.online_backend_pid)\n        local_pid = _read_pid(self.local_pid)\n        gateway_is_alive = bool(gateway_pid and _pid_alive(gateway_pid) and gateway_alive(self.online_url(), 0.35))\n        backend_alive = bool(backend_pid and _pid_alive(backend_pid) and http_alive(self.online_backend_url(), 0.35))\n        local_alive = bool(local_pid and _pid_alive(local_pid) and http_alive(self.local_url(), 0.35))\n        runtime = gateway_runtime_status(self.online_url(), 0.35) if gateway_is_alive else None\n        maintenance_observed = bool(runtime.get("maintenance", False)) if isinstance(runtime, dict) else None\n        return {\n            "desired": desired,\n            "online": {\n                "gateway_alive": gateway_is_alive,\n                "backend_alive": backend_alive,\n                "gateway_pid": gateway_pid,\n                "backend_pid": backend_pid,\n                "env": desired["online"]["env"],\n                "maintenance": desired["online"]["maintenance"],\n                "maintenance_observed": maintenance_observed,\n                "public_url": self.public_url(),\n            },\n            "local": {\n                "alive": local_alive,\n                "pid": local_pid,\n                "env": "dev",\n                "url": self.local_url(),\n            },\n            "worker": {"target": desired["worker"]["target"], "url": self.worker_url()},\n        }\n','    def status(self) -> dict:\n        desired = self.snapshot_desired()\n        gateway_pid = _read_pid(self.online_gateway_pid)\n        backend_pid = _read_pid(self.online_backend_pid)\n        local_pid = _read_pid(self.local_pid)\n\n        # Process state and HTTP health are deliberately separate.\n        # A transient HTTP timeout must never make the UI claim that a process stopped.\n        gateway_process_alive = bool(gateway_pid and _pid_alive(gateway_pid))\n        backend_process_alive = bool(backend_pid and _pid_alive(backend_pid))\n        local_process_alive = bool(local_pid and _pid_alive(local_pid))\n\n        gateway_http_healthy = bool(\n            gateway_process_alive and gateway_alive(self.online_url(), 1.0)\n        )\n        backend_http_healthy = bool(\n            backend_process_alive and http_alive(self.online_backend_url(), 1.0)\n        )\n        local_http_healthy = bool(\n            local_process_alive and http_alive(self.local_url(), 1.0)\n        )\n\n        runtime = (\n            gateway_runtime_status(self.online_url(), 1.0)\n            if gateway_http_healthy\n            else None\n        )\n        maintenance_observed = (\n            bool(runtime.get("maintenance", False))\n            if isinstance(runtime, dict)\n            else None\n        )\n\n        return {\n            "desired": desired,\n            "online": {\n                # Legacy fields kept for compatibility with any existing consumer.\n                "gateway_alive": gateway_http_healthy,\n                "backend_alive": backend_http_healthy,\n                # R41.0G explicit process/health split.\n                "gateway_process_alive": gateway_process_alive,\n                "backend_process_alive": backend_process_alive,\n                "gateway_http_healthy": gateway_http_healthy,\n                "backend_http_healthy": backend_http_healthy,\n                "gateway_pid": gateway_pid,\n                "backend_pid": backend_pid,\n                "env": desired["online"]["env"],\n                "maintenance": desired["online"]["maintenance"],\n                "maintenance_observed": maintenance_observed,\n                "public_url": self.public_url(),\n            },\n            "local": {\n                # Legacy field kept for compatibility.\n                "alive": local_http_healthy,\n                # R41.0G explicit process/health split.\n                "process_alive": local_process_alive,\n                "http_healthy": local_http_healthy,\n                "pid": local_pid,\n                "env": "dev",\n                "url": self.local_url(),\n            },\n            "worker": {"target": desired["worker"]["target"], "url": self.worker_url()},\n        }\n','server status split')

        worker=src['worker']
        worker=rep(worker,'APP_VERSION = "R41.0F"','APP_VERSION = "R41.0G"','worker version')
        worker=rep(worker,'        self._last_snapshot: dict = {}\n        self._server_action_running = False\n        self._bootstrap_path = project_root() / "var" / "runtime" / "analysis-worker-bootstrap.json"\n','        self._last_snapshot: dict = {}\n        self._server_action_running = False\n\n        # R41.0G health hysteresis. Process state is authoritative for\n        # ACTIF/ARRÊTÉ; HTTP health only controls secondary/degraded status.\n        self._health_state = {\n            "online_backend": {"bad": 0, "good": 0, "degraded": False},\n            "online_gateway": {"bad": 0, "good": 0, "degraded": False},\n            "local_http": {"bad": 0, "good": 0, "degraded": False},\n        }\n\n        self._bootstrap_path = project_root() / "var" / "runtime" / "analysis-worker-bootstrap.json"\n','health state init')
        worker=rep(worker,'    def _apply_server_snapshot(self, data: dict) -> None:\n        self._last_snapshot = data\n        online = data.get("online") or {}\n        local = data.get("local") or {}\n        worker = data.get("worker") or {}\n        desired = data.get("desired") or self.server_control.snapshot_desired()\n\n        gateway_ok = bool(online.get("gateway_alive"))\n        backend_ok = bool(online.get("backend_alive"))\n        online_env = str(online.get("env") or desired["online"]["env"])\n        maintenance = bool(online.get("maintenance"))\n        maintenance_observed = online.get("maintenance_observed")\n        if gateway_ok:\n            if maintenance_observed is True and maintenance:\n                state = "MAINTENANCE"\n            elif backend_ok:\n                state = "ONLINE"\n            else:\n                state = "PROTÉGÉ · backend indisponible"\n            self.online_summary_var.set(f"● {state} / {online_env}")\n            profiler = "Profiler actif" if online_env == "dev" else "Profiler inactif"\n            self.online_detail_var.set(f"{online.get(\'public_url\') or self.server_control.public_url()} · {profiler} · backend :8511")\n        else:\n            self.online_summary_var.set(f"○ ARRÊTÉ / {online_env}")\n            self.online_detail_var.set(f"{online.get(\'public_url\') or self.server_control.public_url()} · backend arrêté")\n        self.online_env_var.set(online_env)\n        self.online_maintenance_var.set(maintenance)\n\n        if local.get("alive"):\n            self.local_summary_var.set("● ACTIF / dev")\n            self.local_detail_var.set(f"{local.get(\'url\') or self.server_control.local_url()} · PID {local.get(\'pid\') or \'—\'}")\n        else:\n            self.local_summary_var.set("○ ARRÊTÉ / dev")\n            self.local_detail_var.set(self.server_control.local_url())\n\n        target = str(worker.get("target") or desired["worker"]["target"]).upper()\n        self.worker_target_var.set(target)\n        self.worker_summary_var.set(f"{self.status_var.get()} · {target}")\n        self.url_var.set(str(worker.get("url") or self.server_control.worker_url()))\n','    def _health_degraded(self, key: str, healthy: bool) -> bool:\n        state = self._health_state[key]\n        if healthy:\n            state["good"] += 1\n            state["bad"] = 0\n            if state["degraded"] and state["good"] >= 2:\n                state["degraded"] = False\n        else:\n            state["bad"] += 1\n            state["good"] = 0\n            if not state["degraded"] and state["bad"] >= 3:\n                state["degraded"] = True\n        return bool(state["degraded"])\n\n    def _apply_server_snapshot(self, data: dict) -> None:\n        self._last_snapshot = data\n        online = data.get("online") or {}\n        local = data.get("local") or {}\n        worker = data.get("worker") or {}\n        desired = data.get("desired") or self.server_control.snapshot_desired()\n\n        gateway_process = bool(\n            online.get("gateway_process_alive", online.get("gateway_alive"))\n        )\n        backend_process = bool(\n            online.get("backend_process_alive", online.get("backend_alive"))\n        )\n        gateway_http = bool(\n            online.get("gateway_http_healthy", online.get("gateway_alive"))\n        )\n        backend_http = bool(\n            online.get("backend_http_healthy", online.get("backend_alive"))\n        )\n\n        gateway_degraded = self._health_degraded("online_gateway", gateway_http)\n        backend_degraded = self._health_degraded("online_backend", backend_http)\n\n        online_env = str(online.get("env") or desired["online"]["env"])\n        maintenance = bool(online.get("maintenance"))\n        maintenance_observed = online.get("maintenance_observed")\n\n        # Process liveness is authoritative. HTTP health cannot flip ACTIVE/STOPPED.\n        if gateway_process:\n            if maintenance_observed is True and maintenance:\n                state = "MAINTENANCE"\n            elif not backend_process:\n                state = "PROTÉGÉ · backend arrêté"\n            elif gateway_degraded:\n                state = "ONLINE · passerelle lente"\n            elif backend_degraded:\n                state = "PROTÉGÉ · backend indisponible"\n            else:\n                state = "ONLINE"\n\n            self.online_summary_var.set(f"● {state} / {online_env}")\n            profiler = "Profiler actif" if online_env == "dev" else "Profiler inactif"\n            health_note = ""\n            if backend_process and not backend_http and not backend_degraded:\n                health_note = " · vérification HTTP"\n            self.online_detail_var.set(\n                f"{online.get(\'public_url\') or self.server_control.public_url()} "\n                f"· {profiler} · backend :8511{health_note}"\n            )\n        else:\n            self.online_summary_var.set(f"○ ARRÊTÉ / {online_env}")\n            self.online_detail_var.set(\n                f"{online.get(\'public_url\') or self.server_control.public_url()} "\n                "· passerelle arrêtée"\n            )\n\n        self.online_env_var.set(online_env)\n        self.online_maintenance_var.set(maintenance)\n\n        local_process = bool(local.get("process_alive", local.get("alive")))\n        local_http = bool(local.get("http_healthy", local.get("alive")))\n        local_degraded = self._health_degraded("local_http", local_http)\n\n        if local_process:\n            state = "ACTIF · HTTP lent" if local_degraded else "ACTIF"\n            self.local_summary_var.set(f"● {state} / dev")\n            detail = (\n                f"{local.get(\'url\') or self.server_control.local_url()} "\n                f"· PID {local.get(\'pid\') or \'—\'}"\n            )\n            if not local_http and not local_degraded:\n                detail += " · vérification HTTP"\n            self.local_detail_var.set(detail)\n        else:\n            self.local_summary_var.set("○ ARRÊTÉ / dev")\n            self.local_detail_var.set(self.server_control.local_url())\n\n        target = str(worker.get("target") or desired["worker"]["target"]).upper()\n        self.worker_target_var.set(target)\n        self.worker_summary_var.set(f"{self.status_var.get()} · {target}")\n        self.url_var.set(str(worker.get("url") or self.server_control.worker_url()))\n','stable snapshot UI')

        ci=src['ci']
        ci=rep(ci,'          ANALYSIS_WORKER_TOKEN=ci-worker-token\n          EOF\n','          ANALYSIS_WORKER_TOKEN=ci-worker-token\n          DEFAULT_URI=http://localhost\n          EZ_ANALYSIS_URL=http://127.0.0.1:8502\n          TURNSTILE_SITE_KEY=ci-placeholder\n          TURNSTILE_SECRET_KEY=ci-placeholder\n          EOF\n','CI missing envs')

        contracts=[
          ('APP_VERSION = "R41.0G"' in worker,'version'),
          ('gateway_process_alive' in server and 'gateway_http_healthy' in server,'online split'),
          ('process_alive' in server and 'http_healthy' in server,'local split'),
          ('timeout=1.0' not in server or True,'noop'),
          ('def _health_degraded' in worker,'hysteresis helper'),
          ('state["bad"] >= 3' in worker,'3 failures'),
          ('state["good"] >= 2' in worker,'2 successes'),
          ('PROTÉGÉ · backend arrêté' in worker,'real backend stop'),
          ('ACTIF · HTTP lent' in worker,'local degraded but active'),
          ('DEFAULT_URI=http://localhost' in ci,'CI DEFAULT_URI'),
          ('EZ_ANALYSIS_URL=http://127.0.0.1:8502' in ci,'CI analysis URL'),
          ('TURNSTILE_SITE_KEY=ci-placeholder' in ci,'CI turnstile'),
        ]
        failed=[name for ok,name in contracts if not ok]
        if failed: raise RuntimeError('R41.0G invariant failed: '+', '.join(failed))

        ast.parse(server); ast.parse(worker)
        write_atomic(FILES['server'],server)
        write_atomic(FILES['worker'],worker)
        write_atomic(FILES['ci'],ci)

        for pth in (FILES['server'],FILES['worker']):
            p=subprocess.run([sys.executable,'-m','py_compile',str(pth)],cwd=str(ROOT),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace',check=False)
            if p.returncode!=0: raise RuntimeError(f'py_compile failed: {pth}\n{p.stdout}')

        print('R41_0G_SERVER_STATUS_STABILITY_CI_INSTALL_OK')
        return 0
    except Exception:
        for k,data in original.items(): FILES[k].write_bytes(data)
        raise

if __name__=='__main__':
    try: raise SystemExit(main())
    except Exception as exc:
        print(f'ERROR: {exc}',file=sys.stderr)
        raise SystemExit(1)
