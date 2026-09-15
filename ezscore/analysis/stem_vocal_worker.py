from __future__ import annotations

import argparse
import json
import os
import time
import traceback
from pathlib import Path

from ezscore.analysis.stem_midi import analyze_vocal_notes


def _atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vocals", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--progress-json", required=True)
    parser.add_argument("--chunk-seconds", type=float, default=20.0)
    args = parser.parse_args()

    vocals = Path(args.vocals)
    output_json = Path(args.output_json)
    progress_json = Path(args.progress_json)
    started = time.time()

    def progress(payload: dict) -> None:
        row = dict(payload)
        row.update({
            "pid": os.getpid(),
            "updated_at_epoch": time.time(),
            "elapsed_seconds": round(time.time() - started, 3),
        })
        _atomic_json(progress_json, row)

    try:
        progress({
            "stage": "vocal_worker_start",
            "message": "Processus d'analyse MIDI du chant démarré.",
            "percent": 0.0,
        })
        result = analyze_vocal_notes(
            vocals,
            chunk_seconds=float(args.chunk_seconds),
            progress_callback=progress,
        )
        _atomic_json(output_json, result)
        progress({
            "stage": "done",
            "message": f"Analyse chant terminée : {int(result.get('note_count', 0))} notes.",
            "percent": 1.0,
            "note_count": int(result.get("note_count", 0)),
        })
        return 0
    except Exception as exc:
        progress({
            "stage": "error",
            "message": str(exc),
            "traceback": traceback.format_exc(),
        })
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
