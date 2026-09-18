from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from ezscore.analysis.rhythm_intro_fusion import (
    has_instrumental_prefix,
    merge_intro_beats,
)


def install(stem_module) -> None:
    if getattr(stem_module, "_EZ_INTRO_RHYTHM_FUSION", False):
        return

    def analyze_structure_with_intro(
        *,
        audio_hash: str,
        stems: dict[str, Path],
        meter: dict,
    ) -> dict:
        drums_path = Path(stems["drums"])
        song = stem_module._song_for_hash(audio_hash)
        source = stem_module._source_path(audio_hash, song)
        if source is None or not source.is_file():
            raise RuntimeError(
                "Audio original introuvable pour l'analyse harmonique haute qualité."
            )

        drums_rhythm = None
        drums_error = None
        try:
            drums_rhythm = stem_module.analyze_quality_beats(drums_path)
        except Exception as exc:
            drums_error = exc

        drum_beats = np.asarray(
            list((drums_rhythm or {}).get("beats", []) or []),
            dtype=float,
        )
        first_drum = float(drum_beats[0]) if drum_beats.size else None

        need_mix = first_drum is None or first_drum > 1.0
        mix_rhythm = None
        if need_mix:
            try:
                mix_rhythm = stem_module.analyze_quality_beats(source)
            except Exception:
                mix_rhythm = None

        probe_duration = first_drum if first_drum is not None else 30.0
        instrumental_prefix = has_instrumental_prefix(
            stems,
            duration=max(0.25, probe_duration),
        )

        try:
            fused = merge_intro_beats(
                drums=drums_rhythm,
                mix=mix_rhythm,
                instrumental_prefix=instrumental_prefix,
            )
        except RuntimeError:
            if drums_error is not None and drums_rhythm is None:
                raise RuntimeError(
                    "Analyse rythmique batterie indisponible et aucune "
                    "pulsation instrumentale mix fiable n'a pu être retenue. "
                    f"Détail batterie : {drums_error}"
                ) from drums_error
            raise

        beat_times = np.asarray(fused.beats, dtype=float)
        tempo_value = float(fused.tempo)

        chord_payload = stem_module.analyze_chords_absolute(
            source,
            cache_path=stem_module._chord_cache_path(audio_hash),
            force=False,
        )
        chord_segments = list(chord_payload.get("segments", []) or [])
        if not chord_segments:
            raise RuntimeError("Timeline harmonique lv-chordia vide.")

        beat_timeline = []
        for i, t0 in enumerate(beat_times):
            t1 = (
                float(beat_times[i + 1])
                if i + 1 < len(beat_times)
                else float(t0) + 60.0 / max(1.0, tempo_value)
            )
            chord, raw_chord, overlap = stem_module.chord_for_interval(
                chord_segments,
                float(t0),
                float(t1),
            )
            source_name = fused.sources[i] if i < len(fused.sources) else "drums"
            beat_timeline.append(
                {
                    "index": int(i),
                    "time": round(float(t0), 6),
                    "strength": 0.0,
                    "chord": chord,
                    "chord_raw": raw_chord,
                    "chord_overlap": round(float(overlap), 6),
                    "rhythm_engine": fused.engine,
                    "rhythm_source": source_name,
                    "harmony_engine": str(chord_payload.get("engine", "")),
                }
            )

        structure = stem_module._structure_from_beat_timeline(
            audio_hash=audio_hash,
            beat_timeline=beat_timeline,
            tempo=tempo_value,
            meter=meter,
        )
        structure["analysis_engines"] = {
            "stems": "bs-roformer-sw-6stems-v1",
            "rhythm": fused.engine,
            "harmony": str(chord_payload.get("engine", "")),
            "harmony_dictionary": str(chord_payload.get("dictionary", "")),
        }
        structure["rhythm_fusion"] = {
            "policy": "drums-primary-mix-intro-conservative",
            "intro_mix_beat_count": fused.intro_mix_beat_count,
            "first_drum_beat": fused.first_drum_beat,
            "instrumental_prefix": bool(instrumental_prefix),
            "invented_beats": 0,
        }
        structure["chord_segment_count"] = int(
            chord_payload.get("segment_count", len(chord_segments))
            or len(chord_segments)
        )

        stem_module._structure_cache_path(audio_hash).write_text(
            json.dumps(structure, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return structure

    stem_module._analyze_structure = analyze_structure_with_intro
    stem_module._EZ_INTRO_RHYTHM_FUSION = True
