"""EZScore analysis domain.

Primary analysis:
- chord timeline
- phoneme timeline
- lyrics timeline

Secondary analysis:
- visual block proposal
"""

from .timelines import (
    TIMEBASE,
    TIMELINE_SCHEMA_VERSION,
    active_at,
    build_chord_timeline,
    build_lyrics_timeline,
    build_phoneme_timeline,
    build_primary_timelines,
)
from .structure import detect_visual_blocks

__all__ = [
    "TIMEBASE",
    "TIMELINE_SCHEMA_VERSION",
    "active_at",
    "build_chord_timeline",
    "build_lyrics_timeline",
    "build_phoneme_timeline",
    "build_primary_timelines",
    "detect_visual_blocks",
]
