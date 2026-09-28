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


APP_VERSION = "R35.4"
HEARTBEAT_SECONDS = 2.0
CLAIM_SECONDS = 1.5

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
            "import json,torch,bs_roformer,mel_band_roformer;"
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
                    timeout=20,
                    check=False,
                    creationflags=WINDOWS_NO_WINDOW if os.name == "nt" else 0,
                )
                if proc.returncode != 0:
                    failures.append(f"{candidate}: {proc.stderr.strip()[-250:]}")
                    continue
                data = json.loads(proc.stdout.strip().splitlines()[-1])
                data["bs_roformer"] = True
                data["mel_band_roformer"] = True
                return str(data["python"]), data
            except Exception as exc:
                failures.append(f"{candidate}: {exc}")

        return None, {"errors": failures[-5:]}

    def configure(self) -> None:
        env = read_env_local(self.root)
        base_url = (
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
            raise RuntimeError(
                "Aucun Python compatible trouvé. Il faut bs_roformer + mel_band_roformer."
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

            hello = self.api.post("/internal/analysis/desktop/hello", self._heartbeat_payload("starting"))
            self.app.events.put(("status", "CONNECTÉ"))
            self.log(f"Connexion EZScore établie. worker_id={self.worker_id}")
            for command in (hello or {}).get("commands", []):
                self._handle_command(command)

            last_heartbeat = 0.0
            last_claim = 0.0
            last_queue_refresh = 0.0

            while not self.stop_event.is_set():
                now = time.monotonic()
                if now - last_heartbeat >= HEARTBEAT_SECONDS:
                    self._send_heartbeat("paused" if self.paused else ("busy" if self.current_job else "idle"))
                    last_heartbeat = now

                if now - last_queue_refresh >= 2.0:
                    try:
                        queue_state = self.api.get("/internal/analysis/desktop/jobs/queue", timeout=10)
                        self.app.events.put(("queue", (queue_state or {}).get("jobs", [])))
                    except Exception as exc:
                        self.log(f"Lecture file d'attente impossible: {exc}")
                    last_queue_refresh = now

                if not self.paused and self.current_job is None and now - last_claim >= CLAIM_SECONDS:
                    job = self.api.post("/internal/analysis/desktop/jobs/claim", {})
                    last_claim = now
                    if job:
                        self._run_job(job)

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


class LocalServerMonitor:
    def __init__(self, app: "WorkerWindow"):
        self.app = app
        self.stop_event = threading.Event()
        self.thread: threading.Thread | None = None

    def start(self) -> None:
        if self.thread and self.thread.is_alive():
            return
        self.stop_event.clear()
        self.thread = threading.Thread(
            target=self._loop,
            name="local-server-monitor",
            daemon=True,
        )
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()

    def _loop(self) -> None:
        while not self.stop_event.is_set():
            alive, pid = local_server_alive()
            self.app.events.put(("server_status", {
                "alive": alive,
                "pid": pid,
                "url": local_server_url(),
            }))
            self.stop_event.wait(2.0)


class WorkerWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("EZScore Analysis Worker")
        self.root.geometry("1120x760")
        self.root.minsize(900, 620)
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.engine = WorkerEngine(self)

        self.status_var = tk.StringVar(value="ARRÊTÉ")
        self.url_var = tk.StringVar(value="—")
        self.python_var = tk.StringVar(value="—")
        self.cuda_var = tk.StringVar(value="—")
        self.job_var = tk.StringVar(value="Aucun")
        self.stage_var = tk.StringVar(value="—")
        self.txrx_var = tk.StringVar(value="—")
        self.server_var = tk.StringVar(value="Vérification…")
        self.progress_var = tk.DoubleVar(value=0)
        self.server_monitor = LocalServerMonitor(self)

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

        top = ttk.Frame(self.root, padding=12)
        top.pack(fill="x")

        ttk.Label(top, text="EZScore Analysis Worker", font=("Segoe UI", 18, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Label(top, text=f"{APP_VERSION} · STEMS + CHORDS", foreground="#666").grid(row=1, column=0, sticky="w")

        buttons = ttk.Frame(top)
        buttons.grid(row=0, column=1, rowspan=2, sticky="e")
        self.worker_button = ttk.Button(buttons, text="Démarrer Worker", command=self._worker_action)
        self.worker_button.pack(side="left", padx=4)
        self.server_start_button = ttk.Button(buttons, text="Démarrer serveur", command=self._start_server)
        self.server_start_button.pack(side="left", padx=4)
        self.server_stop_button = ttk.Button(buttons, text="Arrêter serveur", command=self._stop_server)
        self.server_stop_button.pack(side="left", padx=4)
        ttk.Button(buttons, text="Pause / Reprendre", command=self._toggle_pause).pack(side="left", padx=4)
        ttk.Button(buttons, text="Annuler job", command=self.engine.cancel_current).pack(side="left", padx=4)
        ttk.Button(buttons, text="Ouvrir EZScore", command=self._open_ezscore).pack(side="left", padx=4)
        ttk.Button(buttons, text="Ouvrir logs", command=self._open_logs).pack(side="left", padx=4)
        top.columnconfigure(0, weight=1)

        info = ttk.LabelFrame(self.root, text="Connexion / Runtime", padding=10)
        info.pack(fill="x", padx=12, pady=(0, 10))
        rows = [
            ("État", self.status_var),
            ("API EZScore", self.url_var),
            ("Python STEM", self.python_var),
            ("CUDA / GPU", self.cuda_var),
            ("Serveur local", self.server_var),
            ("Canal", self.txrx_var),
        ]
        for i, (label, var) in enumerate(rows):
            ttk.Label(info, text=label, width=14).grid(row=i, column=0, sticky="w", pady=2)
            ttk.Label(info, textvariable=var).grid(row=i, column=1, sticky="w", pady=2)
        info.columnconfigure(1, weight=1)

        job = ttk.LabelFrame(self.root, text="Job courant", padding=10)
        job.pack(fill="x", padx=12, pady=(0, 10))
        ttk.Label(job, text="Chanson", width=14).grid(row=0, column=0, sticky="w")
        ttk.Label(job, textvariable=self.job_var).grid(row=0, column=1, sticky="w")
        ttk.Label(job, text="Étape", width=14).grid(row=1, column=0, sticky="w")
        ttk.Label(job, textvariable=self.stage_var).grid(row=1, column=1, sticky="w")
        self.progress = ttk.Progressbar(job, maximum=100, variable=self.progress_var)
        self.progress.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(8, 2))
        job.columnconfigure(1, weight=1)

        queue_box = ttk.LabelFrame(self.root, text="Traitements en cours / à faire", padding=8)
        queue_box.pack(fill="x", padx=12, pady=(0, 10))
        columns = ("id", "etat", "type", "chanson", "progression")
        self.queue_tree = ttk.Treeview(queue_box, columns=columns, show="headings", height=6)
        headings = {"id": "#", "etat": "État", "type": "Traitement", "chanson": "Chanson", "progression": "Progression"}
        widths = {"id": 55, "etat": 95, "type": 95, "chanson": 560, "progression": 105}
        for name in columns:
            self.queue_tree.heading(name, text=headings[name])
            self.queue_tree.column(name, width=widths[name], anchor="w")
        queue_scroll = ttk.Scrollbar(queue_box, orient="vertical", command=self.queue_tree.yview)
        self.queue_tree.configure(yscrollcommand=queue_scroll.set)
        self.queue_tree.grid(row=0, column=0, sticky="nsew")
        queue_scroll.grid(row=0, column=1, sticky="ns")
        queue_box.columnconfigure(0, weight=1)

        console_box = ttk.LabelFrame(self.root, text="Console temps réel", padding=8)
        console_box.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.console = tk.Text(
            console_box,
            wrap="none",
            bg="#0a0d10",
            fg="#d1f7d9",
            insertbackground="white",
            font=("Consolas", 10),
        )
        yscroll = ttk.Scrollbar(console_box, orient="vertical", command=self.console.yview)
        xscroll = ttk.Scrollbar(console_box, orient="horizontal", command=self.console.xview)
        self.console.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        self.console.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        console_box.rowconfigure(0, weight=1)
        console_box.columnconfigure(0, weight=1)

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
        self._append("Démarrage du worker desktop…")
        self.engine.start()
        self._refresh_worker_button()

    def _start_server(self):
        alive, _ = local_server_alive()
        if alive:
            return
        script = project_root() / "scripts" / "start_ezscore_web.ps1"
        subprocess.Popen(
            ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(script), "-Port", "8501"],
            cwd=str(project_root()),
            creationflags=WINDOWS_NO_WINDOW if os.name == "nt" else 0,
        )
        self._append("Démarrage du serveur local demandé.")

    def _stop_server(self):
        pid = local_server_pid(project_root())
        if not pid:
            return
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", f"Stop-Process -Id {pid} -Force -ErrorAction SilentlyContinue"],
            cwd=str(project_root()),
            check=False,
            creationflags=WINDOWS_NO_WINDOW if os.name == "nt" else 0,
        )
        self._append("Arrêt du serveur local demandé.")

    def _ensure_server_then_start(self):
        alive, _ = local_server_alive()
        if not alive:
            self._start_server()
            for _ in range(40):
                alive, _ = local_server_alive()
                if alive:
                    break
                time.sleep(0.25)
        self._start()

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
            self.queue_tree.insert("", "end", values=(job.get("job_id"), state, kind, song, progress))

    def _toggle_pause(self):
        self.engine.pause(not self.engine.paused)

    def _open_ezscore(self):
        webbrowser.open(browser_url(project_root()) + "/fr/catalog")

    def _open_logs(self):
        path = project_root() / "var" / "log"
        path.mkdir(parents=True, exist_ok=True)
        os.startfile(str(path))

    def _append(self, text: str):
        self.console.insert("end", text.rstrip() + "\n")
        self.console.see("end")

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
                self._refresh_worker_button()
            elif kind == "txrx":
                self.txrx_var.set(str(payload))
            elif kind == "server_status":
                data = payload if isinstance(payload, dict) else {}
                if data.get("alive"):
                    pid = data.get("pid")
                    self.server_var.set(
                        f"ACTIF · 127.0.0.1:8501" + (f" · PID {pid}" if pid else "")
                    )
                else:
                    self.server_var.set("ARRÊTÉ · 127.0.0.1:8501")
            elif kind == "connection_config":
                data = payload if isinstance(payload, dict) else {}
                self.url_var.set(str(data.get("url", "—")))
                self.python_var.set(str(data.get("python", "—")))
                caps = data.get("capabilities") or {}
                if caps.get("cuda"):
                    self.cuda_var.set(str(caps.get("gpu") or "CUDA"))
                else:
                    self.cuda_var.set("CUDA indisponible")
            elif kind == "queue":
                self._render_queue(payload)
            elif kind == "job":
                self._refresh_worker_button()
                if payload:
                    self.job_var.set(
                        f"#{payload.get('job_id')} · {payload.get('artist') or ''} — {payload.get('title') or ''}"
                    )
                else:
                    self.job_var.set("Aucun")
                    self.stage_var.set("—")
                    self.progress_var.set(0)
            elif kind == "progress":
                data = payload if isinstance(payload, dict) else {}
                self.progress_var.set(float(data.get("percent", 0)))
                self.stage_var.set(
                    f"{data.get('stage') or '—'} · {data.get('message') or ''} · {data.get('percent', 0)} %"
                )
            elif kind == "error":
                messagebox.showerror("EZScore Analysis Worker", str(payload))

        self.root.after(100, self._drain_events)

    def _on_close(self):
        if self.engine.current_process and self.engine.current_process.poll() is None:
            if not messagebox.askyesno(
                "EZScore Analysis Worker",
                "Une analyse est en cours. Fermer l'application et demander l'arrêt du processus ?",
            ):
                return
            self.engine.cancel_current()

        self.engine.request_stop()
        self.server_monitor.stop()
        self.root.destroy()

    def run(self):
        self.root.after(250, self._ensure_server_then_start)
        self.root.mainloop()


if __name__ == "__main__":
    WorkerWindow().run()
