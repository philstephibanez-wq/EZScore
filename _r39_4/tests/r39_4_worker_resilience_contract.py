#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else r"H:\EZScore_v1").resolve()
src = (ROOT/"worker_app/ezscore_analysis_worker.pyw").read_text(encoding="utf-8")

assert 'APP_VERSION = "R39.4"' in src
assert "def connection_error_summary(exc: Exception)" in src
assert "getcachewarmerservice.php" in src.lower()
assert "Cache Symfony incohérent" in src
assert 'self.app.events.put(("status", "RECONNEXION"))' in src
assert 'self.app.events.put(("txrx", "HTTP indisponible"))' in src
assert "reconnect_delay = min(" in src
assert '"/internal/analysis/desktop/hello"' in src
assert '"/internal/analysis/desktop/heartbeat"' in src
assert "Prise de job impossible:" in src

loop = src.split("    def _loop(self) -> None:",1)[1].split("    def _run_job",1)[0]
assert "try:" in loop
assert "except Exception as exc:" in loop
assert "connected = False" in loop
assert "RECONNECT_MIN_SECONDS" in loop

assert "Arrêt du serveur interdit jusqu'à la fin du job." in src
assert "Serveur local indisponible après 20 s. Worker non démarré." in src
assert "for _ in range(80):" in src
assert 'self.app.events.put(("error", str(exc)))' in src

print("R39_4_WORKER_RESILIENCE_CONTRACT_OK")
