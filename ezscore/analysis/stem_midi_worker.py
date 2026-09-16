from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import traceback
from pathlib import Path

from ezscore.analysis.stem_midi import (
    browser_events_from_bundle,
    build_chord_midi,
    build_combined_midi,
    build_drum_midi,
    build_vocal_midi,
    drum_analysis_from_structure,
)

APP_DIR = Path(__file__).resolve().parents[2]


def _atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def _read_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _status(output_dir: Path, payload: dict, *, started: float) -> None:
    row = dict(payload)
    row.update({
        "pid": os.getpid(),
        "updated_at_epoch": time.time(),
        "elapsed_seconds": round(time.time() - started, 3),
    })
    _atomic_json(output_dir / "job_status.json", row)


def _append_log(output_dir: Path, message: str) -> None:
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    with (output_dir / "job.log").open("a", encoding="utf-8") as fh:
        fh.write(f"[{stamp}] {message}\n")


def _creationflags() -> int:
    return int(getattr(subprocess, "CREATE_NO_WINDOW", 0)) if os.name == "nt" else 0


def _run_vocal_with_watchdog(*, cmd, progress_path, output_dir, started,
                             inactivity_timeout, total_timeout) -> None:
    if progress_path.exists():
        progress_path.unlink()
    child = subprocess.Popen(
        cmd, cwd=str(APP_DIR), stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        close_fds=(os.name != "nt"), creationflags=_creationflags(),
    )
    child_started = time.time()
    last_progress_epoch = child_started
    last_signature = None
    while True:
        rc = child.poll()
        progress = _read_json(progress_path)
        now = time.time()
        if progress:
            signature = (progress.get("stage"), progress.get("chunk_index"),
                         progress.get("percent"), progress.get("message"))
            updated = float(progress.get("updated_at_epoch", now) or now)
            if signature != last_signature:
                last_signature = signature
                last_progress_epoch = updated
                _append_log(output_dir, str(progress.get("message", "")))
            child_percent = float(progress.get("percent", 0.0) or 0.0)
            _status(output_dir, {
                "state": "running",
                "stage": f"vocal:{progress.get('stage', 'running')}",
                "message": str(progress.get("message", "Analyse MIDI du chant…")),
                "percent": round(0.25 + 0.65 * max(0.0, min(1.0, child_percent)), 4),
                "child_pid": int(child.pid),
                "chunk_index": progress.get("chunk_index"),
                "chunk_total": progress.get("chunk_total"),
                "vocal_elapsed_seconds": progress.get("elapsed_seconds"),
            }, started=started)
        if rc is not None:
            break
        if now - child_started > float(total_timeout):
            child.kill(); child.wait(timeout=10)
            raise RuntimeError(f"Watchdog vocal : durée totale dépassée ({total_timeout:.0f}s).")
        if now - last_progress_epoch > float(inactivity_timeout):
            child.kill(); child.wait(timeout=10)
            stuck = _read_json(progress_path)
            raise RuntimeError(
                f"Watchdog vocal : aucun progrès depuis {inactivity_timeout:.0f}s. "
                f"Dernière étape={stuck.get('stage')!r}, "
                f"segment={stuck.get('chunk_index')}/{stuck.get('chunk_total')}."
            )
        time.sleep(1.0)
    if child.returncode != 0:
        progress = _read_json(progress_path)
        raise RuntimeError("Analyse MIDI chant échouée : " + str(progress.get("message", f"code {child.returncode}")))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vocals", required=True)
    parser.add_argument("--drums", required=True)
    parser.add_argument("--structure", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--vocal-inactivity-timeout", type=float, default=120.0)
    parser.add_argument("--vocal-timeout", type=float, default=900.0)
    args = parser.parse_args()

    vocals_path = Path(args.vocals)
    structure_path = Path(args.structure)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    started = time.time()

    try:
        structure = _read_json(structure_path)
        tempo = float(structure.get("tempo", 0.0) or 120.0)
        beats_per_bar = int(structure.get("beats_per_bar", 4) or 4)
        _append_log(output_dir, "MIDI worker start")

        _status(output_dir, {
            "state": "running", "stage": "metric_midi",
            "message": "MIDI métrique : Accords + Batterie depuis la timeline de structure.",
            "percent": 0.10,
        }, started=started)

        drum_analysis = drum_analysis_from_structure(structure)
        chords_path = output_dir / "chords.mid"
        drums_out = output_dir / "drums.mid"
        chords_path.write_bytes(build_chord_midi(structure, tempo=tempo))
        drums_out.write_bytes(build_drum_midi(drum_analysis, tempo=tempo, beats_per_bar=beats_per_bar))
        _append_log(output_dir, "Metric Chords + Drums MIDI ready")

        vocal_json = output_dir / "vocal_analysis.json"
        vocal_progress = output_dir / "vocal_progress.json"
        vocal = _read_json(vocal_json)
        if vocal and "notes" in vocal:
            _status(output_dir, {
                "state": "running", "stage": "vocal_cached",
                "message": "Chant MIDI : analyse F0 existante réutilisée.",
                "percent": 0.90,
            }, started=started)
            _append_log(output_dir, "Reuse cached vocal_analysis.json")
        else:
            _run_vocal_with_watchdog(
                cmd=[sys.executable, "-m", "ezscore.analysis.stem_vocal_worker",
                     "--vocals", str(vocals_path), "--output-json", str(vocal_json),
                     "--progress-json", str(vocal_progress), "--chunk-seconds", "20"],
                progress_path=vocal_progress, output_dir=output_dir, started=started,
                inactivity_timeout=float(args.vocal_inactivity_timeout),
                total_timeout=float(args.vocal_timeout),
            )
            vocal = _read_json(vocal_json)
            if not vocal or "notes" not in vocal:
                raise RuntimeError("Analyse chant terminée sans vocal_analysis.json valide.")

        _status(output_dir, {"state": "running", "stage": "midi_render",
                             "message": "Finalisation MIDI : Chant + fichier combiné.",
                             "percent": 0.94}, started=started)

        vocal_out = output_dir / "vocal.mid"
        combined_out = output_dir / "stem_mix.mid"
        if not vocal_out.is_file():
            vocal_out.write_bytes(build_vocal_midi(vocal["notes"], tempo=tempo))
        combined_out.write_bytes(build_combined_midi(
            vocal_notes=vocal["notes"], structure=structure,
            drum_analysis=drum_analysis, tempo=tempo, beats_per_bar=beats_per_bar))

        browser_events = browser_events_from_bundle(
            vocal_notes=vocal["notes"], structure=structure,
            drum_analysis=drum_analysis, beats_per_bar=beats_per_bar)
        metadata = {
            "state": "complete", "timebase": "original_audio_seconds",
            "tempo": tempo, "beats_per_bar": beats_per_bar,
            "vocal_note_count": int(vocal.get("note_count", 0)),
            "drum_beat_count": int(drum_analysis.get("beat_count", 0)),
            "available_tracks": ["vocal", "chords", "drums"], "pending_tracks": [],
            "files": {"vocal": vocal_out.name, "chords": chords_path.name,
                      "drums": drums_out.name, "combined": combined_out.name},
            "browser_events": browser_events, "vocal_analysis": vocal,
            "drum_analysis": drum_analysis,
        }
        _atomic_json(output_dir / "stem_midi.json", metadata)
        _append_log(output_dir, "MIDI bundle complete")
        _status(output_dir, {"state": "done", "stage": "done",
                             "message": "MIDI Chant + Accords + Batterie terminés.",
                             "percent": 1.0,
                             "vocal_note_count": int(vocal.get("note_count", 0)),
                             "drum_beat_count": int(drum_analysis.get("beat_count", 0))},
                started=started)
        return 0
    except Exception as exc:
        _append_log(output_dir, "ERROR: " + str(exc))
        _status(output_dir, {"state": "error", "stage": "error",
                             "message": str(exc), "traceback": traceback.format_exc()},
                started=started)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
