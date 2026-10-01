#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import queue
import socket
import subprocess
import sys
import threading
import time
import traceback
import urllib.error
import urllib.request
import uuid
import webbrowser
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from server_control import ServerController


APP_VERSION = "R41.0G"
HEARTBEAT_SECONDS = 2.0
CLAIM_SECONDS = 1.5
RECONNECT_MIN_SECONDS = 1.0
RECONNECT_MAX_SECONDS = 15.0

WINDOWS_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def now_text() -> str:
    return datetime.now().strftime("%H:%M:%S")


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def read_env_local(root: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    path = root / ".env.local"
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


def browser_url(root: Path) -> str:
    env = read_env_local(root)
    return (
        os.environ.get("EZSCORE_BROWSER_URL")
        or env.get("EZSCORE_BROWSER_URL")
        or "https://ezscore.logandplay.com"
    ).rstrip("/")


def local_server_url() -> str:
    return "http://127.0.0.1:8501"


def connection_error_summary(exc: Exception) -> tuple[str, str]:
    text = str(exc)
    lowered = text.lower()

    if (
        "getcachewarmerservice.php" in lowered
        or ("var\\cache\\dev\\container" in lowered and "failed to open stream" in lowered)
    ):
        return (
            "symfony_cache",
            "Cache Symfony incohérent — redémarrage propre du serveur requis."
        )

    if "timed out" in lowered or "timeout" in lowered:
        return ("timeout", "Serveur EZScore temporairement indisponible (timeout).")

    if "connection refused" in lowered or "actively refused" in lowered:
        return ("offline", "Serveur EZScore arrêté ou en cours de redémarrage.")

    if "http 5" in lowered:
        return ("http_5xx", "Serveur EZScore en erreur HTTP 5xx.")

    line = " ".join(text.replace("\r", " ").replace("\n", " ").split())
    return ("network", line[:220] or exc.__class__.__name__)


def local_server_pid(root: Path) -> int | None:
    path = root / "var" / "runtime" / "ezscore-web.pid"
    try:
        value = int(path.read_text(encoding="ascii", errors="ignore").strip())
        return value if value > 0 else None
    except Exception:
        return None


def local_server_alive(timeout: float = 0.8) -> tuple[bool, int | None]:
    root = project_root()
    pid = local_server_pid(root)

    req = urllib.request.Request(
        local_server_url() + "/fr/login",
        headers={"User-Agent": f"EZScore-Analysis-Worker/{APP_VERSION}"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return 200 <= int(response.status) < 500, pid
    except urllib.error.HTTPError as exc:
        # HTTP 4xx proves that the local HTTP server is alive.
        return 400 <= int(exc.code) < 500, pid
    except Exception:
        return False, pid


class ApiClient:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip("/")
        self.token = token

    def request(self, method: str, path: str, payload: dict | None = None, timeout: float = 20.0):
        data = None
        headers = {
            "Accept": "application/json",
            "X-EZScore-Analysis-Token": self.token,
            "User-Agent": f"EZScore-Analysis-Worker/{APP_VERSION}",
        }
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        req = urllib.request.Request(
            self.base_url + path,
            data=data,
            headers=headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                body = response.read()
                if response.status == 204:
                    return None
                if not body:
                    return {}
                return json.loads(body.decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {exc.code} {path}: {body[:500]}") from exc

    def post(self, path: str, payload: dict | None = None, timeout: float = 20.0):
        return self.request("POST", path, payload or {}, timeout)

    def get(self, path: str, timeout: float = 20.0):
        return self.request("GET", path, None, timeout)


class WorkerEngine:
    def __init__(self, app: "WorkerWindow"):
        self.app = app
        self.root = project_root()
        self.worker_id = f"{socket.gethostname()}-{uuid.uuid4().hex[:8]}"
        self.api: ApiClient | None = None
        self.running = False
        self.paused = False
        self.stop_event = threading.Event()
        self.thread: threading.Thread | None = None
        self.current_process: subprocess.Popen | None = None
        self.current_job: dict | None = None
        self.engine_python: str | None = None
        self.capabilities: dict = {}

    def log(self, message: str) -> None:
        line = f"[{now_text()}] {message}"
        self.app.events.put(("log", line))
        log_dir = self.root / "var" / "log"
        log_dir.mkdir(parents=True, exist_ok=True)
        with (log_dir / "analysis-worker-desktop.log").open("a", encoding="utf-8", errors="replace") as fh:
            fh.write(line + "\n")

    def discover_python(self) -> tuple[str | None, dict]:
        env = read_env_local(self.root)
        candidates: list[str] = []
        for candidate in [
            os.environ.get("EZSCORE_STEM_PYTHON"),
            env.get("EZSCORE_STEM_PYTHON"),
            str(self.root / ".venv-py313" / "Scripts" / "python.exe"),
            sys.executable,
            "python",
        ]:
            if candidate and candidate not in candidates:
                candidates.append(candidate)

        probe = (
            "import json,torch,bs_roformer,mel_band_roformer,lv_chordia;"
            "print(json.dumps({"
            "'python':__import__('sys').executable,"
            "'torch':torch.__version__,"
            "'cuda':bool(torch.cuda.is_available()),"
            "'gpu':torch.cuda.get_device_name(0) if torch.cuda.is_available() else None"
            "}))"
        )

        failures = []
        for candidate in candidates:
            try:
                proc = subprocess.run(
                    [candidate, "-c", probe],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=60,
                    check=False,
                    creationflags=WINDOWS_NO_WINDOW if os.name == "nt" else 0,
                )
                if proc.returncode != 0:
                    failures.append(f"{candidate}: {proc.stderr.strip()[-250:]}")
                    continue
                data = json.loads(proc.stdout.strip().splitlines()[-1])
                data["bs_roformer"] = True
                data["mel_band_roformer"] = True
                data["lv_chordia"] = True
                return str(data["python"]), data
            except Exception as exc:
                failures.append(f"{candidate}: {exc}")

        return None, {"errors": failures[-5:]}

    def configure(self) -> None:
        env = read_env_local(self.root)
        controller = getattr(self.app, "server_control", None)
        base_url = controller.worker_url() if controller is not None else (
            os.environ.get("EZSCORE_WORKER_URL")
            or env.get("EZSCORE_WORKER_URL")
            or "http://127.0.0.1:8501"
        )
        token = os.environ.get("ANALYSIS_WORKER_TOKEN") or env.get("ANALYSIS_WORKER_TOKEN") or ""
        if not token:
            raise RuntimeError("ANALYSIS_WORKER_TOKEN absent de .env.local.")

        self.api = ApiClient(base_url, token)
        self.engine_python, self.capabilities = self.discover_python()
        self.capabilities["ffmpeg"] = bool(self._which("ffmpeg"))
        self.capabilities["project"] = str(self.root)
        self.capabilities["protocol"] = "ezscore.worker.desktop.v1"

        self.app.events.put(("connection_config", {
            "url": base_url,
            "python": self.engine_python or "INTRouvable",
            "capabilities": self.capabilities,
        }))

        if not self.engine_python:
            errors = self.capabilities.get("errors") or []
            detail = " | ".join(str(item) for item in errors[-5:]) or "aucun détail disponible"
            raise RuntimeError(
                "Aucun Python compatible trouvé. "
                "Requis: bs_roformer + mel_band_roformer + lv-chordia + CUDA. "
                f"Diagnostics: {detail}"
            )
        if not self.capabilities.get("cuda"):
            raise RuntimeError("CUDA n'est pas disponible dans le Python STEM sélectionné.")
        if not self.capabilities.get("ffmpeg"):
            raise RuntimeError("FFmpeg introuvable dans PATH.")

    def _which(self, name: str) -> str | None:
        import shutil
        return shutil.which(name)

    def start(self) -> None:
        if self.running or (self.thread is not None and self.thread.is_alive()):
            return
        self.stop_event.clear()
        self.running = True
        self.thread = threading.Thread(target=self._loop, name="worker-loop", daemon=True)
        self.thread.start()

    def request_stop(self) -> None:
        self.stop_event.set()

    def stop_and_wait(self, timeout: float = 30.0) -> bool:
        if self.current_job is not None:
            return False
        self.request_stop()
        thread = self.thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=timeout)
        if thread is not None and thread.is_alive():
            return False
        self.thread = None
        self.running = False
        return True

    def restart(self) -> bool:
        if self.current_job is not None:
            return False
        if not self.stop_and_wait():
            return False
        self.start()
        return True

    def pause(self, value: bool = True) -> None:
        self.paused = value
        self.app.events.put(("status", "PAUSE" if value else "RUNNING"))

    def cancel_current(self) -> None:
        proc = self.current_process
        if proc and proc.poll() is None:
            self.log("Annulation demandée pour le processus Python courant.")
            try:
                proc.terminate()
            except Exception:
                pass

    def _heartbeat_payload(self, status: str) -> dict:
        return {
            "worker_id": self.worker_id,
            "version": APP_VERSION,
            "status": status,
            "capabilities": self.capabilities,
            "current_job": self.current_job,
        }

    def _send_heartbeat(self, status: str) -> None:
        assert self.api is not None
        response = self.api.post("/internal/analysis/desktop/heartbeat", self._heartbeat_payload(status))
        self.app.events.put(("txrx", "RX/TX OK"))
        for command in (response or {}).get("commands", []):
            self._handle_command(command)

    def _handle_command(self, item: dict) -> None:
        command = str(item.get("command", "")).strip()
        command_id = str(item.get("id", "")).strip()
        self.log(f"Commande EZScore reçue: {command}")

        if command == "pause":
            self.pause(True)
        elif command == "resume":
            self.pause(False)
        elif command == "cancel_current":
            self.cancel_current()
        elif command == "shutdown":
            self.request_stop()
        elif command == "reload":
            self.log("Commande reload reçue; les capacités seront revalidées au prochain démarrage.")

        if command_id and self.api:
            try:
                self.api.post(f"/internal/analysis/desktop/commands/{command_id}/ack", {})
            except Exception as exc:
                self.log(f"ACK commande impossible: {exc}")

    def _loop(self) -> None:
        try:
            self.configure()
            assert self.api is not None

            connected = False
            reconnect_delay = RECONNECT_MIN_SECONDS
            next_connect_attempt = 0.0
            last_connection_error_kind = None
            last_connection_error_log = 0.0
            last_heartbeat = 0.0
            last_claim = 0.0
            last_queue_refresh = 0.0

            while not self.stop_event.is_set():
                now = time.monotonic()

                if not connected:
                    desired = self.app.server_control.snapshot_desired()
                    target = desired["worker"]["target"]
                    if not bool(desired[target]["running"]):
                        self.app.events.put(("status", "ATTENTE SERVEUR"))
                        self.app.events.put(("txrx", "Serveur cible arrêté"))
                        time.sleep(0.35)
                        continue
                    if now < next_connect_attempt:
                        time.sleep(0.15)
                        continue

                    try:
                        hello = self.api.post(
                            "/internal/analysis/desktop/hello",
                            self._heartbeat_payload("starting"),
                            timeout=6,
                        )
                        connected = True
                        reconnect_delay = RECONNECT_MIN_SECONDS
                        next_connect_attempt = 0.0
                        self.app.events.put(("status", "CONNECTÉ"))
                        self.app.events.put(("txrx", "RX/TX OK"))
                        self.log(f"Connexion EZScore établie. worker_id={self.worker_id}")
                        for command in (hello or {}).get("commands", []):
                            self._handle_command(command)
                        last_connection_error_kind = None
                        last_heartbeat = 0.0
                        last_queue_refresh = 0.0
                        last_claim = 0.0
                    except Exception as exc:
                        kind, summary = connection_error_summary(exc)
                        self.app.events.put(("status", "RECONNEXION"))
                        self.app.events.put(("txrx", "HTTP indisponible"))
                        if (
                            kind != last_connection_error_kind
                            or now - last_connection_error_log >= 15.0
                        ):
                            self.log(summary)
                            last_connection_error_kind = kind
                            last_connection_error_log = now
                        next_connect_attempt = now + reconnect_delay
                        reconnect_delay = min(
                            RECONNECT_MAX_SECONDS,
                            max(RECONNECT_MIN_SECONDS, reconnect_delay * 1.7),
                        )
                        time.sleep(0.15)
                        continue

                if now - last_heartbeat >= HEARTBEAT_SECONDS:
                    try:
                        self._send_heartbeat(
                            "paused" if self.paused else ("busy" if self.current_job else "idle")
                        )
                        last_heartbeat = now
                    except Exception as exc:
                        kind, summary = connection_error_summary(exc)
                        self.log(summary)
                        self.app.events.put(("status", "RECONNEXION"))
                        self.app.events.put(("txrx", "HTTP indisponible"))
                        connected = False
                        last_connection_error_kind = kind
                        last_connection_error_log = now
                        next_connect_attempt = now + RECONNECT_MIN_SECONDS
                        reconnect_delay = RECONNECT_MIN_SECONDS
                        time.sleep(0.15)
                        continue

                if now - last_queue_refresh >= 2.0:
                    try:
                        queue_state = self.api.get(
                            "/internal/analysis/desktop/jobs/queue",
                            timeout=10,
                        )
                        self.app.events.put(("queue", (queue_state or {}).get("jobs", [])))
                    except Exception as exc:
                        kind, summary = connection_error_summary(exc)
                        if kind == "symfony_cache":
                            self.log(summary)
                            connected = False
                            self.app.events.put(("status", "RECONNEXION"))
                            self.app.events.put(("txrx", "HTTP indisponible"))
                            next_connect_attempt = now + RECONNECT_MIN_SECONDS
                        elif now - last_connection_error_log >= 15.0:
                            self.log(f"Lecture file d'attente impossible: {summary}")
                            last_connection_error_log = now
                    last_queue_refresh = now

                if (
                    connected
                    and not self.paused
                    and self.current_job is None
                    and now - last_claim >= CLAIM_SECONDS
                ):
                    try:
                        job = self.api.post(
                            "/internal/analysis/desktop/jobs/claim",
                            {},
                            timeout=10,
                        )
                        last_claim = now
                        if job:
                            self._run_job(job)
                    except Exception as exc:
                        kind, summary = connection_error_summary(exc)
                        self.log(f"Prise de job impossible: {summary}")
                        connected = False
                        self.app.events.put(("status", "RECONNEXION"))
                        self.app.events.put(("txrx", "HTTP indisponible"))
                        next_connect_attempt = now + RECONNECT_MIN_SECONDS
                        reconnect_delay = RECONNECT_MIN_SECONDS

                time.sleep(0.15)

        except Exception as exc:
            self.log(f"ERREUR WORKER: {exc}")
            self.log(traceback.format_exc())
            self.app.events.put(("status", "ERREUR"))
            self.app.events.put(("error", str(exc)))
        finally:
            self.current_job = None
            self.current_process = None
            self.running = False

    def _run_job(self, job: dict) -> None:
        assert self.api is not None
        assert self.engine_python is not None

        if job.get("kind") == "chords":
            self._run_chord_job(job)
            return

        if job.get("kind") == "lyrics":
            from lyrics_worker_r37 import run_lyrics_job
            run_lyrics_job(self, job)
            return

        if job.get("kind") != "stems":
            self.log(f"Job #{job.get('job_id')} ignoré: kind={job.get('kind')}")
            self.api.post(f"/internal/analysis/desktop/jobs/{job['job_id']}/fail", {"error": "unsupported_job_kind"})
            return

        job_id = int(job["job_id"])
        song = job.get("song") or {}
        paths = job.get("paths") or {}
        request = job.get("request") or {}

        self.current_job = {
            "job_id": job_id,
            "song_id": job.get("song_id"),
            "kind": "stems",
            "title": song.get("title"),
            "artist": song.get("artist"),
            "progress": 1,
        }
        self.app.events.put(("job", self.current_job.copy()))
        self.log(f"Job #{job_id} pris: {song.get('artist')} — {song.get('title')}")

        command = [
            self.engine_python,
            str(self.root / "analysis" / "stems_only.py"),
            "--source", str(paths["source"]),
            "--audio-hash", str(request.get("audio_sha256") or ""),
            "--storage-root", str(paths["storage_root"]),
            "--progress-file", str(paths["progress_file"]),
        ]
        if bool(request.get("force")):
            command.append("--force")

        env = os.environ.copy()
        env.setdefault("BS_ROFORMER_MODELS_PATH", r"H:\EZScoreModels\bs-roformer")
        env.setdefault("MELBAND_ROFORMER_MODELS_PATH", r"H:\EZScoreModels\melband-roformer")
        env.setdefault("EZSCORE_RUNTIME_TMP", r"H:\Temp\EZScore")
        env.setdefault("EZSCORE_STEM_DEVICE", "cuda:0")
        env["PYTHONUTF8"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"

        self.log("Python: " + self.engine_python)
        self.log("Commande STEMS lancée.")

        proc = subprocess.Popen(
            command,
            cwd=str(self.root),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            creationflags=WINDOWS_NO_WINDOW if os.name == "nt" else 0,
        )
        self.current_process = proc

        process_output: queue.Queue[str | None] = queue.Queue()

        def _read_process_output() -> None:
            if proc.stdout is None:
                process_output.put(None)
                return
            try:
                for line in proc.stdout:
                    process_output.put(line.rstrip())
            finally:
                process_output.put(None)

        threading.Thread(target=_read_process_output, daemon=True).start()

        progress_path = Path(str(paths["progress_file"]))
        stem_log_path = Path(str(paths["log_file"]))

        try:
            progress_path.unlink(missing_ok=True)
        except Exception:
            pass

        last_progress = -1
        last_log_size = stem_log_path.stat().st_size if stem_log_path.is_file() else 0
        last_db_update = 0.0
        last_job_heartbeat = 0.0

        while proc.poll() is None:
            if self.stop_event.is_set():
                proc.terminate()
                break

            while True:
                try:
                    line = process_output.get_nowait()
                except queue.Empty:
                    break
                if line:
                    self.log(line)

            if stem_log_path.is_file():
                try:
                    with stem_log_path.open("r", encoding="utf-8", errors="replace") as fh:
                        fh.seek(last_log_size)
                        chunk = fh.read()
                        last_log_size = fh.tell()
                    if chunk:
                        for line in chunk.splitlines():
                            self.app.events.put(("engine_log", line))
                except Exception:
                    pass

            progress = self._read_progress(progress_path)
            if progress:
                pct = int(progress.get("percent", 0))
                self.current_job["progress"] = pct
                self.current_job["stage"] = progress.get("stage")
                self.current_job["message"] = progress.get("message")
                self.app.events.put(("progress", progress))

                now = time.monotonic()
                if pct != last_progress and now - last_db_update >= 0.8:
                    try:
                        self.api.post(
                            f"/internal/analysis/desktop/jobs/{job_id}/progress",
                            {"progress": pct},
                            timeout=10,
                        )
                    except Exception as exc:
                        self.log(f"Progression API non publiée: {exc}")
                    last_progress = pct
                    last_db_update = now

            now = time.monotonic()
            if now - last_job_heartbeat >= HEARTBEAT_SECONDS:
                try:
                    self._send_heartbeat("busy")
                except Exception as exc:
                    self.log(f"Heartbeat pendant job impossible: {exc}")
                last_job_heartbeat = now

            time.sleep(0.35)

        return_code = proc.wait()
        self.current_process = None

        # R27.2 PLAYBACK PROXY STAGE
        # Desktop Worker executes stems_only.py directly and bypasses
        # App\Service\SongStemWorker. Build Opus proxies here before complete.
        proxy_error = None

        if return_code == 0:
            proxy_script = self.root / "analysis" / "build_playback_proxies.py"

            if not proxy_script.is_file():
                return_code = 90
                proxy_error = "playback_proxy_builder_missing"
                self.log("ERREUR: build_playback_proxies.py introuvable.")
            else:
                proxy_command = [
                    self.engine_python,
                    str(proxy_script),
                    "--source", str(paths["source"]),
                    "--storage-root", str(paths["storage_root"]),
                    "--progress-file", str(paths["progress_file"]),
                ]

                self.log("Génération des proxies Opus 192 kb/s lancée.")

                proxy_proc = subprocess.Popen(
                    proxy_command,
                    cwd=str(self.root),
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    bufsize=1,
                    creationflags=WINDOWS_NO_WINDOW if os.name == "nt" else 0,
                )
                self.current_process = proxy_proc

                if proxy_proc.stdout is not None:
                    for line in proxy_proc.stdout:
                        line = line.rstrip()
                        if line:
                            self.log("[OPUS] " + line)

                proxy_return_code = proxy_proc.wait()
                self.current_process = None

                if proxy_return_code != 0:
                    return_code = proxy_return_code
                    proxy_error = f"playback_proxy_exit_{proxy_return_code}"
                    self.log(f"Échec génération Opus: {proxy_error}")
                else:
                    self.log("Proxies Opus générés.")

        if return_code == 0:
            try:
                self.api.post(f"/internal/analysis/desktop/jobs/{job_id}/complete", {})
                self.log(f"Job #{job_id} terminé.")
                self.app.events.put(("progress", {"percent": 100, "stage": "complete", "message": "Terminé"}))
            except Exception as exc:
                self.log(f"Échec validation finale job #{job_id}: {exc}")
                self.api.post(f"/internal/analysis/desktop/jobs/{job_id}/fail", {"error": str(exc)[:400]})
        else:
            error = proxy_error or f"stems_python_exit_{return_code}"
            self.log(f"Job #{job_id} en échec: {error}")
            try:
                self.api.post(f"/internal/analysis/desktop/jobs/{job_id}/fail", {"error": error})
            except Exception as exc:
                self.log(f"Impossible de publier l'échec: {exc}")

        self.current_job = None
        self.app.events.put(("job", None))


    def _run_chord_job(self, job: dict) -> None:
        assert self.api is not None
        assert self.engine_python is not None

        job_id = int(job["job_id"])
        song = job.get("song") or {}
        paths = job.get("paths") or {}
        request = job.get("request") or {}

        self.current_job = {
            "job_id": job_id,
            "song_id": job.get("song_id"),
            "kind": "chords",
            "title": song.get("title"),
            "artist": song.get("artist"),
            "progress": 1,
            "stage": "queued",
        }
        self.app.events.put(("job", self.current_job.copy()))
        self.log(f"Job accords #{job_id} pris: {song.get('artist')} — {song.get('title')}")

        command = [
            self.engine_python,
            str(self.root / "analysis" / "chord_timeline_analysis.py"),
            "--audio", str(paths["source"]),
            "--level", str(request.get("level") or "intermediate"),
            "--time-signature", str(request.get("time_signature") or "auto"),
            "--progress-file", str(paths["progress_file"]),
            "--output", str(paths["result_file"]),
        ]
        for stem_path in (paths.get("harmony_stems") or []):
            if stem_path:
                command.extend(["--stem", str(stem_path)])
        if paths.get("drums"):
            command.extend(["--drums", str(paths["drums"])])
        if bool(request.get("filter_noise")):
            command.append("--filter-noise")

        progress_path = Path(str(paths["progress_file"]))
        result_path = Path(str(paths["result_file"]))
        progress_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            progress_path.unlink(missing_ok=True)
            result_path.unlink(missing_ok=True)
        except Exception:
            pass

        env = os.environ.copy()
        env["PYTHONUTF8"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        self.log("Commande CHORDS lancée.")

        proc = subprocess.Popen(
            command,
            cwd=str(self.root),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            creationflags=WINDOWS_NO_WINDOW if os.name == "nt" else 0,
        )
        self.current_process = proc

        output_queue: queue.Queue[str | None] = queue.Queue()
        def _reader() -> None:
            if proc.stdout is None:
                output_queue.put(None)
                return
            try:
                for line in proc.stdout:
                    output_queue.put(line.rstrip())
            finally:
                output_queue.put(None)
        threading.Thread(target=_reader, daemon=True).start()

        last_progress = -1
        last_db_update = 0.0
        last_job_heartbeat = 0.0

        while proc.poll() is None:
            if self.stop_event.is_set():
                proc.terminate()
                break

            while True:
                try:
                    line = output_queue.get_nowait()
                except queue.Empty:
                    break
                if line:
                    self.log("[CHORDS] " + line)

            current = self._read_progress(progress_path)
            if current:
                pct = int(current.get("percent", 0))
                self.current_job["progress"] = pct
                self.current_job["stage"] = current.get("stage")
                self.current_job["message"] = current.get("message")
                self.app.events.put(("progress", current))
                now = time.monotonic()
                if pct != last_progress and now - last_db_update >= 0.5:
                    try:
                        self.api.post(
                            f"/internal/analysis/desktop/jobs/{job_id}/progress",
                            {"progress": pct},
                            timeout=10,
                        )
                    except Exception as exc:
                        self.log(f"Progression accords non publiée: {exc}")
                    last_progress = pct
                    last_db_update = now

            now = time.monotonic()
            if now - last_job_heartbeat >= HEARTBEAT_SECONDS:
                try:
                    self._send_heartbeat("busy")
                except Exception as exc:
                    self.log(f"Heartbeat accords impossible: {exc}")
                last_job_heartbeat = now

            time.sleep(0.25)

        return_code = proc.wait()
        self.current_process = None

        if return_code == 0 and result_path.is_file():
            try:
                self.api.post(f"/internal/analysis/desktop/jobs/{job_id}/complete", {}, timeout=20)
                self.log(f"Job accords #{job_id} terminé.")
                self.app.events.put(("progress", {"percent": 100, "stage": "complete", "message": "Accords terminés"}))
            except Exception as exc:
                self.log(f"Échec validation accords #{job_id}: {exc}")
                try:
                    self.api.post(f"/internal/analysis/desktop/jobs/{job_id}/fail", {"error": str(exc)[:400]})
                except Exception:
                    pass
        else:
            error = f"chords_python_exit_{return_code}"
            self.log(f"Job accords #{job_id} en échec: {error}")
            try:
                self.api.post(f"/internal/analysis/desktop/jobs/{job_id}/fail", {"error": error})
            except Exception as exc:
                self.log(f"Impossible de publier l'échec accords: {exc}")

        self.current_job = None
        self.app.events.put(("job", None))

    @staticmethod
    def _read_progress(path: Path) -> dict | None:
        try:
            if not path.is_file():
                return None
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else None
        except Exception:
            return None


class ServerStatusMonitor:
    def __init__(self, app: "WorkerWindow"):
        self.app = app
        self.stop_event = threading.Event()
        self.thread: threading.Thread | None = None

    def start(self) -> None:
        if self.thread and self.thread.is_alive():
            return
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._loop, name="server-status-monitor", daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()

    def _loop(self) -> None:
        while not self.stop_event.is_set():
            try:
                self.app.events.put(("server_snapshot", self.app.server_control.status()))
            except Exception as exc:
                self.app.events.put(("log", f"[SERVER] Monitoring impossible: {exc}"))
            self.stop_event.wait(2.0)


class WorkerWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("EZScore Analysis Worker")
        self.root.geometry("1180x860")
        self.root.minsize(980, 720)
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.server_control = ServerController(project_root(), self.events.put)
        self.engine = WorkerEngine(self)

        desired = self.server_control.snapshot_desired()
        self.status_var = tk.StringVar(value="ARRÊTÉ")
        self.url_var = tk.StringVar(value=self.server_control.worker_url())
        self.python_var = tk.StringVar(value="—")
        self.cuda_var = tk.StringVar(value="—")
        self.job_var = tk.StringVar(value="Aucun")
        self.stage_var = tk.StringVar(value="—")
        self.txrx_var = tk.StringVar(value="—")
        self.progress_var = tk.DoubleVar(value=0)

        self.online_summary_var = tk.StringVar(value="Vérification…")
        self.online_detail_var = tk.StringVar(value=self.server_control.public_url())
        self.online_env_var = tk.StringVar(value=desired["online"]["env"])
        self.online_maintenance_var = tk.BooleanVar(value=desired["online"]["maintenance"])
        self.local_summary_var = tk.StringVar(value="Vérification…")
        self.local_detail_var = tk.StringVar(value=self.server_control.local_url())
        self.worker_target_var = tk.StringVar(value=desired["worker"]["target"].upper())
        self.worker_summary_var = tk.StringVar(value=f"Cible {desired['worker']['target'].upper()} · {self.server_control.worker_url()}")
        self.gpu_summary_var = tk.StringVar(value="CUDA : vérification…")
        self.operation_var = tk.StringVar(value="Prêt")
        self._last_snapshot: dict = {}
        self._server_action_running = False

        # R41.0G health hysteresis. Process state is authoritative for
        # ACTIF/ARRÊTÉ; HTTP health only controls secondary/degraded status.
        self._health_state = {
            "online_backend": {"bad": 0, "good": 0, "degraded": False},
            "online_gateway": {"bad": 0, "good": 0, "degraded": False},
            "local_http": {"bad": 0, "good": 0, "degraded": False},
        }

        self._bootstrap_path = project_root() / "var" / "runtime" / "analysis-worker-bootstrap.json"

        self.server_monitor = ServerStatusMonitor(self)
        self._build()
        self.root.after(100, self._drain_events)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.server_monitor.start()

    def _build(self):
        style = ttk.Style()
        try:
            style.theme_use("vista")
        except Exception:
            pass
        style.configure("Title.TLabel", font=("Segoe UI", 19, "bold"))
        style.configure("Sub.TLabel", foreground="#687780")
        style.configure("CardTitle.TLabel", font=("Segoe UI", 11, "bold"))
        style.configure("State.TLabel", font=("Segoe UI", 11, "bold"))
        style.configure("StateGood.TLabel", font=("Segoe UI", 11, "bold"), foreground="#188038")
        style.configure("StateBad.TLabel", font=("Segoe UI", 11, "bold"), foreground="#c62828")
        style.configure("StateWarn.TLabel", font=("Segoe UI", 11, "bold"), foreground="#b06000")
        style.configure("Muted.TLabel", foreground="#687780")
        style.configure("Danger.TButton", foreground="#8b1e1e")

        outer = ttk.Frame(self.root, padding=12)
        outer.pack(fill="both", expand=True)

        header = ttk.Frame(outer)
        header.pack(fill="x", pady=(0, 10))
        left = ttk.Frame(header)
        left.pack(side="left", fill="x", expand=True)
        ttk.Label(left, text="EZScore Analysis Worker", style="Title.TLabel").pack(anchor="w")
        ttk.Label(left, text=f"{APP_VERSION} · Pilotage ONLINE / LOCAL · STEMS + CHORDS + LYRICS", style="Sub.TLabel").pack(anchor="w")
        ttk.Label(header, textvariable=self.operation_var, style="Muted.TLabel").pack(side="right", anchor="e")

        summary = ttk.Frame(outer)
        summary.pack(fill="x", pady=(0, 10))
        for col in range(3):
            summary.columnconfigure(col, weight=1)
        self._summary_card(summary, 0, "ONLINE", self.online_summary_var)
        self._summary_card(summary, 1, "LOCAL DEV", self.local_summary_var)
        self._summary_card(summary, 2, "WORKER", self.worker_summary_var)

        servers = ttk.Frame(outer)
        servers.pack(fill="x", pady=(0, 10))
        servers.columnconfigure(0, weight=1)
        servers.columnconfigure(1, weight=1)

        online = ttk.LabelFrame(servers, text="Serveur ONLINE", padding=12)
        online.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        ttk.Label(online, textvariable=self.online_summary_var, style="State.TLabel").grid(row=0, column=0, columnspan=4, sticky="w")
        ttk.Label(online, textvariable=self.online_detail_var, style="Muted.TLabel").grid(row=1, column=0, columnspan=4, sticky="w", pady=(2, 8))
        ttk.Label(online, text="Environnement").grid(row=2, column=0, sticky="w")
        self.online_env_combo = ttk.Combobox(online, textvariable=self.online_env_var, values=("prod", "dev"), state="readonly", width=9)
        self.online_env_combo.grid(row=2, column=1, sticky="w", padx=(6, 14))
        self.online_env_combo.bind("<<ComboboxSelected>>", self._online_env_changed)
        self.maintenance_check = ttk.Checkbutton(online, text="Maintenance", variable=self.online_maintenance_var, command=self._maintenance_changed)
        self.maintenance_check.grid(row=2, column=2, columnspan=2, sticky="w")
        self.online_start_btn = ttk.Button(online, text="Démarrer", command=lambda: self._server_action("online_start"))
        self.online_restart_btn = ttk.Button(online, text="Relancer", command=lambda: self._server_action("online_restart"))
        self.online_stop_btn = ttk.Button(online, text="Arrêter", command=lambda: self._server_action("online_stop"))
        self.online_open_btn = ttk.Button(online, text="Ouvrir", command=self.server_control.open_online)
        for i, widget in enumerate((self.online_start_btn, self.online_restart_btn, self.online_stop_btn, self.online_open_btn)):
            widget.grid(row=3, column=i, sticky="ew", padx=(0 if i == 0 else 4, 0), pady=(10, 0))
            online.columnconfigure(i, weight=1)

        local = ttk.LabelFrame(servers, text="Serveur LOCAL DEV", padding=12)
        local.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        ttk.Label(local, textvariable=self.local_summary_var, style="State.TLabel").grid(row=0, column=0, columnspan=4, sticky="w")
        ttk.Label(local, textvariable=self.local_detail_var, style="Muted.TLabel").grid(row=1, column=0, columnspan=4, sticky="w", pady=(2, 8))
        ttk.Label(local, text="Environnement").grid(row=2, column=0, sticky="w")
        ttk.Label(local, text="dev", style="State.TLabel").grid(row=2, column=1, sticky="w", padx=(6, 0))
        ttk.Label(local, text="Port 8502 · privé", style="Muted.TLabel").grid(row=2, column=2, columnspan=2, sticky="e")
        self.local_start_btn = ttk.Button(local, text="Démarrer", command=lambda: self._server_action("local_start"))
        self.local_restart_btn = ttk.Button(local, text="Relancer", command=lambda: self._server_action("local_restart"))
        self.local_stop_btn = ttk.Button(local, text="Arrêter", command=lambda: self._server_action("local_stop"))
        self.local_open_btn = ttk.Button(local, text="Ouvrir", command=self.server_control.open_local)
        for i, widget in enumerate((self.local_start_btn, self.local_restart_btn, self.local_stop_btn, self.local_open_btn)):
            widget.grid(row=3, column=i, sticky="ew", padx=(0 if i == 0 else 4, 0), pady=(10, 0))
            local.columnconfigure(i, weight=1)

        runtime = ttk.LabelFrame(outer, text="Worker / Runtime", padding=10)
        runtime.pack(fill="x", pady=(0, 10))
        ttk.Label(runtime, text="Cible Worker", width=14).grid(row=0, column=0, sticky="w", pady=2)
        self.worker_target_combo = ttk.Combobox(runtime, textvariable=self.worker_target_var, values=("ONLINE", "LOCAL"), state="readonly", width=10)
        self.worker_target_combo.grid(row=0, column=1, sticky="w", pady=2)
        self.worker_target_combo.bind("<<ComboboxSelected>>", self._worker_target_changed)
        ttk.Label(runtime, text="État", width=12).grid(row=0, column=2, sticky="w", padx=(20, 0))
        ttk.Label(runtime, textvariable=self.status_var).grid(row=0, column=3, sticky="w")
        ttk.Label(runtime, text="Canal", width=10).grid(row=0, column=4, sticky="w", padx=(20, 0))
        ttk.Label(runtime, textvariable=self.txrx_var).grid(row=0, column=5, sticky="w")

        ttk.Label(runtime, text="API effective", width=14).grid(row=1, column=0, sticky="w", pady=2)
        ttk.Label(runtime, textvariable=self.url_var).grid(row=1, column=1, columnspan=5, sticky="w")
        ttk.Label(runtime, text="Python STEM", width=14).grid(row=2, column=0, sticky="w", pady=2)
        ttk.Label(runtime, textvariable=self.python_var).grid(row=2, column=1, columnspan=5, sticky="w")
        ttk.Label(runtime, text="CUDA / GPU", width=14).grid(row=3, column=0, sticky="w", pady=2)
        ttk.Label(runtime, textvariable=self.cuda_var).grid(row=3, column=1, columnspan=5, sticky="w")
        runtime.columnconfigure(5, weight=1)

        actions = ttk.Frame(runtime)
        actions.grid(row=4, column=0, columnspan=6, sticky="ew", pady=(8, 0))
        self.worker_button = ttk.Button(actions, text="Démarrer Worker", command=self._worker_action)
        self.worker_button.pack(side="left", padx=(0, 5))
        ttk.Button(actions, text="Pause / Reprendre", command=self._toggle_pause).pack(side="left", padx=5)
        ttk.Button(actions, text="Annuler job", command=self.engine.cancel_current).pack(side="left", padx=5)
        ttk.Button(actions, text="Ouvrir logs", command=self._open_logs).pack(side="right", padx=(5, 0))

        job = ttk.LabelFrame(outer, text="Job courant", padding=10)
        job.pack(fill="x", pady=(0, 10))
        ttk.Label(job, text="Chanson", width=14).grid(row=0, column=0, sticky="w")
        ttk.Label(job, textvariable=self.job_var).grid(row=0, column=1, sticky="w")
        ttk.Label(job, text="Étape", width=14).grid(row=1, column=0, sticky="w")
        ttk.Label(job, textvariable=self.stage_var).grid(row=1, column=1, sticky="w")
        self.progress = ttk.Progressbar(job, maximum=100, variable=self.progress_var)
        self.progress.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(8, 2))
        job.columnconfigure(1, weight=1)

        # Operational queue is always visible. The live console is collapsed
        # by default and uses an explicit pixel height when expanded.
        queue_box = ttk.LabelFrame(outer, text="Traitements en cours / à faire", padding=8)
        queue_box.pack(fill="x", pady=(0, 8))

        columns = ("id", "etat", "type", "chanson", "progression")
        self.queue_tree = ttk.Treeview(queue_box, columns=columns, show="headings", height=6)
        style.configure("Treeview", rowheight=25)
        headings = {"id": "#", "etat": "État", "type": "Traitement", "chanson": "Chanson", "progression": "Progression"}
        widths = {"id": 55, "etat": 105, "type": 105, "chanson": 650, "progression": 110}
        for name in columns:
            self.queue_tree.heading(name, text=headings[name])
            self.queue_tree.column(name, width=widths[name], anchor="w")
        queue_scroll = ttk.Scrollbar(queue_box, orient="vertical", command=self.queue_tree.yview)
        self.queue_tree.configure(yscrollcommand=queue_scroll.set)
        self.queue_tree.grid(row=0, column=0, sticky="nsew")
        queue_scroll.grid(row=0, column=1, sticky="ns")
        queue_box.columnconfigure(0, weight=1)
        queue_box.rowconfigure(0, weight=1)

        log_bar = ttk.Frame(outer)
        log_bar.pack(fill="x", pady=(0, 4))
        ttk.Label(log_bar, text="Console temps réel", style="CardTitle.TLabel").pack(side="left")
        self.logs_toggle_btn = ttk.Button(log_bar, text="Afficher les logs", command=self._toggle_console)
        self.logs_toggle_btn.pack(side="right", padx=(5, 0))
        ttk.Button(log_bar, text="Copier les logs", command=self._copy_console_logs).pack(side="right")

        self.console_box = ttk.Frame(outer, height=230)
        self.console_box.pack_propagate(False)
        self.console = tk.Text(
            self.console_box,
            wrap="none",
            bg="#0a0d10",
            fg="#d1f7d9",
            insertbackground="white",
            font=("Consolas", 10),
        )
        yscroll = ttk.Scrollbar(self.console_box, orient="vertical", command=self.console.yview)
        xscroll = ttk.Scrollbar(self.console_box, orient="horizontal", command=self.console.xview)
        self.console.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        self.console.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        self.console_box.rowconfigure(0, weight=1)
        self.console_box.columnconfigure(0, weight=1)
        self.console_visible = False

    def _summary_card(self, parent, column: int, title: str, variable: tk.StringVar) -> None:
        frame = ttk.LabelFrame(parent, text=title, padding=(6, 4))
        frame.grid(row=0, column=column, sticky="nsew", padx=(0 if column == 0 else 3, 0 if column == 2 else 3), pady=(0, 2))
        label = ttk.Label(frame, textvariable=variable, style="State.TLabel", wraplength=300)
        label.pack(anchor="w")

        def refresh_style(*_args):
            value = str(variable.get() or "").upper()
            if any(token in value for token in ("ARRÊTÉ", "DÉCONNECTÉ", "ERREUR", "INDISPONIBLE")):
                label.configure(style="StateBad.TLabel")
            elif any(token in value for token in ("MAINTENANCE", "RECONNEXION", "ATTENTE", "PAUSE", "PROTECTION")):
                label.configure(style="StateWarn.TLabel")
            elif any(token in value for token in ("CONNECTÉ", "ONLINE", "ACTIF", "RUNNING")):
                label.configure(style="StateGood.TLabel")
            else:
                label.configure(style="State.TLabel")

        variable.trace_add("write", refresh_style)
        refresh_style()

    def _busy_guard(self, operation: str) -> bool:
        if self.engine.current_job is not None:
            messagebox.showwarning("EZScore Analysis Worker", f"Un traitement est actif. {operation} interdite jusqu'à la fin du job.")
            return True
        if self._server_action_running:
            return True
        return False

    def _set_controls_state(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        readonly = "readonly" if enabled else "disabled"
        for widget in (
            self.online_start_btn, self.online_restart_btn, self.online_stop_btn,
            self.local_start_btn, self.local_restart_btn, self.local_stop_btn,
            self.maintenance_check,
        ):
            widget.configure(state=state)
        self.online_env_combo.configure(state=readonly)
        self.worker_target_combo.configure(state=readonly)

    def _server_action(self, action: str) -> None:
        if self._busy_guard("Bascule serveur"):
            return
        self._server_action_running = True
        self._set_controls_state(False)
        labels = {
            "online_start": "Démarrage ONLINE…", "online_restart": "Relance ONLINE…", "online_stop": "Arrêt ONLINE…",
            "local_start": "Démarrage LOCAL…", "local_restart": "Relance LOCAL…", "local_stop": "Arrêt LOCAL…",
        }
        self.operation_var.set(labels.get(action, "Opération serveur…"))

        def run():
            try:
                if action == "online_start": self.server_control.start_online()
                elif action == "online_restart": self.server_control.restart_online()
                elif action == "online_stop": self.server_control.stop_online()
                elif action == "local_start": self.server_control.start_local()
                elif action == "local_restart": self.server_control.restart_local()
                elif action == "local_stop": self.server_control.stop_local()
                else: raise RuntimeError(f"Action inconnue: {action}")
                self.events.put(("server_operation_done", action))
            except Exception as exc:
                self.events.put(("server_operation_error", str(exc)))
        threading.Thread(target=run, name=f"server-action-{action}", daemon=True).start()

    def _online_env_changed(self, _event=None) -> None:
        selected = self.online_env_var.get().lower()
        desired = self.server_control.snapshot_desired()["online"]["env"]
        if selected == desired:
            return
        if self._busy_guard("Changement d'environnement"):
            self.online_env_var.set(desired)
            return
        self._server_action_running = True
        self._set_controls_state(False)
        self.operation_var.set(f"ONLINE : bascule vers {selected} + relance automatique…")

        def run():
            try:
                self.server_control.set_online_environment(selected)
                self.events.put(("server_operation_done", "online_env"))
            except Exception as exc:
                self.events.put(("server_operation_error", str(exc)))
        threading.Thread(target=run, name="online-env-switch", daemon=True).start()

    def _maintenance_changed(self) -> None:
        selected = bool(self.online_maintenance_var.get())
        if self._busy_guard("Bascule maintenance"):
            current = self.server_control.snapshot_desired()["online"]["maintenance"]
            self.online_maintenance_var.set(current)
            return
        try:
            self.server_control.set_maintenance(selected)
            self.operation_var.set("Maintenance ONLINE activée" if selected else "Maintenance ONLINE désactivée")
        except Exception as exc:
            self.online_maintenance_var.set(not selected)
            messagebox.showerror("EZScore Analysis Worker", str(exc))

    def _worker_target_changed(self, _event=None) -> None:
        target = self.worker_target_var.get().lower()
        current = self.server_control.snapshot_desired()["worker"]["target"]
        if target == current:
            return
        if self.engine.current_job is not None:
            self.worker_target_var.set(current.upper())
            messagebox.showwarning("EZScore Analysis Worker", "Un traitement est actif. Changement de cible Worker interdit.")
            return
        self.server_control.set_worker_target(target)
        self.url_var.set(self.server_control.worker_url())
        self.worker_summary_var.set(f"Cible {target.upper()} · reconnexion…")
        self._append(f"Cible Worker -> {target.upper()}; redémarrage contrôlé du Worker.")
        if self.engine.running:
            if not self.engine.restart():
                messagebox.showerror("EZScore Analysis Worker", "Le Worker ne s'est pas arrêté proprement. Cible mémorisée, relance manuelle requise.")
        else:
            self._start()
        self._refresh_worker_button()

    def _refresh_worker_button(self):
        if self.engine.current_job is not None:
            self.worker_button.configure(text="Worker occupé", state="disabled")
        elif self.engine.running:
            self.worker_button.configure(text="Redémarrer Worker", state="normal")
        else:
            self.worker_button.configure(text="Démarrer Worker", state="normal")

    def _worker_action(self):
        if self.engine.current_job is not None:
            messagebox.showwarning("EZScore Analysis Worker", "Un traitement est actif. Redémarrage interdit.")
            return
        if self.engine.running:
            self._append("Redémarrage Worker : attente de la fin réelle de l'ancien thread…")
            if not self.engine.restart():
                messagebox.showerror("EZScore Analysis Worker", "L'ancien Worker ne s'est pas arrêté. Relance annulée.")
                return
        else:
            self._start()
        self._refresh_worker_button()

    def _start(self):
        if self.engine.running:
            return
        self._append(f"Démarrage du Worker desktop · cible {self.server_control.snapshot_desired()['worker']['target'].upper()}…")
        self.engine.start()
        self._refresh_worker_button()

    def _restore_and_start(self):
        try:
            self.server_control.restore_desired()
            self.events.put(("restore_done", None))
        except Exception as exc:
            self.events.put(("restore_error", str(exc)))

    def _render_queue(self, jobs):
        for item in self.queue_tree.get_children():
            self.queue_tree.delete(item)
        for job in jobs if isinstance(jobs, list) else []:
            status = str(job.get("status") or "")
            current_id = int((self.engine.current_job or {}).get("job_id") or 0)
            job_id = int(job.get("job_id") or 0)
            locally_running = current_id > 0 and current_id == job_id
            state = "EN COURS" if status == "running" or locally_running else "À FAIRE"
            kind = {"stems": "Stems", "chords": "Accords", "lyrics": "Paroles"}.get(str(job.get("kind") or ""), str(job.get("kind") or "—"))
            song = f"{job.get('artist') or ''} — {job.get('title') or ''}".strip(" —")
            progress_value = int(job.get("progress") or 0)
            if locally_running and self.engine.current_job:
                progress_value = int(self.engine.current_job.get("progress") or progress_value)
            progress = f"{progress_value} %" if status == "running" or locally_running else "—"
            tag = "running" if state == "EN COURS" else "pending"
            self.queue_tree.tag_configure("running", foreground="#188038")
            self.queue_tree.tag_configure("pending", foreground="#b06000")
            self.queue_tree.insert("", "end", values=(job.get("job_id"), state, kind, song, progress), tags=(tag,))

    def _toggle_pause(self):
        self.engine.pause(not self.engine.paused)

    def _toggle_console(self) -> None:
        if self.console_visible:
            self.console_box.pack_forget()
            self.console_visible = False
            self.logs_toggle_btn.configure(text="Afficher les logs")
            return

        self.root.update_idletasks()
        width = max(self.root.winfo_width(), 980)
        height = max(self.root.winfo_height(), 980)
        if self.root.winfo_height() < 980:
            self.root.geometry(f"{width}x{height}")

        self.console_box.pack(fill="x", pady=(0, 4))
        self.console_visible = True
        self.logs_toggle_btn.configure(text="Masquer les logs")
        self.console.see("end")
        self.root.update_idletasks()

    def _copy_console_logs(self) -> None:
        text = self.console.get("1.0", "end-1c")
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.root.update_idletasks()
        self.operation_var.set("Logs copiés dans le presse-papiers")

    def _open_logs(self):
        path = project_root() / "var" / "log"
        path.mkdir(parents=True, exist_ok=True)
        os.startfile(str(path))

    def _append(self, text: str):
        self.console.insert("end", text.rstrip() + "\n")
        self.console.see("end")

    def _health_degraded(self, key: str, healthy: bool) -> bool:
        state = self._health_state[key]
        if healthy:
            state["good"] += 1
            state["bad"] = 0
            if state["degraded"] and state["good"] >= 2:
                state["degraded"] = False
        else:
            state["bad"] += 1
            state["good"] = 0
            if not state["degraded"] and state["bad"] >= 3:
                state["degraded"] = True
        return bool(state["degraded"])

    def _apply_server_snapshot(self, data: dict) -> None:
        self._last_snapshot = data
        online = data.get("online") or {}
        local = data.get("local") or {}
        worker = data.get("worker") or {}
        desired = data.get("desired") or self.server_control.snapshot_desired()

        gateway_process = bool(
            online.get("gateway_process_alive", online.get("gateway_alive"))
        )
        backend_process = bool(
            online.get("backend_process_alive", online.get("backend_alive"))
        )
        gateway_http = bool(
            online.get("gateway_http_healthy", online.get("gateway_alive"))
        )
        backend_http = bool(
            online.get("backend_http_healthy", online.get("backend_alive"))
        )

        gateway_degraded = self._health_degraded("online_gateway", gateway_http)
        backend_degraded = self._health_degraded("online_backend", backend_http)

        online_env = str(online.get("env") or desired["online"]["env"])
        maintenance = bool(online.get("maintenance"))
        maintenance_observed = online.get("maintenance_observed")

        # Process liveness is authoritative. HTTP health cannot flip ACTIVE/STOPPED.
        if gateway_process:
            if maintenance_observed is True and maintenance:
                state = "MAINTENANCE"
            elif not backend_process:
                state = "PROTÉGÉ · backend arrêté"
            elif gateway_degraded:
                state = "ONLINE · passerelle lente"
            elif backend_degraded:
                state = "PROTÉGÉ · backend indisponible"
            else:
                state = "ONLINE"

            self.online_summary_var.set(f"● {state} / {online_env}")
            profiler = "Profiler actif" if online_env == "dev" else "Profiler inactif"
            health_note = ""
            if backend_process and not backend_http and not backend_degraded:
                health_note = " · vérification HTTP"
            self.online_detail_var.set(
                f"{online.get('public_url') or self.server_control.public_url()} "
                f"· {profiler} · backend :8511{health_note}"
            )
        else:
            self.online_summary_var.set(f"○ ARRÊTÉ / {online_env}")
            self.online_detail_var.set(
                f"{online.get('public_url') or self.server_control.public_url()} "
                "· passerelle arrêtée"
            )

        self.online_env_var.set(online_env)
        self.online_maintenance_var.set(maintenance)

        local_process = bool(local.get("process_alive", local.get("alive")))
        local_http = bool(local.get("http_healthy", local.get("alive")))
        local_degraded = self._health_degraded("local_http", local_http)

        if local_process:
            state = "ACTIF · HTTP lent" if local_degraded else "ACTIF"
            self.local_summary_var.set(f"● {state} / dev")
            detail = (
                f"{local.get('url') or self.server_control.local_url()} "
                f"· PID {local.get('pid') or '—'}"
            )
            if not local_http and not local_degraded:
                detail += " · vérification HTTP"
            self.local_detail_var.set(detail)
        else:
            self.local_summary_var.set("○ ARRÊTÉ / dev")
            self.local_detail_var.set(self.server_control.local_url())

        target = str(worker.get("target") or desired["worker"]["target"]).upper()
        self.worker_target_var.set(target)
        self.worker_summary_var.set(f"{self.status_var.get()} · {target}")
        self.url_var.set(str(worker.get("url") or self.server_control.worker_url()))

    def _drain_events(self):
        while True:
            try:
                kind, payload = self.events.get_nowait()
            except queue.Empty:
                break

            if kind in ("log", "engine_log"):
                self._append(str(payload))
            elif kind == "status":
                self.status_var.set(str(payload))
                target = self.server_control.snapshot_desired()["worker"]["target"].upper()
                self.worker_summary_var.set(f"{payload} · {target}")
                self._refresh_worker_button()
            elif kind == "txrx":
                self.txrx_var.set(str(payload))
            elif kind == "server_snapshot":
                self._apply_server_snapshot(payload if isinstance(payload, dict) else {})
            elif kind == "server_operation_done":
                self._server_action_running = False
                self._set_controls_state(True)
                self.operation_var.set("Opération serveur terminée")
                self.events.put(("server_snapshot", self.server_control.status()))
            elif kind == "server_operation_error":
                self._server_action_running = False
                self._set_controls_state(True)
                desired = self.server_control.snapshot_desired()
                self.online_env_var.set(desired["online"]["env"])
                self.online_maintenance_var.set(desired["online"]["maintenance"])
                self.operation_var.set("ERREUR serveur")
                messagebox.showerror("EZScore — serveur", str(payload))
            elif kind == "restore_done":
                self.operation_var.set("Modes persistés restaurés")
                self.events.put(("server_snapshot", self.server_control.status()))
                self._start()
            elif kind == "restore_error":
                self.operation_var.set("Restauration incomplète · Worker actif")
                self.events.put(("server_snapshot", self.server_control.status()))
                self._append(f"[SERVER] Restauration incomplète: {payload}")
                self._append("[SERVER] Le Worker démarre quand même et gère lui-même la reconnexion à sa cible.")
                self._start()
                messagebox.showwarning("EZScore — restauration serveurs", str(payload))
            elif kind == "connection_config":
                data = payload if isinstance(payload, dict) else {}
                self.url_var.set(str(data.get("url", "—")))
                self.python_var.set(str(data.get("python", "—")))
                caps = data.get("capabilities") or {}
                if caps.get("cuda"):
                    gpu = str(caps.get("gpu") or "CUDA")
                    self.cuda_var.set(gpu)
                    self.gpu_summary_var.set(f"● CUDA · {gpu}")
                else:
                    self.cuda_var.set("CUDA indisponible")
                    self.gpu_summary_var.set("● CUDA indisponible")
            elif kind == "queue":
                self._render_queue(payload)
            elif kind == "job":
                self._refresh_worker_button()
                if payload:
                    self.job_var.set(f"#{payload.get('job_id')} · {payload.get('artist') or ''} — {payload.get('title') or ''}")
                else:
                    self.job_var.set("Aucun")
                    self.stage_var.set("—")
                    self.progress_var.set(0)
            elif kind == "progress":
                data = payload if isinstance(payload, dict) else {}
                self.progress_var.set(float(data.get("percent", 0)))
                self.stage_var.set(f"{data.get('stage') or '—'} · {data.get('message') or ''} · {data.get('percent', 0)} %")
            elif kind == "error":
                messagebox.showerror("EZScore Analysis Worker", str(payload))

        self.root.after(100, self._drain_events)

    def _on_close(self):
        if self.engine.current_process and self.engine.current_process.poll() is None:
            if not messagebox.askyesno("EZScore Analysis Worker", "Une analyse est en cours. Fermer l'application et demander l'arrêt du processus ?"):
                return
            self.engine.cancel_current()
        self.engine.request_stop()
        self.server_monitor.stop()
        self.root.destroy()

    def run(self):
        self.operation_var.set("Restauration des modes persistés…")
        self._bootstrap_path.parent.mkdir(parents=True, exist_ok=True)
        self._bootstrap_path.write_text(json.dumps({
            "ready": False,
            "stage": "starting",
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        threading.Thread(target=self._restore_and_start, name="restore-server-modes", daemon=True).start()
        self.root.after(2500, lambda: self._bootstrap_path.write_text(json.dumps({
            "ready": True,
            "stage": "worker_window_ready",
            "worker_status": self.status_var.get(),
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"))
        self.root.mainloop()


if __name__ == "__main__":
    WorkerWindow().run()
