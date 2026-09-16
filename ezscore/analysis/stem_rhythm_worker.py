from __future__ import annotations

import argparse
import json
import os
import time
import traceback
from pathlib import Path

from ezscore.analysis.stem_midi import analyze_drum_beats


def _atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--drums", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--progress-json", required=True)
    args = parser.parse_args()

    drums = Path(args.drums)
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
            "stage": "rhythm_worker_start",
            "message": "Processus batterie/tempo démarré.",
            "percent": 0.0,
        })
        result = analyze_drum_beats(drums, progress_callback=progress)
        _atomic_json(output_json, result)
        progress({
            "stage": "done",
            "message": f"Batterie terminée : {int(result.get('beat_count', 0))} beats.",
            "percent": 1.0,
            "beat_count": int(result.get("beat_count", 0)),
            "tempo": result.get("tempo"),
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
