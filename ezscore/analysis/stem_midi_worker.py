from __future__ import annotations

import argparse
import json
import os
import traceback
from pathlib import Path

from ezscore.analysis.stem_midi import (
    analyze_drum_beats,
    analyze_vocal_notes,
    browser_events_from_bundle,
    build_chord_midi,
    build_combined_midi,
    build_drum_midi,
    build_vocal_midi,
)


def _write_json_atomic(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    tmp.replace(path)


def _write_status(output_dir: Path, payload: dict) -> None:
    _write_json_atomic(output_dir / "job_status.json", payload)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vocals", required=True)
    parser.add_argument("--drums", required=True)
    parser.add_argument("--structure", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    vocals_path = Path(args.vocals)
    drums_path = Path(args.drums)
    structure_path = Path(args.structure)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        structure = json.loads(structure_path.read_text(encoding="utf-8"))
        tempo = float(structure.get("tempo", 0.0) or 0.0)
        beats_per_bar = int(structure.get("beats_per_bar", 4) or 4)

        _write_status(
            output_dir,
            {
                "state": "running",
                "pid": os.getpid(),
                "stage": "drums_chords",
                "message": "Étape 1/2 : accords + batterie MIDI…",
            },
        )

        drum_analysis = analyze_drum_beats(drums_path)
        if tempo <= 1.0:
            tempo = float(drum_analysis.get("tempo", 0.0) or 120.0)

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

        # Publish an explicit PARTIAL bundle immediately.
        # This is not a fallback: vocal track is declared unavailable until step 2 finishes.
        partial_events = browser_events_from_bundle(
            vocal_notes=[],
            structure=structure,
            drum_analysis=drum_analysis,
            beats_per_bar=beats_per_bar,
        )
        partial = {
            "state": "partial",
            "timebase": "original_audio_seconds",
            "tempo": tempo,
            "beats_per_bar": beats_per_bar,
            "vocal_note_count": 0,
            "drum_beat_count": int(drum_analysis.get("beat_count", 0)),
            "available_tracks": ["chords", "drums"],
            "pending_tracks": ["vocal"],
            "files": {
                "vocal": None,
                "chords": chords_path.name,
                "drums": drums_out.name,
                "combined": None,
            },
            "browser_events": partial_events,
            "vocal_analysis": None,
            "drum_analysis": drum_analysis,
        }
        _write_json_atomic(output_dir / "stem_midi.json", partial)

        _write_status(
            output_dir,
            {
                "state": "running",
                "pid": os.getpid(),
                "stage": "vocal",
                "message": (
                    "Étape 1/2 prête : lecteur Accords + Batterie disponible. "
                    "Étape 2/2 : analyse MIDI du chant en cours…"
                ),
            },
        )

        vocal = analyze_vocal_notes(vocals_path)
        vocal_out = output_dir / "vocal.mid"
        combined_out = output_dir / "stem_mix.mid"

        vocal_out.write_bytes(
            build_vocal_midi(vocal["notes"], tempo=tempo)
        )
        combined_out.write_bytes(
            build_combined_midi(
                vocal_notes=vocal["notes"],
                structure=structure,
                drum_analysis=drum_analysis,
                tempo=tempo,
                beats_per_bar=beats_per_bar,
            )
        )

        full_events = browser_events_from_bundle(
            vocal_notes=vocal["notes"],
            structure=structure,
            drum_analysis=drum_analysis,
            beats_per_bar=beats_per_bar,
        )
        full = {
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
            "browser_events": full_events,
            "vocal_analysis": vocal,
            "drum_analysis": drum_analysis,
        }
        _write_json_atomic(output_dir / "stem_midi.json", full)

        _write_status(
            output_dir,
            {
                "state": "done",
                "pid": os.getpid(),
                "stage": "done",
                "message": "MIDI chant + accords + batterie prêts.",
                "vocal_note_count": int(vocal.get("note_count", 0)),
                "drum_beat_count": int(drum_analysis.get("beat_count", 0)),
            },
        )
        return 0

    except Exception as exc:
        _write_status(
            output_dir,
            {
                "state": "error",
                "pid": os.getpid(),
                "stage": "error",
                "message": str(exc),
                "traceback": traceback.format_exc(),
            },
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
