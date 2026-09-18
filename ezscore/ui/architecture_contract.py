from __future__ import annotations

"""Executable architecture contract for Analyse / Player / Editorial."""

from pathlib import Path


FORBIDDEN_PLAYER_TOKENS = (
    "_transcribe_original",
    "_whisper_small",
    "model.transcribe(",
    "analyze_quality_beats(",
    "analyze_chords_absolute(",
    "_build_conductor_timeline(",
    "_ensure_vocal_whisper_supplement(",
)

FORBIDDEN_EDITOR_TOKENS = (
    "_transcribe_original",
    "_whisper_small",
    "model.transcribe(",
    "ensure_stems(",
    "analyze_quality_beats(",
    "analyze_chords_absolute(",
)


def audit_file(path: Path, forbidden: tuple[str, ...]) -> list[str]:
    text = path.read_text(encoding="utf-8")
    return [token for token in forbidden if token in text]


def audit_repository(app_dir: Path) -> dict[str, list[str]]:
    app_dir = Path(app_dir)

    checks = {
        "truth_player": (
            app_dir / "ezscore" / "player" / "analysis_truth_player.py",
            FORBIDDEN_PLAYER_TOKENS,
        ),
        "editorial_timeline": (
            app_dir / "ezscore" / "ui" / "editorial_timeline.py",
            FORBIDDEN_EDITOR_TOKENS,
        ),
        "lyrics_inline_editor": (
            app_dir / "ezscore" / "ui" / "lyrics_inline_editor.py",
            FORBIDDEN_EDITOR_TOKENS,
        ),
    }

    failures: dict[str, list[str]] = {}
    for name, (path, forbidden) in checks.items():
        if not path.is_file():
            continue
        found = audit_file(path, forbidden)
        if found:
            failures[name] = found

    return failures


def assert_repository_contract(app_dir: Path) -> None:
    audit_analysis_actions_location(app_dir)
    failures = audit_repository(app_dir)
    if failures:
        details = "; ".join(
            f"{name}: {', '.join(tokens)}"
            for name, tokens in sorted(failures.items())
        )
        raise RuntimeError(
            "Violation du contrat Analyse/Player/Édition : " + details
        )


def audit_analysis_actions_location(app_dir: Path) -> None:
    """Guard against putting re-analysis commands back inside the player."""
    app_dir = Path(app_dir)
    player = app_dir / "ezscore" / "player" / "analysis_truth_player.py"
    if not player.is_file():
        return

    text = player.read_text(encoding="utf-8")
    forbidden_ui = (
        "Ré-analyser paroles",
        "Ré-analyser accords",
        "Ré-analyser tout",
        "st.button(",
    )
    found = [token for token in forbidden_ui if token in text]
    if found:
        raise RuntimeError(
            "Les commandes de réanalyse ont été remises dans le player : "
            + ", ".join(found)
        )
