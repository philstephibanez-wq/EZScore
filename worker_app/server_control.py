#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import queue
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path
from typing import Callable

WINDOWS_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
ONLINE_GATEWAY_PORT = 8501
ONLINE_BACKEND_PORT = 8511
LOCAL_DEV_PORT = 8502
STATE_SCHEMA = "ezscore.server-control.v1"
GATEWAY_PROTOCOL = "ezscore.online-gateway.v3"
WEB_SCRIPT_TIMEOUT_SECONDS = 15.0


def _atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _read_json(path: Path, default: dict) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else dict(default)
    except Exception:
        return dict(default)


def _pid_alive(pid: int | None) -> bool:
    if not pid or pid <= 0:
        return False
    if os.name == "nt":
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-Command", f"if (Get-Process -Id {pid} -ErrorAction SilentlyContinue) {{ exit 0 }} else {{ exit 1 }}"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=WINDOWS_NO_WINDOW,
            check=False,
        )
        return proc.returncode == 0
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _read_pid(path: Path) -> int | None:
    try:
        value = int(path.read_text(encoding="ascii", errors="ignore").strip())
        return value if value > 0 else None
    except Exception:
        return None


def _stop_pid(path: Path, timeout: float = 10.0) -> bool:
    pid = _read_pid(path)
    if not pid:
        path.unlink(missing_ok=True)
        return True
    if os.name == "nt":
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", f"Stop-Process -Id {pid} -Force -ErrorAction SilentlyContinue"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=WINDOWS_NO_WINDOW,
            check=False,
        )
    else:
        try:
            os.kill(pid, 15)
        except OSError:
            pass
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not _pid_alive(pid):
            path.unlink(missing_ok=True)
            return True
        time.sleep(0.2)
    return not _pid_alive(pid)


def http_alive(base_url: str, timeout: float = 1.0) -> bool:
    req = urllib.request.Request(
        base_url.rstrip("/") + "/fr/login",
        headers={"User-Agent": "EZScore-Server-Control/1"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return 200 <= int(response.status) < 500
    except urllib.error.HTTPError as exc:
        return 400 <= int(exc.code) < 500
    except Exception:
        return False

def gateway_alive(base_url: str, timeout: float = 1.0) -> bool:
    req = urllib.request.Request(
        base_url.rstrip("/") + "/__ezscore_gateway_health",
        headers={"User-Agent": "EZScore-Server-Control/1"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return int(response.status) == 200
    except Exception:
        return False



def gateway_runtime_status(base_url: str, timeout: float = 1.0) -> dict | None:
    req = urllib.request.Request(
        base_url.rstrip("/") + "/__ezscore_gateway_status",
        headers={"User-Agent": "EZScore-Server-Control/1"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if int(response.status) != 200:
                return None
            payload = json.loads(response.read().decode("utf-8"))
            return payload if isinstance(payload, dict) else None
    except Exception:
        return None


class ServerController:
    DEFAULT_STATE = {
        "schema_version": STATE_SCHEMA,
        "online": {"running": True, "maintenance": False, "env": "prod"},
        "local": {"running": False, "env": "dev"},
        "worker": {"target": "online"},
    }

    def __init__(self, root: Path, event_sink: Callable[[tuple[str, object]], None] | None = None):
        self.root = Path(root).resolve()
        self.runtime = self.root / "var" / "runtime"
        self.logs = self.root / "var" / "log"
        self.state_path = self.runtime / "ezscore-server-control.json"
        self.gateway_config_path = self.runtime / "online-gateway.json"
        self.online_gateway_pid = self.runtime / "ezscore-online-gateway.pid"
        self.online_backend_pid = self.runtime / "ezscore-web-online.pid"
        self.local_pid = self.runtime / "ezscore-web-local.pid"
        self._state_lock = threading.RLock()
        self._online_lock = threading.RLock()
        self._local_lock = threading.RLock()
        self._event_sink = event_sink
        self.runtime.mkdir(parents=True, exist_ok=True)
        self.logs.mkdir(parents=True, exist_ok=True)
        self.state = self._load_state()
        self._write_gateway_config(self.state["online"]["maintenance"])

    def _emit(self, kind: str, payload: object) -> None:
        if self._event_sink:
            self._event_sink((kind, payload))

    def log(self, message: str) -> None:
        self._emit("log", f"[SERVER] {message}")

    def _load_state(self) -> dict:
        data = _read_json(self.state_path, self.DEFAULT_STATE)
        online = data.get("online") if isinstance(data.get("online"), dict) else {}
        local = data.get("local") if isinstance(data.get("local"), dict) else {}
        worker = data.get("worker") if isinstance(data.get("worker"), dict) else {}
        env = str(online.get("env", "prod")).lower()
        target = str(worker.get("target", "online")).lower()
        state = {
            "schema_version": STATE_SCHEMA,
            "online": {
                "running": bool(online.get("running", True)),
                "maintenance": bool(online.get("maintenance", False)),
                "env": env if env in {"prod", "dev"} else "prod",
            },
            "local": {"running": bool(local.get("running", False)), "env": "dev"},
            "worker": {"target": target if target in {"online", "local"} else "online"},
        }
        _atomic_json(self.state_path, state)
        return state

    def save(self) -> None:
        with self._state_lock:
            _atomic_json(self.state_path, self.state)

    def snapshot_desired(self) -> dict:
        with self._state_lock:
            return json.loads(json.dumps(self.state))

    def public_url(self) -> str:
        env = self._read_env_local()
        return (os.environ.get("EZSCORE_BROWSER_URL") or env.get("EZSCORE_BROWSER_URL") or "https://ezscore.logandplay.com").rstrip("/")

    def online_url(self) -> str:
        return f"http://127.0.0.1:{ONLINE_GATEWAY_PORT}"

    def online_backend_url(self) -> str:
        return f"http://127.0.0.1:{ONLINE_BACKEND_PORT}"

    def local_url(self) -> str:
        return f"http://127.0.0.1:{LOCAL_DEV_PORT}"

    def worker_url(self) -> str:
        desired = self.snapshot_desired()
        return self.local_url() if desired["worker"]["target"] == "local" else self.online_url()

    def _read_env_local(self) -> dict[str, str]:
        result: dict[str, str] = {}
        path = self.root / ".env.local"
        if not path.is_file():
            return result
        for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            result[key.strip()] = value
        return result

    def _write_gateway_config(self, maintenance: bool) -> None:
        _atomic_json(self.gateway_config_path, {
            "schema_version": "ezscore.online-gateway.v1",
            "maintenance": bool(maintenance),
            "backend_host": "127.0.0.1",
            "backend_port": ONLINE_BACKEND_PORT,
            "public_url": self.public_url(),
        })

    def _start_gateway(self) -> None:
        pid = _read_pid(self.online_gateway_pid)
        if pid and _pid_alive(pid) and gateway_alive(self.online_url(), timeout=0.6):
            runtime = gateway_runtime_status(self.online_url(), timeout=0.6)
            if isinstance(runtime, dict) and runtime.get("protocol") == GATEWAY_PROTOCOL:
                return
            self.log("Passerelle ONLINE obsolète détectée : relance automatique.")
            if not _stop_pid(self.online_gateway_pid, timeout=5.0):
                raise RuntimeError("Impossible d'arrêter l'ancienne passerelle ONLINE.")

        self.online_gateway_pid.unlink(missing_ok=True)
        gateway = self.root / "worker_app" / "online_gateway.py"
        out = (self.logs / "online-gateway.out.log").open("ab")
        err = (self.logs / "online-gateway.err.log").open("ab")
        try:
            proc = subprocess.Popen(
                [sys.executable, str(gateway), "--root", str(self.root), "--port", str(ONLINE_GATEWAY_PORT)],
                cwd=str(self.root),
                stdout=out,
                stderr=err,
                creationflags=WINDOWS_NO_WINDOW if os.name == "nt" else 0,
            )
        finally:
            out.close()
            err.close()

        self.online_gateway_pid.write_text(str(proc.pid), encoding="ascii")
        deadline = time.monotonic() + 8.0
        while time.monotonic() < deadline:
            runtime = gateway_runtime_status(self.online_url(), timeout=0.5)
            if isinstance(runtime, dict) and runtime.get("protocol") == GATEWAY_PROTOCOL:
                return
            if proc.poll() is not None:
                break
            time.sleep(0.15)
        raise RuntimeError("La passerelle ONLINE R40.0I ne répond pas sur 127.0.0.1:8501.")

    def _instance_meta(self, instance: str) -> dict:
        return _read_json(self.runtime / f"ezscore-web-{instance}.json", {})

    def _run_web_script(self, instance: str, env: str) -> None:
        script = self.root / "scripts" / "start_ezscore_web.ps1"
        cmd = [
            "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
            "-File", str(script), "-Instance", instance, "-Environment", env,
        ]
        proc = subprocess.Popen(
            cmd,
            cwd=str(self.root),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            creationflags=WINDOWS_NO_WINDOW if os.name == "nt" else 0,
        )
        output: queue.Queue[str | None] = queue.Queue()

        def reader() -> None:
            try:
                if proc.stdout is not None:
                    for line in proc.stdout:
                        output.put(line.rstrip())
            finally:
                output.put(None)

        threading.Thread(target=reader, daemon=True).start()
        deadline = time.monotonic() + WEB_SCRIPT_TIMEOUT_SECONDS
        timed_out = False

        while proc.poll() is None:
            while True:
                try:
                    line = output.get_nowait()
                except queue.Empty:
                    break
                if line:
                    self.log(line)
            if time.monotonic() >= deadline:
                timed_out = True
                proc.kill()
                break
            time.sleep(0.05)

        try:
            proc.wait(timeout=2.0)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=2.0)

        while True:
            try:
                line = output.get_nowait()
            except queue.Empty:
                break
            if line:
                self.log(line)

        if timed_out:
            raise RuntimeError(
                f"Démarrage {instance}: script PowerShell bloqué plus de "
                f"{int(WEB_SCRIPT_TIMEOUT_SECONDS)} s."
            )
        if proc.returncode != 0:
            raise RuntimeError(f"Démarrage {instance} impossible (code {proc.returncode}).")

    def _wait_health(self, url: str, seconds: float = 12.0) -> None:
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if http_alive(url, timeout=0.7):
                return
            time.sleep(0.25)
        raise RuntimeError(f"Health check en échec: {url}/fr/login")

    def start_online(self) -> None:
        with self._online_lock:
            desired = self.snapshot_desired()
            env = desired["online"]["env"]
            maintenance = bool(desired["online"]["maintenance"])
            self._write_gateway_config(True)
            self._start_gateway()
            try:
                self._run_web_script("online", env)
                self._wait_health(self.online_backend_url())
            except Exception:
                self._write_gateway_config(True)
                raise
            with self._state_lock:
                self.state["online"]["running"] = True
                self.save()
            self._write_gateway_config(maintenance)
            self.log(f"ONLINE démarré · env={env} · public=:8501 · backend=:{ONLINE_BACKEND_PORT}")

    def stop_online(self) -> None:
        with self._online_lock:
            self._write_gateway_config(True)
            if not _stop_pid(self.online_backend_pid):
                raise RuntimeError("Le backend ONLINE ne s'est pas arrêté.")
            if not _stop_pid(self.online_gateway_pid):
                raise RuntimeError("La passerelle ONLINE ne s'est pas arrêtée.")
            with self._state_lock:
                self.state["online"]["running"] = False
                self.save()
            self.log("ONLINE arrêté.")

    def restart_online(self, env: str | None = None) -> None:
        with self._online_lock:
            desired = self.snapshot_desired()
            new_env = (env or desired["online"]["env"]).lower()
            if new_env not in {"prod", "dev"}:
                raise ValueError("Environnement ONLINE invalide.")
            was_running = bool(desired["online"]["running"])
            previous_maintenance = bool(desired["online"]["maintenance"])
            with self._state_lock:
                self.state["online"]["env"] = new_env
                self.save()
            if not was_running:
                self.log(f"Env ONLINE mémorisé: {new_env} (serveur arrêté).")
                return
            self._write_gateway_config(True)
            self._start_gateway()
            if not _stop_pid(self.online_backend_pid):
                raise RuntimeError("Le backend ONLINE ne s'est pas arrêté avant relance.")
            try:
                self._run_web_script("online", new_env)
                self._wait_health(self.online_backend_url())
            except Exception:
                self._write_gateway_config(True)
                raise
            self._write_gateway_config(previous_maintenance)
            self.log(f"ONLINE relancé automatiquement · env={new_env}.")

    def set_online_environment(self, env: str) -> None:
        self.restart_online(env=env)

    def set_maintenance(self, value: bool) -> None:
        with self._online_lock:
            requested = bool(value)
            desired = self.snapshot_desired()
            previous = bool(desired["online"]["maintenance"])
            self._write_gateway_config(requested)
            if bool(desired["online"]["running"]):
                deadline = time.monotonic() + 3.0
                observed = None
                while time.monotonic() < deadline:
                    runtime = gateway_runtime_status(self.online_url(), timeout=0.6)
                    if runtime is not None:
                        observed = bool(runtime.get("maintenance", False))
                        if observed == requested:
                            break
                    time.sleep(0.1)
                if observed != requested:
                    self._write_gateway_config(previous)
                    raise RuntimeError("La passerelle ONLINE n'a pas confirmé le nouvel état maintenance.")
            with self._state_lock:
                self.state["online"]["maintenance"] = requested
                self.save()
            self.log("Maintenance ONLINE activée." if requested else "Maintenance ONLINE désactivée.")

    def start_local(self) -> None:
        with self._local_lock:
            self._run_web_script("local", "dev")
            self._wait_health(self.local_url())
            with self._state_lock:
                self.state["local"]["running"] = True
                self.state["local"]["env"] = "dev"
                self.save()
            self.log(f"LOCAL DEV démarré · 127.0.0.1:{LOCAL_DEV_PORT}.")

    def stop_local(self) -> None:
        with self._local_lock:
            if not _stop_pid(self.local_pid):
                raise RuntimeError("Le serveur LOCAL ne s'est pas arrêté.")
            with self._state_lock:
                self.state["local"]["running"] = False
                self.save()
            self.log("LOCAL DEV arrêté.")

    def restart_local(self) -> None:
        with self._local_lock:
            desired = self.snapshot_desired()
            if bool(desired["local"]["running"]):
                if not _stop_pid(self.local_pid):
                    raise RuntimeError("Le serveur LOCAL ne s'est pas arrêté avant relance.")
            self._run_web_script("local", "dev")
            self._wait_health(self.local_url())
            with self._state_lock:
                self.state["local"]["running"] = True
                self.state["local"]["env"] = "dev"
                self.save()
            self.log("LOCAL DEV relancé." if desired["local"]["running"] else "LOCAL DEV démarré.")

    def set_worker_target(self, target: str) -> None:
        target = target.lower()
        if target not in {"online", "local"}:
            raise ValueError("Cible Worker invalide.")
        with self._state_lock:
            self.state["worker"]["target"] = target
            self.save()
        self.log(f"Cible Worker mémorisée: {target.upper()}.")

    def restore_desired(self) -> None:
        desired = self.snapshot_desired()
        self.log("Restauration des modes persistés…")
        legacy_pid_file = self.runtime / "ezscore-web.pid"
        if legacy_pid_file.is_file():
            legacy_pid = _read_pid(legacy_pid_file)
            if legacy_pid and _pid_alive(legacy_pid):
                self.log(f"Migration du serveur R39 : arrêt de l'ancien PID {legacy_pid} sur :8501…")
                if not _stop_pid(legacy_pid_file, timeout=8.0):
                    raise RuntimeError("L'ancien serveur R39 sur :8501 ne s'est pas arrêté. STOP.")
            legacy_pid_file.unlink(missing_ok=True)
        if desired["online"]["running"]:
            self._write_gateway_config(True)
            self._start_gateway()
            backend_ok = http_alive(self.online_backend_url(), timeout=0.7)
            backend_meta = self._instance_meta("online")
            backend_env_ok = str(backend_meta.get("environment") or "") == desired["online"]["env"]
            if not backend_ok or not backend_env_ok:
                _stop_pid(self.online_backend_pid, timeout=2.0)
                self._run_web_script("online", desired["online"]["env"])
                self._wait_health(self.online_backend_url())
            self._write_gateway_config(desired["online"]["maintenance"])
        else:
            _stop_pid(self.online_backend_pid, timeout=2.0)
            _stop_pid(self.online_gateway_pid, timeout=2.0)
        if desired["local"]["running"]:
            local_meta = self._instance_meta("local")
            local_env_ok = str(local_meta.get("environment") or "") == "dev"
            if not http_alive(self.local_url(), timeout=0.7) or not local_env_ok:
                _stop_pid(self.local_pid, timeout=2.0)
                self._run_web_script("local", "dev")
                self._wait_health(self.local_url())
        else:
            _stop_pid(self.local_pid, timeout=2.0)
        self.log("Modes persistés restaurés.")

    def status(self) -> dict:
        desired = self.snapshot_desired()
        gateway_pid = _read_pid(self.online_gateway_pid)
        backend_pid = _read_pid(self.online_backend_pid)
        local_pid = _read_pid(self.local_pid)

        # Process state and HTTP health are deliberately separate.
        # A transient HTTP timeout must never make the UI claim that a process stopped.
        gateway_process_alive = bool(gateway_pid and _pid_alive(gateway_pid))
        backend_process_alive = bool(backend_pid and _pid_alive(backend_pid))
        local_process_alive = bool(local_pid and _pid_alive(local_pid))

        gateway_http_healthy = bool(
            gateway_process_alive and gateway_alive(self.online_url(), 1.0)
        )
        backend_http_healthy = bool(
            backend_process_alive and http_alive(self.online_backend_url(), 1.0)
        )
        local_http_healthy = bool(
            local_process_alive and http_alive(self.local_url(), 1.0)
        )

        runtime = (
            gateway_runtime_status(self.online_url(), 1.0)
            if gateway_http_healthy
            else None
        )
        maintenance_observed = (
            bool(runtime.get("maintenance", False))
            if isinstance(runtime, dict)
            else None
        )

        return {
            "desired": desired,
            "online": {
                # Legacy fields kept for compatibility with any existing consumer.
                "gateway_alive": gateway_http_healthy,
                "backend_alive": backend_http_healthy,
                # R41.0G explicit process/health split.
                "gateway_process_alive": gateway_process_alive,
                "backend_process_alive": backend_process_alive,
                "gateway_http_healthy": gateway_http_healthy,
                "backend_http_healthy": backend_http_healthy,
                "gateway_pid": gateway_pid,
                "backend_pid": backend_pid,
                "env": desired["online"]["env"],
                "maintenance": desired["online"]["maintenance"],
                "maintenance_observed": maintenance_observed,
                "public_url": self.public_url(),
            },
            "local": {
                # Legacy field kept for compatibility.
                "alive": local_http_healthy,
                # R41.0G explicit process/health split.
                "process_alive": local_process_alive,
                "http_healthy": local_http_healthy,
                "pid": local_pid,
                "env": "dev",
                "url": self.local_url(),
            },
            "worker": {"target": desired["worker"]["target"], "url": self.worker_url()},
        }

    def open_online(self) -> None:
        webbrowser.open(self.public_url() + "/fr/catalog")

    def open_local(self) -> None:
        webbrowser.open(self.local_url() + "/fr/catalog")
