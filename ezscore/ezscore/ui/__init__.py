"""EZScore UI helpers.

Temporary integration hook for the STEM analysis karaoke conductor.
The hook is intentionally isolated so it can later be replaced by a normal
import in stem_lab_analysis.py once the conductor is validated.
"""

def _install_karaoke_patch() -> None:
    try:
        from ezscore.ui import stem_lab_analysis as _stem_lab
        from ezscore.player.karaoke_stem_webaudio import render_player as _karaoke_player
        _stem_lab._render_stem_player = _karaoke_player
    except Exception:
        # Never make the whole UI unavailable because the preview hook failed.
        pass

_install_karaoke_patch()
