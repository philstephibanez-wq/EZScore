"""EZScore navigation EFSM."""

from .states import (
    REPERTOIRE_LIST,
    PLAYLISTS_LIST,
    GROUPS_LIST,
    GROUP_DETAIL,
    PLAYLIST_DETAIL,
    SONG_DETAIL,
    SONG_ANALYSIS,
)
from .events import (
    OPEN_REPERTOIRE,
    OPEN_PLAYLISTS,
    OPEN_GROUPS,
    OPEN_GROUP,
    OPEN_PLAYLIST,
    OPEN_SONG,
    BACK,
)
from .machine import initial_route, transition

__all__ = [
    "REPERTOIRE_LIST", "PLAYLISTS_LIST", "GROUPS_LIST", "GROUP_DETAIL",
    "PLAYLIST_DETAIL", "SONG_DETAIL", "SONG_ANALYSIS",
    "OPEN_REPERTOIRE", "OPEN_PLAYLISTS", "OPEN_GROUPS", "OPEN_GROUP",
    "OPEN_PLAYLIST", "OPEN_SONG", "BACK", "initial_route", "transition",
]
