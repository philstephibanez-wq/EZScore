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
    if os.name == "nt":
        return int(getattr(subprocess, "CREATE_NO_WINDOW", 0))
    return 0


def _run_child_with_watchdog(
    *,
    cmd: list[str],
    progress_path: Path,
    output_dir: Path,
    started: float,
    stage_prefix: str,
    overall_start: float,
    overall_span: float,
    inactivity_timeout: float,
    total_timeout: float,
) -> None:
    if progress_path.exists():
        progress_path.unlink()

    child = subprocess.Popen(
        cmd,
        cwd=str(APP_DIR),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=(os.name != "nt"),
        creationflags=_creationflags(),
    )

    child_started = time.time()
    last_progress_epoch = child_started
    last_signature = None

    while True:
        rc = child.poll()
        progress = _read_json(progress_path)
        now = time.time()

        if progress:
            signature = (
                progress.get("stage"),
                progress.get("percent"),
                progress.get("message"),
            )
            updated = float(progress.get("updated_at_epoch", now) or now)
            if signature != last_signature:
                last_signature = signature
                last_progress_epoch = updated
                _append_log(output_dir, str(progress.get("message", "")))

            child_percent = float(progress.get("percent", 0.0) or 0.0)
            overall = overall_start + overall_span * max(0.0, min(1.0, child_percent))
            _status(
                output_dir,
                {
                    "state": "running",
                    "stage": f"{stage_prefix}:{progress.get('stage', 'running')}",
                    "message": str(progress.get("message", "Traitement en cours…")),
                    "percent": round(overall, 4),
                    "child_pid": int(child.pid),
                    "child_elapsed_seconds": progress.get("elapsed_seconds"),
                    "chunk_index": progress.get("chunk_index"),
                    "chunk_total": progress.get("chunk_total"),
                },
                started=started,
            )

        if rc is not None:
            break

        if now - child_started > float(total_timeout):
            child.kill()
            child.wait(timeout=10)
            raise RuntimeError(
                f"Watchdog {stage_prefix} : durée totale dépassée "
                f"({total_timeout:.0f}s)."
            )

        if now - last_progress_epoch > float(inactivity_timeout):
            child.kill()
            child.wait(timeout=10)
            stuck = _read_json(progress_path)
            raise RuntimeError(
                f"Watchdog {stage_prefix} : aucun progrès depuis "
                f"{inactivity_timeout:.0f}s. "
                f"Dernière étape={stuck.get('stage')!r}."
            )

        time.sleep(1.0)

    if child.returncode != 0:
        progress = _read_json(progress_path)
        raise RuntimeError(
            f"{stage_prefix} échoué : "
            + str(progress.get("message", f"code {child.returncode}"))
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vocals", required=True)
    parser.add_argument("--drums", required=True)
    parser.add_argument("--structure", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--rhythm-inactivity-timeout", type=float, default=90.0)
    parser.add_argument("--rhythm-timeout", type=float, default=300.0)
    parser.add_argument("--vocal-inactivity-timeout", type=float, default=120.0)
    parser.add_argument("--vocal-timeout", type=float, default=900.0)
    args = parser.parse_args()

    vocals_path = Path(args.vocals)
    drums_path = Path(args.drums)
    structure_path = Path(args.structure)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    started = time.time()

    try:
        _append_log(output_dir, "MIDI worker start")
        structure = _read_json(structure_path)
        tempo = float(structure.get("tempo", 0.0) or 0.0)
        beats_per_bar = int(structure.get("beats_per_bar", 4) or 4)

        rhythm_json = output_dir / "drum_analysis.json"
        rhythm_progress = output_dir / "rhythm_progress.json"
        if rhythm_json.exists():
            rhythm_json.unlink()

        _status(
            output_dir,
            {
                "state": "running",
                "stage": "rhythm:start",
                "message": "Étape MIDI 1/2 : batterie + accords — démarrage.",
                "percent": 0.01,
            },
            started=started,
        )

        _run_child_with_watchdog(
            cmd=[
                sys.executable, "-m", "ezscore.analysis.stem_rhythm_worker",
                "--drums", str(drums_path),
                "--output-json", str(rhythm_json),
                "--progress-json", str(rhythm_progress),
            ],
            progress_path=rhythm_progress,
            output_dir=output_dir,
            started=started,
            stage_prefix="rhythm",
            overall_start=0.02,
            overall_span=0.18,
            inactivity_timeout=float(args.rhythm_inactivity_timeout),
            total_timeout=float(args.rhythm_timeout),
        )

        drum_analysis = _read_json(rhythm_json)
        if not drum_analysis or "beats" not in drum_analysis:
            raise RuntimeError("Analyse batterie terminée sans drum_analysis.json valide.")

        if tempo <= 1.0:
            tempo = float(drum_analysis.get("tempo", 0.0) or 120.0)

        _status(
            output_dir,
            {
                "state": "running",
                "stage": "rhythm:midi_write",
                "message": "Étape MIDI 1/2 : écriture Accords + Batterie.",
                "percent": 0.22,
            },
            started=started,
        )

        chords_path = output_dir / "chords.mid"
        drums_out = output_dir / "drums.mid"
        chords_path.write_bytes(build_chord_midi(structure, tempo=tempo))
        drums_out.write_bytes(
            build_drum_midi(
                drum_analysis,
                tempo=tempo,
                beats_per_bar=beats_per_bar,
            )
        )
        _append_log(output_dir, "Chords + drums MIDI ready")

        vocal_json = output_dir / "vocal_analysis.json"
        vocal_progress = output_dir / "vocal_progress.json"
        if vocal_json.exists():
            vocal_json.unlink()

        _run_child_with_watchdog(
            cmd=[
                sys.executable, "-m", "ezscore.analysis.stem_vocal_worker",
                "--vocals", str(vocals_path),
                "--output-json", str(vocal_json),
                "--progress-json", str(vocal_progress),
                "--chunk-seconds", "20",
            ],
            progress_path=vocal_progress,
            output_dir=output_dir,
            started=started,
            stage_prefix="vocal",
            overall_start=0.25,
            overall_span=0.65,
            inactivity_timeout=float(args.vocal_inactivity_timeout),
            total_timeout=float(args.vocal_timeout),
        )

        vocal = _read_json(vocal_json)
        if not vocal or "notes" not in vocal:
            raise RuntimeError("Analyse chant terminée sans vocal_analysis.json valide.")

        _status(
            output_dir,
            {
                "state": "running",
                "stage": "midi_render",
                "message": "Finalisation MIDI : Chant + fichier combiné.",
                "percent": 0.92,
            },
            started=started,
        )

        vocal_out = output_dir / "vocal.mid"
        combined_out = output_dir / "stem_mix.mid"
        vocal_out.write_bytes(build_vocal_midi(vocal["notes"], tempo=tempo))
        combined_out.write_bytes(
            build_combined_midi(
                vocal_notes=vocal["notes"],
                structure=structure,
                drum_analysis=drum_analysis,
                tempo=tempo,
                beats_per_bar=beats_per_bar,
            )
        )

        browser_events = browser_events_from_bundle(
            vocal_notes=vocal["notes"],
            structure=structure,
            drum_analysis=drum_analysis,
            beats_per_bar=beats_per_bar,
        )

        metadata = {
            "state": "complete",
            "timebase": "original_audio_seconds",
            "tempo": tempo,
            "beats_per_bar": beats_per_bar,
            "vocal_note_count": int(vocal.get("note_count", 0)),
            "drum_beat_count": int(drum_analysis.get("beat_count", 0)),
            "available_tracks": ["vocal", "chords", "drums"],
            "pending_tracks": [],
            "files": {
                "vocal": vocal_out.name,
                "chords": chords_path.name,
                "drums": drums_out.name,
                "combined": combined_out.name,
            },
            "browser_events": browser_events,
            "vocal_analysis": vocal,
            "drum_analysis": drum_analysis,
        }
        _atomic_json(output_dir / "stem_midi.json", metadata)

        _append_log(output_dir, "MIDI bundle complete")
        _status(
            output_dir,
            {
                "state": "done",
                "stage": "done",
                "message": "MIDI Chant + Accords + Batterie terminés.",
                "percent": 1.0,
                "vocal_note_count": int(vocal.get("note_count", 0)),
                "drum_beat_count": int(drum_analysis.get("beat_count", 0)),
            },
            started=started,
        )
        return 0

    except Exception as exc:
        _append_log(output_dir, "ERROR: " + str(exc))
        _status(
            output_dir,
            {
                "state": "error",
                "stage": "error",
                "message": str(exc),
                "traceback": traceback.format_exc(),
            },
            started=started,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
