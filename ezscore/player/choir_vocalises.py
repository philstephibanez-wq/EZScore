from __future__ import annotations

from pathlib import Path
import re
import unicodedata
from typing import Any, Iterable

import numpy as np


_MIN_VOCALISE_DURATION = 1.10
_MIN_ONSET_GAP = 0.24
_EDGE_TOLERANCE = 0.18
_MAX_EVENTS = 32


def _ascii_letters(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(text or ""))
    return "".join(
        ch.lower()
        for ch in normalized
        if ch.isascii() and ch.isalpha()
    )


def _vocalise_label(text: str) -> str | None:
    letters = _ascii_letters(text)
    if not letters:
        return None

    known = {
        "oh": "Ho", "ooh": "Ho", "oooh": "Ho",
        "ho": "Ho", "hoo": "Ho",
        "ah": "Ah", "aah": "Ah", "ha": "Ah",
        "eh": "Eh", "he": "Eh",
    }
    if letters in known:
        return known[letters]

    counts: dict[str, int] = {}
    for char in letters:
        counts[char] = counts.get(char, 0) + 1
    dominant, dominant_count = max(counts.items(), key=lambda item: item[1])
    ratio = dominant_count / max(1, len(letters))

    if len(letters) >= 4 and dominant in "aeiouy" and ratio >= 0.72:
        return {
            "o": "Ho",
            "a": "Ah",
            "e": "Eh",
            "i": "Ih",
            "u": "Ouh",
            "y": "Ih",
        }[dominant]

    if re.fullmatch(r"h?[aeiouy]{1,3}h*", letters):
        vowel = next((ch for ch in letters if ch in "aeiouy"), "")
        return {
            "o": "Ho",
            "a": "Ah",
            "e": "Eh",
            "i": "Ih",
            "u": "Ouh",
            "y": "Ih",
        }.get(vowel)

    return None


def _cluster_onsets(values: Iterable[float]) -> list[float]:
    clustered: list[float] = []
    for value in sorted(float(x) for x in values if np.isfinite(x)):
        if not clustered or value - clustered[-1] >= _MIN_ONSET_GAP:
            clustered.append(value)
    return clustered[:_MAX_EVENTS]


def split_long_vocalise(
    *,
    text: str,
    raw_start: float,
    raw_end: float,
    onset_times: np.ndarray,
    has_backing_activity: bool,
) -> list[dict[str, Any]]:
    start = float(raw_start)
    end = float(raw_end)
    duration = max(0.0, end - start)
    label = _vocalise_label(text)

    if (
        not has_backing_activity
        or label is None
        or duration < _MIN_VOCALISE_DURATION
        or onset_times.size == 0
    ):
        return []

    local = onset_times[
        (onset_times >= max(0.0, start - _EDGE_TOLERANCE))
        & (onset_times <= end + _EDGE_TOLERANCE)
    ]
    anchors = _cluster_onsets(local.tolist())
    anchors = [
        max(start, min(end, value))
        for value in anchors
        if start - _EDGE_TOLERANCE <= value <= end + _EDGE_TOLERANCE
    ]
    anchors = _cluster_onsets(anchors)

    if anchors and abs(anchors[0] - start) <= 0.22:
        anchors[0] = start

    if len(anchors) < 2:
        return []

    words: list[dict[str, Any]] = []
    for index, event_start in enumerate(anchors):
        next_start = anchors[index + 1] if index + 1 < len(anchors) else end
        event_end = min(end, max(event_start + 0.08, next_start - 0.035))
        if event_end <= event_start:
            continue
        words.append(
            {
                "text": label,
                "start": round(event_start, 6),
                "end": round(event_end, 6),
                "raw_start": round(start, 6),
                "raw_end": round(end, 6),
                "backing_activity": True,
                "snapped_to_backing": True,
                "vocalise_split": True,
            }
        )

    return words if len(words) >= 2 else []


def _split_result_with_backing(
    words: list[dict[str, Any]],
    backing_path: Path,
) -> list[dict[str, Any]]:
    candidates = [
        word
        for word in words
        if (
            float(word.get("end", word.get("start", 0.0)) or 0.0)
            - float(word.get("start", 0.0) or 0.0)
        ) >= _MIN_VOCALISE_DURATION
        and _vocalise_label(str(word.get("text", "") or "")) is not None
    ]
    if not candidates:
        return words

    import librosa

    y, sr = librosa.load(str(backing_path), sr=16000, mono=True)
    if y.size == 0:
        return words

    hop_length = 160
    onset_env = librosa.onset.onset_strength(
        y=y,
        sr=sr,
        hop_length=hop_length,
        aggregate=np.median,
    )
    onset_times = np.asarray(
        librosa.onset.onset_detect(
            onset_envelope=onset_env,
            sr=sr,
            hop_length=hop_length,
            units="time",
            backtrack=True,
            pre_max=3,
            post_max=3,
            pre_avg=8,
            post_avg=8,
            delta=0.08,
            wait=3,
        ),
        dtype=float,
    )
    onset_times = onset_times[np.isfinite(onset_times)]

    rms = np.asarray(
        librosa.feature.rms(y=y, frame_length=1024, hop_length=hop_length)[0],
        dtype=float,
    )
    rms_times = np.asarray(
        librosa.frames_to_time(
            np.arange(rms.size),
            sr=sr,
            hop_length=hop_length,
        ),
        dtype=float,
    )
    positive_rms = rms[rms > 1e-8]
    activity_floor = (
        float(np.percentile(positive_rms, 35))
        if positive_rms.size
        else 0.0
    )

    output: list[dict[str, Any]] = []
    for word in words:
        start = float(word.get("start", 0.0) or 0.0)
        end = float(word.get("end", start) or start)
        duration = max(0.0, end - start)

        if duration < _MIN_VOCALISE_DURATION or _vocalise_label(
            str(word.get("text", "") or "")
        ) is None:
            output.append(word)
            continue

        local_mask = (
            (rms_times >= max(0.0, start - 0.20))
            & (rms_times <= end + 0.20)
        )
        local_peak = float(np.max(rms[local_mask])) if np.any(local_mask) else 0.0
        active = (
            local_peak > 0.0
            and (
                activity_floor <= 0.0
                or local_peak >= activity_floor * 1.15
            )
        )

        split = split_long_vocalise(
            text=str(word.get("text", "") or ""),
            raw_start=start,
            raw_end=end,
            onset_times=onset_times,
            has_backing_activity=active,
        )
        if split:
            output.extend(split)
        else:
            output.append(word)

    return sorted(
        output,
        key=lambda item: (
            float(item.get("start", 0.0) or 0.0),
            float(item.get("end", item.get("start", 0.0)) or 0.0),
        ),
    )


def install_choir_vocalise_patch() -> None:
    from ezscore.player import karaoke_stem_webaudio as base

    if getattr(base, "_ezscore_vocalise_patch_installed", False):
        return

    original = getattr(base, "_derive_choir_words_from_vocals", None)
    if original is None:
        return

    def wrapped(
        stems: dict[str, Path],
        preview_dir: Path,
        lead_words: list[dict[str, Any]],
        player_words: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        words = original(stems, preview_dir, lead_words, player_words)

        backing = stems.get("backing_vocals")
        if backing is None:
            return words

        backing_path = Path(backing)
        if not backing_path.is_file():
            return words

        try:
            return _split_result_with_backing(list(words), backing_path)
        except Exception:
            return words

    base._derive_choir_words_from_vocals = wrapped
    base._ezscore_vocalise_patch_installed = True
