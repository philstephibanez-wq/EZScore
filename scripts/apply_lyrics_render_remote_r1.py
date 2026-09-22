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
    out = base / f"EZScore_LYRICS_RENDER_REMOTE_R1_backup_{stamp}"
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

    start_marker = '    short_hash = str(audio_hash)[:12]\n'
    end_marker = '    original_caption = st.caption\n'
    start = text.find(start_marker)
    end = text.find(end_marker, start)
    if start < 0 or end < 0:
        raise RuntimeError("hydration BDD: zone introuvable")

    replacement = '''    short_hash = str(audio_hash)[:12]
    old_payload = load_alignment(audio_hash) or {}

    # SQLite est la source de vérité du bloc éditable.
    persisted_source = str(load_persisted_source_text(audio_hash) or "")
    if not persisted_source.strip():
        migrated = _initial_user_lyrics(audio_hash)
        persisted_source = str(
            load_persisted_source_text(audio_hash) or migrated or ""
        )

    # La révision BDD définit l'identité du widget : un ancien état Streamlit
    # vide ne peut plus masquer la valeur persistée.
    import hashlib
    source_revision = hashlib.sha256(
        persisted_source.encode("utf-8")
    ).hexdigest()[:12]
    text_key = f"ezscore_manual_lyrics_{short_hash}_{source_revision}"

'''
    text = text[:start] + replacement + text[end:]

    old_widget = '''            current_text = st.text_area(
                "Texte exact du chant",
                key=text_key,
                height=300,
                placeholder=(
                    "Collez ici les paroles exactes. "
                    "Conservez les retours à la ligne : ils seront mémorisés."
                ),
            )
'''
    new_widget = '''            st.markdown(
                """
                <style>
                div[data-testid="InputInstructions"] { display:none !important; }
                textarea:focus-visible,
                button:focus-visible,
                input:focus-visible,
                [role="button"]:focus-visible {
                    outline:3px solid currentColor !important;
                    outline-offset:2px !important;
                }
                </style>
                """,
                unsafe_allow_html=True,
            )

            current_text = st.text_area(
                "Texte exact du chant",
                value=persisted_source,
                key=text_key,
                height=300,
                placeholder=(
                    "Collez ici les paroles exactes. "
                    "Conservez les retours à la ligne : ils seront mémorisés."
                ),
            )
'''
    text = replace_once(text, old_widget, new_widget, "textarea depuis BDD")

    old_success = '''                    else:
                        st.session_state[text_key] = saved_text
                        st.success("✓ Bloc de paroles enregistré en BDD.")
                        st.rerun()
'''
    new_success = '''                    else:
                        st.success("✓ Bloc de paroles enregistré en BDD.")
                        st.rerun()
'''
    text = replace_once(text, old_success, new_success, "validation/rerun")

    old_recover = '''                ):
                    st.session_state[text_key] = legacy_text
                    save_draft(audio_hash, legacy_text)
                    st.rerun()
'''
    new_recover = '''                ):
                    save_draft(audio_hash, legacy_text)
                    st.rerun()
'''
    if old_recover in text:
        text = replace_once(text, old_recover, new_recover, "récupération legacy")

    path.write_text(text, encoding="utf-8")


def patch_player(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    pairs = [
        ('<input class="diagram-checkbox" type="checkbox">', '<input class="diagram-checkbox" type="checkbox" tabindex="0" aria-label="Diagrammes guitare">', "diagrammes"),
        ('<button class="play" type="button">▶ Lecture</button>', '<button class="play" type="button" tabindex="0" aria-label="Lecture">▶ Lecture</button>', "lecture"),
        ('<button class="pause" type="button">⏸ Pause</button>', '<button class="pause" type="button" tabindex="0" aria-label="Pause">⏸ Pause</button>', "pause"),
        ('<button class="stop" type="button">⏹ Stop</button>', '<button class="stop" type="button" tabindex="0" aria-label="Stop">⏹ Stop</button>', "stop"),
        ('<input class="seek conductor-seek" type="range" min="0" max="1" step="0.001" value="0">', '<input class="seek conductor-seek" type="range" min="0" max="1" step="0.001" value="0" tabindex="0" aria-label="Position de lecture">', "seek"),
    ]
    for old, new, label in pairs:
        text = replace_once(text, old, new, f"tabindex {label}")

    text = replace_once(
        text,
        '.conductor-seek { width:100%; margin:8px 0 2px; }\n',
        '''.conductor-seek { width:100%; margin:8px 0 2px; }

.diagram-checkbox:focus-visible,
.conductor-transport button:focus-visible,
.conductor-seek:focus-visible {
  outline:3px solid currentColor;
  outline-offset:3px;
}
''',
        "focus visible lecteur",
    )
    path.write_text(text, encoding="utf-8")


def main() -> int:
    paths = [CHOIR, PLAYER]
    for path in paths:
        if not path.is_file():
            raise FileNotFoundError(path)

    print("Backup:", backup(paths))

    with tempfile.TemporaryDirectory(prefix="ezscore_lyrics_render_remote_") as td:
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
    print(" - textarea peuplé directement depuis SQLite")
    print(" - widget versionné par contenu BDD")
    print(" - bouton Valider reste l'action métier explicite")
    print(" - aide Ctrl+Enter masquée")
    print(" - focus visible + tabindex lecteur pour télécommande Android")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
