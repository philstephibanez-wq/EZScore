from __future__ import annotations

import argparse
import json
import os
import traceback
from pathlib import Path

from ezscore.analysis.stem_midi import generate_stem_midi_bundle


def _write_status(output_dir: Path, payload: dict) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "job_status.json"
    tmp = path.with_suffix(".tmp")
    tmp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    tmp.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vocals", required=True)
    parser.add_argument("--drums", required=True)
    parser.add_argument("--structure", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    vocals = Path(args.vocals)
    drums = Path(args.drums)
    structure_path = Path(args.structure)
    output_dir = Path(args.output)

    try:
        _write_status(
            output_dir,
            {
                "state": "running",
                "pid": os.getpid(),
                "stage": "analysis",
                "message": "Analyse chant + batterie + accords en cours…",
            },
        )
        structure = json.loads(structure_path.read_text(encoding="utf-8"))
        metadata = generate_stem_midi_bundle(
            vocals_path=vocals,
            drums_path=drums,
            structure=structure,
            output_dir=output_dir,
        )
        _write_status(
            output_dir,
            {
                "state": "done",
                "pid": os.getpid(),
                "stage": "done",
                "message": "MIDI chant + accords + batterie prêts.",
                "vocal_note_count": int(metadata.get("vocal_note_count", 0)),
                "drum_beat_count": int(metadata.get("drum_beat_count", 0)),
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
