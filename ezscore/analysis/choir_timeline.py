from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import re
import unicodedata
from typing import Any

import librosa
import numpy as np

from ezscore.analysis.choirs import choir_analysis_path, load_choir_analysis


TIMELINE_ALIGNMENT_VERSION = 1
TARGET_SR = 16000
HOP = 160
MIN_ATTACK_GAP = 0.24
EDGE_SECONDS = 0.20
VOCALISE_MIN_SECONDS = 0.55


def _source_signature(path: Path) -> dict[str, int | str]:
    stat = path.stat()
    return {
        "path": str(path),
        "size": int(stat.st_size),
        "mtime_ns": int(stat.st_mtime_ns),
    }


def _letters(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(text or ""))
    return "".join(
        char.lower()
        for char in normalized
        if char.isascii() and char.isalpha()
    )


def _vocalise_label(text: str) -> str | None:
    letters = _letters(text)
    if not letters:
        return None

    direct = {
        "oh": "Ho", "ooh": "Ho", "oooh": "Ho",
        "ho": "Ho", "hoo": "Ho",
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
            "o": "Ho", "a": "Ah", "e": "Eh",
            "i": "Ih", "u": "Ouh", "y": "Ih",
        }[dominant]

    if re.fullmatch(r"h?[aeiouy]{1,3}h*", letters):
        vowel = next((char for char in letters if char in "aeiouy"), "")
        return {
            "o": "Ho", "a": "Ah", "e": "Eh",
            "i": "Ih", "u": "Ouh", "y": "Ih",
        }.get(vowel)

    return None


def _cluster(values: list[float]) -> list[float]:
    result: list[float] = []
    for value in sorted(float(x) for x in values if np.isfinite(x)):
        if not result or value - result[-1] >= MIN_ATTACK_GAP:
            result.append(value)
    return result


def _rms_active_at(rms: np.ndarray, *, time_seconds: float, sr: int) -> bool:
    if rms.size == 0:
        return False
    frame = int(round(float(time_seconds) * sr / HOP))
    frame = max(0, min(len(rms) - 1, frame))
    lo = max(0, frame - 2)
    hi = min(len(rms), frame + 3)
    local = float(np.max(rms[lo:hi])) if hi > lo else 0.0
    positive = rms[rms > 1e-8]
    if positive.size == 0:
        return False
    threshold = float(np.percentile(positive, 25)) * 0.70
    return local >= max(1e-8, threshold)


def _all_backing_attacks(y: np.ndarray, *, sr: int) -> tuple[list[float], np.ndarray]:
    onset_env = np.asarray(
        librosa.onset.onset_strength(
            y=y,
            sr=sr,
            hop_length=HOP,
            aggregate=np.median,
        ),
        dtype=float,
    )
    rms = np.asarray(
        librosa.feature.rms(
            y=y,
            frame_length=1024,
            hop_length=HOP,
        )[0],
        dtype=float,
    )

    attacks: list[float] = []
    primary = librosa.onset.onset_detect(
        onset_envelope=onset_env,
        sr=sr,
        hop_length=HOP,
        units="time",
        backtrack=True,
        pre_max=2,
        post_max=2,
        pre_avg=5,
        post_avg=5,
        delta=0.035,
        wait=2,
    )
    attacks.extend(float(x) for x in np.asarray(primary).reshape(-1))

    finite = onset_env[np.isfinite(onset_env)]
    if finite.size:
        threshold = max(
            float(np.percentile(finite, 48)),
            float(np.mean(finite) + 0.05 * np.std(finite)),
        )
        min_frames = max(1, int(round(MIN_ATTACK_GAP * sr / HOP)))
        last = -100000
        for index in range(1, len(onset_env) - 1):
            value = float(onset_env[index])
            if (
                value >= threshold
                and value >= float(onset_env[index - 1])
                and value >= float(onset_env[index + 1])
            ):
                if index - last >= min_frames:
                    attacks.append(index * HOP / float(sr))
                    last = index

    if rms.size >= 4:
        delta = np.diff(rms, prepend=rms[0])
        positive = delta[delta > 0]
        if positive.size:
            threshold = float(np.percentile(positive, 60))
            min_frames = max(1, int(round(MIN_ATTACK_GAP * sr / HOP)))
            last = -100000
            for index in range(1, len(delta) - 1):
                value = float(delta[index])
                if (
                    value >= threshold
                    and value >= float(delta[index - 1])
                    and value >= float(delta[index + 1])
                ):
                    if index - last >= min_frames:
                        attacks.append(index * HOP / float(sr))
                        last = index

    return _cluster(attacks), rms


def _phrase_map(payload: dict[str, Any]) -> dict[int, dict[str, Any]]:
    result: dict[int, dict[str, Any]] = {}
    for phrase in list(payload.get("phrases", []) or []):
        try:
            index = int(phrase.get("index"))
        except (TypeError, ValueError):
            continue
        result[index] = dict(phrase)
    return result


def _words_by_phrase(words: list[dict[str, Any]]) -> dict[int, list[dict[str, Any]]]:
    result: dict[int, list[dict[str, Any]]] = {}
    for word in words:
        try:
            index = int(word.get("phrase_index"))
        except (TypeError, ValueError):
            continue
        result.setdefault(index, []).append(word)
    for group in result.values():
        group.sort(
            key=lambda item: (
                float(item.get("start", 0.0) or 0.0),
                float(item.get("end", item.get("start", 0.0)) or 0.0),
            )
        )
    return result


def _vocalise_domain(
    word: dict[str, Any],
    *,
    phrase: dict[str, Any] | None,
    siblings: list[dict[str, Any]],
) -> tuple[float, float]:
    start = float(word.get("start", 0.0) or 0.0)
    end = float(word.get("end", start) or start)
    phrase_start = (
        float(phrase.get("start", start) or start)
        if phrase is not None else start
    )
    phrase_end = (
        float(phrase.get("end", end) or end)
        if phrase is not None else end
    )

    previous = None
    following = None
    for candidate in siblings:
        if candidate is word:
            continue
        candidate_start = float(candidate.get("start", 0.0) or 0.0)
        candidate_end = float(candidate.get("end", candidate_start) or candidate_start)
        if candidate_end <= start:
            previous = candidate
        elif candidate_start >= end and following is None:
            following = candidate

    left = phrase_start
    if previous is not None:
        previous_end = float(previous.get("end", previous.get("start", start)) or start)
        left = max(phrase_start, (previous_end + start) / 2.0)

    right = phrase_end
    if following is not None:
        following_start = float(following.get("start", end) or end)
        right = min(phrase_end, (end + following_start) / 2.0)

    left = max(0.0, min(left, start))
    right = max(end, right)
    return left, right


def _split_vocalise(
    word: dict[str, Any],
    *,
    domain_start: float,
    domain_end: float,
    attacks: list[float],
    rms: np.ndarray,
    sr: int,
) -> list[dict[str, Any]]:
    label = _vocalise_label(str(word.get("text", "") or ""))
    if label is None:
        return []

    domain_start = max(0.0, float(domain_start))
    domain_end = max(domain_start, float(domain_end))
    if domain_end - domain_start < VOCALISE_MIN_SECONDS:
        return []

    anchors = [
        float(value)
        for value in attacks
        if domain_start - EDGE_SECONDS <= float(value) <= domain_end + EDGE_SECONDS
    ]
    anchors = [
        max(domain_start, min(domain_end, value))
        for value in _cluster(anchors)
    ]

    if (
        _rms_active_at(rms, time_seconds=domain_start, sr=sr)
        and (not anchors or anchors[0] - domain_start >= MIN_ATTACK_GAP)
    ):
        anchors.insert(0, domain_start)

    anchors = _cluster(anchors)
    if len(anchors) < 2:
        return []

    result: list[dict[str, Any]] = []
    for index, event_start in enumerate(anchors):
        next_start = anchors[index + 1] if index + 1 < len(anchors) else domain_end
        event_end = min(
            domain_end,
            max(event_start + 0.08, next_start - 0.04),
        )
        if event_end <= event_start:
            continue

        item = deepcopy(word)
        item.update({
            "text": label,
            "start": round(event_start, 6),
            "end": round(event_end, 6),
            "recognized_start": float(word.get("start", 0.0) or 0.0),
            "recognized_end": float(
                word.get("end", word.get("start", 0.0)) or 0.0
            ),
            "timeline_source": "backing_vocals",
            "timeline_kind": "vocalise_attack",
        })
        result.append(item)

    return result if len(result) >= 2 else []


def timeline_alignment_is_current(audio_hash: str) -> bool:
    payload = load_choir_analysis(audio_hash)
    if payload is None:
        return False

    metadata = dict(payload.get("timeline_alignment", {}) or {})
    if int(metadata.get("version", 0) or 0) != TIMELINE_ALIGNMENT_VERSION:
        return False

    backing = Path(str(payload.get("source", "") or ""))
    if not backing.is_file():
        return False

    return dict(metadata.get("backing_signature", {}) or {}) == _source_signature(backing)


def align_choir_timeline(audio_hash: str, *, force: bool = False) -> dict[str, Any] | None:
    payload = load_choir_analysis(audio_hash)
    if payload is None:
        return None

    if not force and timeline_alignment_is_current(audio_hash):
        return payload

    backing = Path(str(payload.get("source", "") or ""))
    if not backing.is_file():
        return payload

    y, sr = librosa.load(str(backing), sr=TARGET_SR, mono=True)
    y = np.asarray(y, dtype=np.float32)
    if y.size == 0:
        return payload

    attacks, rms = _all_backing_attacks(y, sr=sr)

    recognized = list(
        payload.get("recognized_words", [])
        or payload.get("words", [])
        or []
    )
    recognized = [deepcopy(word) for word in recognized]

    phrases = _phrase_map(payload)
    groups = _words_by_phrase(recognized)
    timeline_words: list[dict[str, Any]] = []
    vocalise_source_count = 0
    vocalise_event_count = 0

    for word in recognized:
        start = float(word.get("start", 0.0) or 0.0)
        end = float(word.get("end", start) or start)
        label = _vocalise_label(str(word.get("text", "") or ""))

        if label is None or end - start < VOCALISE_MIN_SECONDS:
            item = deepcopy(word)
            item["timeline_source"] = "backing_whisper"
            item["timeline_kind"] = "word"
            timeline_words.append(item)
            continue

        try:
            phrase_index = int(word.get("phrase_index"))
        except (TypeError, ValueError):
            phrase_index = -1

        phrase = phrases.get(phrase_index)
        siblings = groups.get(phrase_index, [word])
        domain_start, domain_end = _vocalise_domain(
            word,
            phrase=phrase,
            siblings=siblings,
        )

        split = _split_vocalise(
            word,
            domain_start=domain_start,
            domain_end=domain_end,
            attacks=attacks,
            rms=rms,
            sr=sr,
        )

        if split:
            vocalise_source_count += 1
            vocalise_event_count += len(split)
            timeline_words.extend(split)
        else:
            item = deepcopy(word)
            item["timeline_source"] = "backing_whisper"
            item["timeline_kind"] = "vocalise_unsplit"
            timeline_words.append(item)

    timeline_words.sort(
        key=lambda item: (
            float(item.get("start", 0.0) or 0.0),
            float(item.get("end", item.get("start", 0.0)) or 0.0),
            str(item.get("text", "") or ""),
        )
    )

    payload = dict(payload)
    payload["recognized_words"] = recognized
    payload["words"] = timeline_words
    payload["word_count"] = len(timeline_words)
    payload["timebase"] = "original_audio_seconds"
    payload["timeline_alignment"] = {
        "version": TIMELINE_ALIGNMENT_VERSION,
        "authority": "original_audio_seconds",
        "backing_timing_source": "backing_vocals",
        "lead_used_for_timing": False,
        "backing_signature": _source_signature(backing),
        "detected_attack_count": len(attacks),
        "recognized_word_count": len(recognized),
        "timeline_word_count": len(timeline_words),
        "vocalise_source_count": vocalise_source_count,
        "vocalise_event_count": vocalise_event_count,
    }

    output = choir_analysis_path(audio_hash)
    output.parent.mkdir(parents=True, exist_ok=True)
    temp = output.with_suffix(".timeline.tmp")
    temp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temp.replace(output)
    return payload
