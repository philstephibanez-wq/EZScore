#!/usr/bin/env python3
from pathlib import Path
import sys

def die(msg):
    raise SystemExit("R37.0d ABORT: " + msg)

root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
worker = root / "worker_app" / "ezscore_analysis_worker.pyw"
helper = root / "worker_app" / "lyrics_worker_r37.py"

if not worker.is_file():
    die("worker_app/ezscore_analysis_worker.pyw absent")
if not helper.is_file():
    die("worker_app/lyrics_worker_r37.py absent")

s = worker.read_text(encoding="utf-8-sig")

for token in ['self._run_chord_job(job)', 'def _read_progress(']:
    if token not in s:
        die("Worker stable inattendu, token absent: " + token)

if 'from lyrics_worker_r37 import run_lyrics_job' not in s:
    anchor = (
        '        if job.get("kind") == "chords":\n'
        '            self._run_chord_job(job)\n'
        '            return\n\n'
    )
    if anchor not in s:
        die("bloc dispatch CHORDS introuvable")

    replacement = anchor + (
        '        if job.get("kind") == "lyrics":\n'
        '            from lyrics_worker_r37 import run_lyrics_job\n'
        '            run_lyrics_job(self, job)\n'
        '            return\n\n'
    )
    s = s.replace(anchor, replacement, 1)

worker.write_text(s, encoding="utf-8", newline="\n")

check = worker.read_text(encoding="utf-8")
for token in [
    'self._run_chord_job(job)',
    'def _read_progress(',
    'if job.get("kind") == "lyrics":',
    'from lyrics_worker_r37 import run_lyrics_job',
    'run_lyrics_job(self, job)',
]:
    if token not in check:
        die("token absent après patch: " + token)

print("R37_0D_APPLIED_OK")
