#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else r"H:\EZScore_v1").resolve()
WORKER = ROOT / "worker_app" / "ezscore_analysis_worker.pyw"

def rd(p):
    return p.read_text(encoding="utf-8").replace("\r\n","\n").replace("\r","\n")

def wr(p, text):
    tmp = p.with_suffix(p.suffix + ".r39_4_tmp")
    tmp.write_text(text, encoding="utf-8", newline="\n")
    tmp.replace(p)

def once(text, old, new, label):
    n = text.count(old)
    if n != 1:
        raise RuntimeError(f"{label}: expected 1 anchor, found {n}. STOP.")
    return text.replace(old, new, 1)

def main():
    if not WORKER.is_file():
        raise RuntimeError(f"Missing prerequisite: {WORKER}. STOP.")

    source = rd(WORKER)
    backup = WORKER.read_bytes()

    checks = [
        ('version', 'APP_VERSION = "R35.4"' in source),
        ('heartbeat', 'def _send_heartbeat(self, status: str) -> None:' in source),
        ('loop', 'def _loop(self) -> None:' in source),
        ('server stop', 'def _stop_server(self):' in source),
        ('server bootstrap', 'def _ensure_server_then_start(self):' in source),
        ('error popup', 'elif kind == "error":\n                messagebox.showerror("EZScore Analysis Worker", str(payload))' in source),
    ]
    bad = [name for name, ok in checks if not ok]
    if bad:
        raise RuntimeError("Unexpected worker baseline: " + ", ".join(bad) + ". STOP.")

    try:
        source = once(
            source,
            'APP_VERSION = "R35.4"\nHEARTBEAT_SECONDS = 2.0\nCLAIM_SECONDS = 1.5\n',
            'APP_VERSION = "R39.4"\nHEARTBEAT_SECONDS = 2.0\nCLAIM_SECONDS = 1.5\nRECONNECT_MIN_SECONDS = 1.0\nRECONNECT_MAX_SECONDS = 15.0\n',
            "constants"
        )

        helper_anchor = 'def local_server_url() -> str:\n    return "http://127.0.0.1:8501"\n\n\n'
        helper_new = '''def local_server_url() -> str:
    return "http://127.0.0.1:8501"


def connection_error_summary(exc: Exception) -> tuple[str, str]:
    text = str(exc)
    lowered = text.lower()

    if (
        "getcachewarmerservice.php" in lowered
        or ("var\\\\cache\\\\dev\\\\container" in lowered and "failed to open stream" in lowered)
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

    line = " ".join(text.replace("\\r", " ").replace("\\n", " ").split())
    return ("network", line[:220] or exc.__class__.__name__)


'''
        source = once(source, helper_anchor, helper_new, "connection error helper")

        old_loop = '''    def _loop(self) -> None:
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
'''

        new_loop = '''    def _loop(self) -> None:
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
'''
        source = once(source, old_loop, new_loop, "worker loop")

        old_stop = '''    def _stop_server(self):
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
'''
        new_stop = '''    def _stop_server(self):
        if self.engine.current_job is not None:
            messagebox.showwarning(
                "EZScore Analysis Worker",
                "Un traitement est actif. Arrêt du serveur interdit jusqu'à la fin du job.",
            )
            return

        pid = local_server_pid(project_root())
        if not pid:
            return

        subprocess.run(
            ["powershell", "-NoProfile", "-Command", f"Stop-Process -Id {pid} -Force -ErrorAction SilentlyContinue"],
            cwd=str(project_root()),
            check=False,
            creationflags=WINDOWS_NO_WINDOW if os.name == "nt" else 0,
        )

        for _ in range(40):
            alive, _ = local_server_alive(timeout=0.35)
            if not alive:
                self._append("Serveur local arrêté.")
                return
            time.sleep(0.25)

        self._append("Arrêt serveur demandé, mais le processus HTTP répond encore.")
'''
        source = once(source, old_stop, new_stop, "server stop guard")

        old_boot = '''    def _ensure_server_then_start(self):
        alive, _ = local_server_alive()
        if not alive:
            self._start_server()
            for _ in range(40):
                alive, _ = local_server_alive()
                if alive:
                    break
                time.sleep(0.25)
        self._start()
'''
        new_boot = '''    def _ensure_server_then_start(self):
        alive, _ = local_server_alive()
        if not alive:
            self._start_server()
            for _ in range(80):
                alive, _ = local_server_alive(timeout=0.5)
                if alive:
                    break
                time.sleep(0.25)

        if not alive:
            self._append("Serveur local indisponible après 20 s. Worker non démarré.")
            self.status_var.set("SERVEUR INDISPONIBLE")
            self._refresh_worker_button()
            return

        self._start()
'''
        source = once(source, old_boot, new_boot, "server startup readiness")

        for token in (
            'APP_VERSION = "R39.4"',
            'connection_error_summary',
            'self.app.events.put(("status", "RECONNEXION"))',
            'Prise de job impossible',
            "Arrêt du serveur interdit jusqu'à la fin du job.",
            'Serveur local indisponible après 20 s. Worker non démarré.',
        ):
            if token not in source:
                raise RuntimeError(f"Generated worker missing {token}. STOP.")

        wr(WORKER, source)
        print("R39_4_WORKER_RESILIENCE_INSTALL_OK")

    except Exception:
        WORKER.write_bytes(backup)
        raise

if __name__ == "__main__":
    main()
