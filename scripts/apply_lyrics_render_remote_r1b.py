from __future__ import annotations

import ast
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHOIR = ROOT / "ezscore/integration/choir_pipeline.py"
PLAYER = ROOT / "ezscore/player/stem_analysis_conductor.py"


def backup(paths: list[Path]) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    preferred = Path(r"H:\temp")
    base = preferred if preferred.exists() else Path.home() / "AppData" / "Local" / "Temp"
    out = base / f"EZScore_LYRICS_RENDER_REMOTE_R1b_backup_{stamp}"
    out.mkdir(parents=True, exist_ok=True)
    for path in paths:
        rel = path.relative_to(ROOT)
        dest = out / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)
    return out


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: attendu 1 motif, trouvé {count}.")
    return text.replace(old, new, 1)


def patch_choir(path: Path) -> None:
    text = path.read_text(encoding="utf-8")

    # Import hashlib once, at module level.
    if "import hashlib\n" not in text:
        text = replace_once(
            text,
            "import json\n",
            "import hashlib\nimport json\n",
            "import hashlib",
        )

    # Replace only the pre-widget hydration region.
    start_marker = '    short_hash = str(audio_hash)[:12]\n'
    end_marker = '    original_caption = st.caption\n'
    start = text.find(start_marker, text.find("def _install_manual_lyrics_ui"))
    end = text.find(end_marker, start)
    if start < 0 or end < 0:
        raise RuntimeError("hydration BDD: zone introuvable.")

    hydration = "\n".join([
        '    short_hash = str(audio_hash)[:12]',
        '    old_payload = load_alignment(audio_hash) or {}',
        '',
        '    # SQLite is the authoritative source for the editable block.',
        '    persisted_source = str(load_persisted_source_text(audio_hash) or "")',
        '    if not persisted_source.strip():',
        '        migrated = _initial_user_lyrics(audio_hash)',
        '        persisted_source = str(',
        '            load_persisted_source_text(audio_hash) or migrated or ""',
        '        )',
        '',
        '    # DB content revision = widget identity. A stale/empty Streamlit',
        '    # widget from an earlier render cannot mask the persisted source.',
        '    source_revision = hashlib.sha256(',
        '        persisted_source.encode("utf-8")',
        '    ).hexdigest()[:12]',
        '    text_key = f"ezscore_manual_lyrics_{short_hash}_{source_revision}"',
        '',
    ]) + "\n"

    text = text[:start] + hydration + text[end:]

    # Replace only the text_area block, not other widgets.
    widget_start_marker = '            current_text = st.text_area(\n'
    widget_end_marker = '\n\n            persisted_text = str(\n'
    wstart = text.find(widget_start_marker, text.find("def caption_proxy"))
    wend = text.find(widget_end_marker, wstart)
    if wstart < 0 or wend < 0:
        raise RuntimeError("textarea Paroles: zone introuvable.")

    widget = "\n".join([
        '            st.markdown(',
        '                """',
        '                <style>',
        '                div[data-testid="InputInstructions"] {',
        '                    display: none !important;',
        '                }',
        '                textarea:focus-visible,',
        '                button:focus-visible,',
        '                input:focus-visible,',
        '                [role="button"]:focus-visible {',
        '                    outline: 3px solid currentColor !important;',
        '                    outline-offset: 2px !important;',
        '                }',
        '                </style>',
        '                """,',
        '                unsafe_allow_html=True,',
        '            )',
        '',
        '            current_text = st.text_area(',
        '                "Texte exact du chant",',
        '                value=persisted_source,',
        '                key=text_key,',
        '                height=300,',
        '                placeholder=(',
        '                    "Collez ici les paroles exactes. "',
        '                    "Conservez les retours à la ligne : ils seront mémorisés."',
        '                ),',
        '            )',
    ])
    text = text[:wstart] + widget + text[wend:]

    # After validation, rerun with the new DB-revision widget key.
    assignment = "                        st.session_state[text_key] = saved_text\n"
    if text.count(assignment) == 1:
        text = text.replace(assignment, "", 1)
    elif text.count(assignment) > 1:
        raise RuntimeError("validation BDD: plusieurs affectations widget inattendues.")

    path.write_text(text, encoding="utf-8")


def patch_player(path: Path) -> None:
    text = path.read_text(encoding="utf-8")

    # Checkbox: unique in the inserted conductor HTML.
    text = replace_once(
        text,
        '<input class="diagram-checkbox" type="checkbox">',
        '<input class="diagram-checkbox" type="checkbox" tabindex="0" aria-label="Diagrammes guitare">',
        "focus diagrammes",
    )

    # Patch the INSERTED transport block as a whole. Do not touch the earlier
    # pattern used to remove the base player's original transport.
    old_transport = """    <div class="transport conductor-transport">
      <button class="play" type="button">▶ Lecture</button>
      <button class="pause" type="button">⏸ Pause</button>
      <button class="stop" type="button">⏹ Stop</button>
      <span class="time">0:00 / 0:00</span>
    </div>
    <input class="seek conductor-seek" type="range" min="0" max="1" step="0.001" value="0">
"""
    new_transport = """    <div class="transport conductor-transport">
      <button class="play" type="button" tabindex="0" aria-label="Lecture">▶ Lecture</button>
      <button class="pause" type="button" tabindex="0" aria-label="Pause">⏸ Pause</button>
      <button class="stop" type="button" tabindex="0" aria-label="Stop">⏹ Stop</button>
      <span class="time">0:00 / 0:00</span>
    </div>
    <input class="seek conductor-seek" type="range" min="0" max="1" step="0.001" value="0" tabindex="0" aria-label="Position de lecture">
"""
    text = replace_once(
        text,
        old_transport,
        new_transport,
        "transport conducteur focusable",
    )

    text = replace_once(
        text,
        ".conductor-seek { width:100%; margin:8px 0 2px; }\n",
        """.conductor-seek { width:100%; margin:8px 0 2px; }

.diagram-checkbox:focus-visible,
.conductor-transport button:focus-visible,
.conductor-seek:focus-visible {
  outline:3px solid currentColor;
  outline-offset:3px;
}
""",
        "focus visible conducteur",
    )

    path.write_text(text, encoding="utf-8")


def main() -> int:
    paths = [CHOIR, PLAYER]
    for path in paths:
        if not path.is_file():
            raise FileNotFoundError(path)

    print("Backup:", backup(paths))

    # Atomic: no repository target is written unless BOTH candidate files patch
    # and parse successfully.
    with tempfile.TemporaryDirectory(prefix="ezscore_lyrics_render_remote_r1b_") as td:
        td = Path(td)
        choir_tmp = td / "choir_pipeline.py"
        player_tmp = td / "stem_analysis_conductor.py"
        shutil.copy2(CHOIR, choir_tmp)
        shutil.copy2(PLAYER, player_tmp)

        patch_choir(choir_tmp)
        patch_player(player_tmp)

        ast.parse(choir_tmp.read_text(encoding="utf-8"), filename=str(choir_tmp))
        ast.parse(player_tmp.read_text(encoding="utf-8"), filename=str(player_tmp))

        shutil.copy2(choir_tmp, CHOIR)
        shutil.copy2(player_tmp, PLAYER)

    print("PATCH OK")
    print(" - textarea alimenté directement par SQLite")
    print(" - clé widget versionnée par le contenu BDD")
    print(" - bouton Valider conservé")
    print(" - aide Ctrl+Enter masquée")
    print(" - lecteur STEM navigable au clavier/télécommande")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
