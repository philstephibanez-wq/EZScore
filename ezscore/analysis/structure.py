"""Secondary visual-structure analysis for EZScore.

Canonical audio timestamps are owned by the primary timelines.
This module only proposes readable visual sections.

R33 strategy
------------
- work at measure level, not fixed 4-measure final blocks;
- search repeated harmonic phrases of variable length;
- prefer musically/readably useful phrases (roughly 8..24 measures);
- lyrics are only a secondary confidence cue;
- never rewrite chord / phoneme / lyric timestamps.
"""

from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any
import math

import numpy as np


ENGINE_TRACE = "VISUAL_STRUCTURE_R33"


def _normalize_measure_pattern(notation: str) -> str:
    value = str(notation or "").strip()
    if value.endswith("^"):
        value = value[:-1]
    return value


def _pattern_similarity(a: str, b: str) -> float:
    a = _normalize_measure_pattern(a)
    b = _normalize_measure_pattern(b)
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    return SequenceMatcher(None, a, b, autojunk=False).ratio()


def _phrase_similarity(patterns, a0: int, b0: int, length: int) -> tuple[float, float]:
    scores = [
        _pattern_similarity(patterns[a0 + k], patterns[b0 + k])
        for k in range(length)
    ]
    if not scores:
        return 0.0, 0.0
    return float(np.mean(scores)), float(np.min(scores))


def _lyrics_in_interval(
    lyrics_timeline: list[dict[str, Any]] | None,
    t0: float,
    t1: float,
) -> list[dict[str, Any]]:
    if not lyrics_timeline:
        return []
    return [
        item
        for item in lyrics_timeline
        if float(item.get("end", item.get("start", 0.0))) >= t0
        and float(item.get("start", 0.0)) <= t1
    ]


def _word_count_between(
    lyrics_timeline: list[dict[str, Any]] | None,
    t0: float,
    t1: float,
) -> int:
    return len(_lyrics_in_interval(lyrics_timeline, t0, t1))


def _readability_bonus(length: int) -> float:
    """Soft prior only; never a hard block size.

    12-16 measures are usually easier to read than 4-measure fragmentation,
    while 8 and 20+ remain perfectly possible when the harmonic evidence wins.
    """
    center = 14.0
    spread = 7.0
    return 0.045 * math.exp(-((float(length) - center) / spread) ** 2)


def _lyrics_density_bonus(word_count: int) -> float:
    """Very small secondary cue.

    A visual block containing a sensible phrase-sized amount of text gets a
    slight bonus. Instrumental sections are neutral, not penalized.
    """
    if word_count <= 0:
        return 0.0
    target = 28.0
    spread = 24.0
    return 0.018 * math.exp(-((float(word_count) - target) / spread) ** 2)


def _candidate_repeated_phrases(
    mesures: list[dict[str, Any]],
    lyrics_timeline: list[dict[str, Any]] | None,
    threshold: float,
) -> list[dict[str, Any]]:
    patterns = [_normalize_measure_pattern(m.get("notation", "")) for m in mesures]
    n = len(patterns)

    if n < 12:
        return []

    # Variable phrase sizes. 4 measures are deliberately NOT used as a final
    # phrase candidate: they remain a motif scale, not a visual section scale.
    min_len = 8 if n >= 24 else 6
    max_len = min(24, max(min_len, n // 2))

    candidates = []

    for length in range(min_len, max_len + 1):
        # all starts are allowed: no snapping to a 4-measure grid
        for a0 in range(0, n - length + 1):
            # repeated occurrences must not overlap
            for b0 in range(a0 + length, n - length + 1):
                avg, minimum = _phrase_similarity(patterns, a0, b0, length)

                if avg < threshold:
                    continue
                if minimum < max(0.28, threshold - 0.30):
                    continue

                a_t0 = float(mesures[a0]["debut"])
                a_t1 = float(mesures[a0 + length - 1]["fin"])
                b_t0 = float(mesures[b0]["debut"])
                b_t1 = float(mesures[b0 + length - 1]["fin"])

                words_a = _word_count_between(lyrics_timeline, a_t0, a_t1)
                words_b = _word_count_between(lyrics_timeline, b_t0, b_t1)

                # Harmonic evidence dominates. Readability and lyric density
                # only resolve close harmonic candidates.
                quality = (
                    avg
                    + _readability_bonus(length)
                    + 0.5 * (
                        _lyrics_density_bonus(words_a)
                        + _lyrics_density_bonus(words_b)
                    )
                )

                candidates.append({
                    "a0": a0,
                    "b0": b0,
                    "length": length,
                    "avg": avg,
                    "min": minimum,
                    "quality": quality,
                    "words_a": words_a,
                    "words_b": words_b,
                })

    # Keep maximal / useful matches first.
    candidates.sort(
        key=lambda c: (
            c["quality"],
            c["avg"],
            c["length"],
        ),
        reverse=True,
    )
    return candidates


def _select_repeat_anchors(candidates, measure_count: int) -> list[dict[str, Any]]:
    """Select a small coherent set of repeat anchors.

    This is the key anti-fragmentation rule: every possible harmonic match does
    NOT become a boundary.
    """
    selected = []
    used_repeat_starts = []
    used_ref_starts = []

    # Larger songs may need more sections, but keep the automatic proposal
    # deliberately conservative.
    max_anchors = max(2, min(8, measure_count // 12))

    for cand in candidates:
        a0 = int(cand["a0"])
        b0 = int(cand["b0"])
        length = int(cand["length"])

        # Near-duplicate starts describe the same phrase recurrence.
        if any(abs(b0 - x) < max(4, length // 3) for x in used_repeat_starts):
            continue
        if any(
            abs(a0 - x) < max(4, length // 3)
            and abs(b0 - y) < max(4, length // 3)
            for x, y in zip(used_ref_starts, used_repeat_starts)
        ):
            continue

        selected.append(cand)
        used_ref_starts.append(a0)
        used_repeat_starts.append(b0)

        if len(selected) >= max_anchors:
            break

    return selected


def _harmonic_boundary_strength(patterns, boundary: int, radius: int = 4) -> float:
    """Novelty around a proposed boundary, 0..1."""
    if boundary <= 0 or boundary >= len(patterns):
        return 1.0

    left0 = max(0, boundary - radius)
    right1 = min(len(patterns), boundary + radius)
    left = patterns[left0:boundary]
    right = patterns[boundary:right1]
    n = min(len(left), len(right))
    if n <= 0:
        return 0.0

    similarity = float(np.mean([
        _pattern_similarity(left[-n + i], right[i])
        for i in range(n)
    ]))
    return 1.0 - similarity


def _compact_boundaries(
    boundaries: list[dict[str, Any]],
    measure_count: int,
) -> list[int]:
    """Merge nearby competing boundaries instead of creating tiny sections."""
    if not boundaries:
        return [0]

    by_pos = {}
    for item in boundaries:
        pos = max(0, min(measure_count, int(item["pos"])))
        score = float(item.get("score", 0.0))
        reason = str(item.get("reason", ""))
        current = by_pos.get(pos)
        if current is None or score > current["score"]:
            by_pos[pos] = {"pos": pos, "score": score, "reason": reason}

    items = sorted(by_pos.values(), key=lambda x: x["pos"])
    result = []
    min_gap = 6

    for item in items:
        pos = item["pos"]
        if pos in (0, measure_count):
            if pos not in result:
                result.append(pos)
            continue

        if not result:
            result.append(pos)
            continue

        if pos - result[-1] < min_gap:
            # Keep the stronger of two nearby boundaries.
            previous_pos = result[-1]
            previous = by_pos.get(previous_pos, {"score": 0.0})
            if item["score"] > previous.get("score", 0.0):
                result[-1] = pos
        else:
            result.append(pos)

    if 0 not in result:
        result.insert(0, 0)
    if measure_count not in result:
        result.append(measure_count)

    result = sorted(set(result))

    # Avoid a tiny tail caused by a late anchor.
    if len(result) >= 3 and result[-1] - result[-2] < 4:
        del result[-2]

    return result


def _label_sections(
    sections: list[dict[str, Any]],
    patterns: list[str],
    threshold: float,
) -> None:
    """Assign neutral A/B/C families; no fake Verse/Chorus claim."""
    representatives = []

    for section in sections:
        a = int(section["_start0"])
        b = int(section["_end0"])
        current = patterns[a:b]

        best_idx = None
        best_score = 0.0

        for idx, rep in enumerate(representatives):
            n = min(len(current), len(rep))
            if n < 4:
                continue

            # Compare the common phrase, with a mild length penalty.
            seq_scores = [
                _pattern_similarity(current[i], rep[i])
                for i in range(n)
            ]
            score = float(np.mean(seq_scores))
            score *= min(len(current), len(rep)) / max(len(current), len(rep))

            if score > best_score:
                best_score = score
                best_idx = idx

        if best_idx is not None and best_score >= max(0.60, threshold - 0.06):
            cluster_idx = best_idx
        else:
            cluster_idx = len(representatives)
            representatives.append(current)

        label = chr(ord("A") + (cluster_idx % 26))
        section["cluster"] = label
        section["type"] = f"Bloc {label}"
        section["harmonic_repeat"] = float(best_score)


def detect_visual_blocks(
    mesures: list[dict[str, Any]],
    lyrics_timeline: list[dict[str, Any]] | None = None,
    similarity_threshold: float = 0.66,
) -> list[dict[str, Any]]:
    """Propose variable-length visual blocks from recurring chord phrases."""
    if not mesures:
        return []

    patterns = [_normalize_measure_pattern(m.get("notation", "")) for m in mesures]
    measure_count = len(mesures)
    threshold = float(np.clip(similarity_threshold, 0.45, 0.90))

    candidates = _candidate_repeated_phrases(
        mesures,
        lyrics_timeline,
        threshold,
    )
    selected = _select_repeat_anchors(candidates, measure_count)

    boundary_items = [
        {"pos": 0, "score": 1.0, "reason": "song-start"},
        {"pos": measure_count, "score": 1.0, "reason": "song-end"},
    ]

    for cand in selected:
        a0 = int(cand["a0"])
        b0 = int(cand["b0"])
        length = int(cand["length"])
        base = float(cand["avg"])

        for pos, reason in (
            (a0, "repeat-reference-start"),
            (b0, "repeat-return-start"),
            (a0 + length, "repeat-reference-end"),
            (b0 + length, "repeat-return-end"),
        ):
            if 0 < pos < measure_count:
                novelty = _harmonic_boundary_strength(patterns, pos)
                # A repeated phrase start is already meaningful; novelty only
                # strengthens it, never becomes the sole driver.
                score = base + 0.12 * novelty
                boundary_items.append({
                    "pos": pos,
                    "score": score,
                    "reason": reason,
                })

    boundaries = _compact_boundaries(boundary_items, measure_count)

    # If the song is highly repetitive and there is no reliable recurrence
    # boundary, do NOT fall back to 4-measure slicing.
    if len(boundaries) <= 2 and measure_count >= 20:
        # One conservative readability split at the strongest broad novelty,
        # only if it is actually visible in harmony.
        best_pos = None
        best_strength = 0.0
        for pos in range(8, measure_count - 7):
            strength = _harmonic_boundary_strength(patterns, pos, radius=6)
            if strength > best_strength:
                best_strength = strength
                best_pos = pos

        if best_pos is not None and best_strength >= 0.28:
            boundaries = [0, int(best_pos), measure_count]

    sections = []
    for index in range(len(boundaries) - 1):
        start0 = int(boundaries[index])
        end0 = int(boundaries[index + 1])
        if end0 <= start0:
            continue

        first = mesures[start0]
        last = mesures[end0 - 1]

        sections.append({
            "index": index,
            "measure_start": int(first["numero"]),
            "measure_end": int(last["numero"]),
            "time_start": float(first["debut"]),
            "time_end": float(last["fin"]),
            "confidence": (
                0.78 if selected else 0.48
            ),
            "visual_only": True,
            "measure_patterns": patterns[start0:end0],
            "_start0": start0,
            "_end0": end0,
        })

    _label_sections(sections, patterns, threshold)

    # Include vocal pre-roll / post-roll in the visual envelope only.
    # No word timestamp is modified.
    if sections and lyrics_timeline:
        lyric_starts = [
            float(w.get("start", 0.0))
            for w in lyrics_timeline
            if str(w.get("text", "") or "").strip()
        ]
        lyric_ends = [
            float(w.get("end", w.get("start", 0.0)))
            for w in lyrics_timeline
            if str(w.get("text", "") or "").strip()
        ]
        if lyric_starts:
            sections[0]["time_start"] = min(
                float(sections[0]["time_start"]),
                min(lyric_starts),
            )
        if lyric_ends:
            sections[-1]["time_end"] = max(
                float(sections[-1]["time_end"]),
                max(lyric_ends),
            )

    # Internal fields are diagnostic only.
    for section in sections:
        section.pop("_start0", None)
        section.pop("_end0", None)

    top_candidates = [
        (
            c["a0"] + 1,
            c["b0"] + 1,
            c["length"],
            round(c["avg"], 3),
            round(c["quality"], 3),
        )
        for c in candidates[:10]
    ]
    selected_trace = [
        (
            c["a0"] + 1,
            c["b0"] + 1,
            c["length"],
            round(c["avg"], 3),
        )
        for c in selected
    ]

    print(
        f"[EZTRACE][{ENGINE_TRACE}] "
        f"measures={measure_count} threshold={threshold:.2f} "
        f"top_candidates={top_candidates} "
        f"selected={selected_trace} "
        f"ranges={[(s['measure_start'], s['measure_end'], s['cluster']) for s in sections]}"
    )

    return sections
