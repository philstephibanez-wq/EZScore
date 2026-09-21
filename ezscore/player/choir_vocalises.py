from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import re
import unicodedata
from typing import Any

import numpy as np


APP_DIR = Path(__file__).resolve().parents[2]
CHOIR_DISPLAY_LOG = APP_DIR / "data" / "logs" / "ezscore_choir_display.log"

_MIN_DURATION = 0.55
_MIN_GAP = 0.24
_EDGE = 0.18
_MAX_EVENTS = 48


def _log(event: str, **fields: Any) -> None:
    try:
        CHOIR_DISPLAY_LOG.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "event": str(event),
        }
        payload.update(fields)
        with CHOIR_DISPLAY_LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")
    except Exception:
        pass


def _letters(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(text or ""))
    return "".join(
        c.lower() for c in normalized if c.isascii() and c.isalpha()
    )


def _label(text: str) -> str | None:
    letters = _letters(text)
    if not letters:
        return None

    direct = {
        "oh": "Ho", "ooh": "Ho", "oooh": "Ho", "ho": "Ho", "hoo": "Ho",
        "ah": "Ah", "aah": "Ah", "ha": "Ah",
        "eh": "Eh", "he": "Eh",
    }
    if letters in direct:
        return direct[letters]

    counts: dict[str, int] = {}
    for char in letters:
        counts[char] = counts.get(char, 0) + 1
    dominant, count = max(counts.items(), key=lambda item: item[1])
    ratio = count / max(1, len(letters))

    if len(letters) >= 4 and dominant in "aeiouy" and ratio >= 0.68:
        return {
            "o": "Ho",
            "a": "Ah",
            "e": "Eh",
            "i": "Ih",
            "u": "Ouh",
            "y": "Ih",
        }[dominant]

    if re.fullmatch(r"h?[aeiouy]{1,3}h*", letters):
        vowel = next((c for c in letters if c in "aeiouy"), "")
        return {
            "o": "Ho", "a": "Ah", "e": "Eh",
            "i": "Ih", "u": "Ouh", "y": "Ih",
        }.get(vowel)

    return None


def _cluster(values: list[float]) -> list[float]:
    result: list[float] = []
    for value in sorted(float(x) for x in values if np.isfinite(x)):
        if not result or value - result[-1] >= _MIN_GAP:
            result.append(value)
    return result[:_MAX_EVENTS]


def _candidate_attacks(
    *,
    y: np.ndarray,
    sr: int,
    start: float,
    end: float,
) -> tuple[list[float], dict[str, Any]]:
    import librosa

    hop = 160
    i0 = max(0, int((start - _EDGE) * sr))
    i1 = min(len(y), int((end + _EDGE) * sr))
    segment = np.asarray(y[i0:i1], dtype=np.float32)
    offset = i0 / float(sr)
    if segment.size < 2048:
        return [], {"reason": "segment_too_short"}

    onset_env = np.asarray(
        librosa.onset.onset_strength(
            y=segment,
            sr=sr,
            hop_length=hop,
            aggregate=np.median,
        ),
        dtype=float,
    )
    rms = np.asarray(
        librosa.feature.rms(
            y=segment,
            frame_length=1024,
            hop_length=hop,
        )[0],
        dtype=float,
    )

    attacks: list[float] = []

    primary = librosa.onset.onset_detect(
        onset_envelope=onset_env,
        sr=sr,
        hop_length=hop,
        units="time",
        backtrack=True,
        pre_max=2,
        post_max=2,
        pre_avg=5,
        post_avg=5,
        delta=0.035,
        wait=2,
    )
    attacks.extend(offset + float(x) for x in np.asarray(primary).reshape(-1))

    finite = onset_env[np.isfinite(onset_env)]
    if finite.size:
        threshold = max(
            float(np.percentile(finite, 48)),
            float(np.mean(finite) + 0.05 * np.std(finite)),
        )
        min_frames = max(1, int(round(_MIN_GAP * sr / hop)))
        last = -10000
        for i in range(1, len(onset_env) - 1):
            value = float(onset_env[i])
            if (
                value >= threshold
                and value >= float(onset_env[i - 1])
                and value >= float(onset_env[i + 1])
            ):
                if i - last >= min_frames:
                    attacks.append(offset + i * hop / float(sr))
                    last = i

    if len(rms) >= 4:
        dr = np.diff(rms, prepend=rms[0])
        positive = dr[dr > 0]
        if positive.size:
            threshold = float(np.percentile(positive, 60))
            min_frames = max(1, int(round(_MIN_GAP * sr / hop)))
            last = -10000
            for i in range(1, len(dr) - 1):
                value = float(dr[i])
                if (
                    value >= threshold
                    and value >= float(dr[i - 1])
                    and value >= float(dr[i + 1])
                ):
                    if i - last >= min_frames:
                        attacks.append(offset + i * hop / float(sr))
                        last = i

    attacks = [
        x for x in _cluster(attacks)
        if start - _EDGE <= x <= end + _EDGE
    ]

    return attacks, {
        "attack_count": len(attacks),
        "segment_seconds": round(segment.size / float(sr), 3),
        "onset_env_peak": round(float(np.max(onset_env)) if onset_env.size else 0.0, 6),
        "rms_peak": round(float(np.max(rms)) if rms.size else 0.0, 6),
    }


def _split_word(
    word: dict[str, Any],
    *,
    attacks: list[float],
) -> list[dict[str, Any]]:
    text = str(word.get("text", "") or "").strip()
    label = _label(text)
    start = float(word.get("start", 0.0) or 0.0)
    end = float(word.get("end", start) or start)
    if label is None or end - start < _MIN_DURATION:
        return []

    anchors = [
        max(start, min(end, float(x)))
        for x in attacks
        if start - _EDGE <= x <= end + _EDGE
    ]
    anchors = _cluster(anchors)

    if anchors and abs(anchors[0] - start) <= 0.28:
        anchors[0] = start

    if anchors and anchors[0] - start >= _MIN_GAP:
        anchors.insert(0, start)

    if len(anchors) < 2:
        return []

    result: list[dict[str, Any]] = []
    for index, event_start in enumerate(anchors):
        next_start = anchors[index + 1] if index + 1 < len(anchors) else end
        event_end = min(end, max(event_start + 0.08, next_start - 0.04))
        if event_end <= event_start:
            continue
        result.append({
            "text": label,
            "start": round(event_start, 6),
            "end": round(event_end, 6),
            "raw_start": round(start, 6),
            "raw_end": round(end, 6),
            "vocalise_split": True,
            "backing_activity": True,
            "snapped_to_backing": True,
        })
    return result if len(result) >= 2 else []


def _split_result_with_backing(
    words: list[dict[str, Any]],
    backing_path: Path,
    *,
    audio_hash: str,
) -> list[dict[str, Any]]:
    candidates = [
        word for word in words
        if _label(str(word.get("text", "") or "")) is not None
        and (
            float(word.get("end", word.get("start", 0.0)) or 0.0)
            - float(word.get("start", 0.0) or 0.0)
        ) >= _MIN_DURATION
    ]

    _log(
        "choir.display.input",
        audio_hash=audio_hash[:12],
        word_count=len(words),
        vocalise_candidate_count=len(candidates),
        candidates=[
            {
                "text": str(w.get("text", "") or ""),
                "start": round(float(w.get("start", 0.0) or 0.0), 3),
                "end": round(float(w.get("end", w.get("start", 0.0)) or 0.0), 3),
            }
            for w in candidates[:20]
        ],
    )

    if not candidates:
        return words

    import librosa
    y, sr = librosa.load(str(backing_path), sr=16000, mono=True)
    if y.size == 0:
        _log("choir.display.no_audio", audio_hash=audio_hash[:12])
        return words

    output: list[dict[str, Any]] = []
    split_count = 0

    for word in words:
        text = str(word.get("text", "") or "").strip()
        start = float(word.get("start", 0.0) or 0.0)
        end = float(word.get("end", start) or start)

        if _label(text) is None or end - start < _MIN_DURATION:
            output.append(word)
            continue

        attacks, metrics = _candidate_attacks(
            y=y, sr=sr, start=start, end=end
        )
        split = _split_word(word, attacks=attacks)

        _log(
            "choir.display.vocalise",
            audio_hash=audio_hash[:12],
            text=text,
            start=round(start, 3),
            end=round(end, 3),
            attacks=[round(x, 3) for x in attacks],
            split_count=len(split),
            **metrics,
        )

        if split:
            split_count += 1
            output.extend(split)
        else:
            output.append(word)

    output.sort(
        key=lambda item: (
            float(item.get("start", 0.0) or 0.0),
            float(item.get("end", item.get("start", 0.0)) or 0.0),
        )
    )

    _log(
        "choir.display.output",
        audio_hash=audio_hash[:12],
        input_count=len(words),
        output_count=len(output),
        vocalise_tokens_split=split_count,
        preview=[
            {
                "text": str(w.get("text", "") or ""),
                "start": round(float(w.get("start", 0.0) or 0.0), 3),
                "end": round(float(w.get("end", w.get("start", 0.0)) or 0.0), 3),
                "split": bool(w.get("vocalise_split", False)),
            }
            for w in output[:80]
        ],
    )
    return output


def install_choir_vocalise_patch() -> None:
    from ezscore.player import karaoke_stem_webaudio as base

    if getattr(base, "_ezscore_vocalise_patch_installed", False):
        return

    original = getattr(base, "_derive_choir_words_from_vocals", None)
    if original is None:
        _log("choir.patch.missing_base_function")
        return

    def wrapped(
        stems: dict[str, Path],
        preview_dir: Path,
        lead_words: list[dict[str, Any]],
        player_words: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        words = original(stems, preview_dir, lead_words, player_words)
        backing = stems.get("backing_vocals")
        audio_hash = Path(preview_dir).parent.name

        if backing is None or not Path(backing).is_file():
            _log(
                "choir.display.no_backing_stem",
                audio_hash=audio_hash[:12],
                word_count=len(words),
            )
            return words

        try:
            return _split_result_with_backing(
                list(words),
                Path(backing),
                audio_hash=audio_hash,
            )
        except Exception as exc:
            _log(
                "choir.display.error",
                audio_hash=audio_hash[:12],
                error_type=type(exc).__name__,
                error=str(exc),
            )
            return words

    base._derive_choir_words_from_vocals = wrapped
    base._ezscore_vocalise_patch_installed = True
    _log("choir.patch.installed")
