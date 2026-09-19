from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

EXPECTED_HEAD = "e3262b88b2de5c61dcb9a58b3b804541d325ca7e"
TARGETS = [
    Path("ezscore/auth/ui.py"),
    Path("ezscore/auth/session.py"),
    Path("ezscore/ui/stem_lab_analysis.py"),
]


def run(cmd, cwd, check=True):
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=check,
    )


def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: attendu 1 occurrence, trouvé {count}")
    return text.replace(old, new, 1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    args = parser.parse_args()
    repo = Path(args.repo).resolve()

    if not (repo / ".git").is_dir():
        raise RuntimeError(f"Dépôt Git introuvable : {repo}")

    head = run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
    if head != EXPECTED_HEAD:
        raise RuntimeError(
            "HEAD inattendu.\n"
            f"Attendu : {EXPECTED_HEAD}\n"
            f"Trouvé  : {head}\n"
            "Aucun fichier n'a été modifié."
        )

    for rel in TARGETS:
        path = repo / rel
        if not path.is_file():
            raise RuntimeError(f"Fichier absent : {rel}")
        dirty = run(["git", "diff", "--quiet", "--", str(rel)], repo, check=False)
        if dirty.returncode != 0:
            raise RuntimeError(
                f"{rel} contient déjà des modifications locales. "
                "Aucun fichier n'a été modifié."
            )

    originals = {}
    new_texts = {}

    rel = Path("ezscore/auth/ui.py")
    path = repo / rel
    raw = path.read_bytes()
    originals[rel] = raw
    nl = "\r\n" if b"\r\n" in raw else "\n"
    text = raw.decode("utf-8").replace("\r\n", "\n")

    old = '''def render_account_page() -> None:
    st.markdown(_AUTH_CSS, unsafe_allow_html=True)
    user = current_user()
    st.header("Compte EZScore")

    if user:
        _render_profile(user)
        render_admin_users()
        return

    users = user_count()
    admins = active_admin_count()

    if users == 0 and admins == 0:
        _render_initial_admin_setup()
        return
'''
    new = '''def render_account_page() -> None:
    st.markdown(_AUTH_CSS, unsafe_allow_html=True)
    st.header("Compte EZScore")

    # Une BDD de comptes vide doit toujours passer par le bootstrap interactif
    # du premier administrateur AVANT toute résolution de session/OIDC.
    users = user_count()
    if users == 0:
        _render_initial_admin_setup()
        return

    user = current_user()
    if user:
        _render_profile(user)
        render_admin_users()
        return

    admins = active_admin_count()
'''
    text = replace_once(text, old, new, "AUTH bootstrap UI")
    compile(text, str(path), "exec")
    new_texts[rel] = text.replace("\n", nl).encode("utf-8")

    rel = Path("ezscore/auth/session.py")
    path = repo / rel
    raw = path.read_bytes()
    originals[rel] = raw
    nl = "\r\n" if b"\r\n" in raw else "\n"
    text = raw.decode("utf-8").replace("\r\n", "\n")

    text = replace_once(
        text,
        '''from .storage import (
    authenticate_local,
    bootstrap_admin_from_env,
    get_user_by_id,
''',
        '''from .storage import (
    authenticate_local,
    get_user_by_id,
''',
        "AUTH import bootstrap",
    )
    text = replace_once(
        text,
        '''def initialize_auth() -> None:
    bootstrap_admin_from_env()
    ensure_persistent_session_schema()
''',
        '''def initialize_auth() -> None:
    # Ne jamais créer/promouvoir implicitement un compte au démarrage.
    # Une BDD vide est initialisée depuis l'écran Compte par le premier admin.
    ensure_persistent_session_schema()
''',
        "AUTH démarrage",
    )
    compile(text, str(path), "exec")
    new_texts[rel] = text.replace("\n", nl).encode("utf-8")

    rel = Path("ezscore/ui/stem_lab_analysis.py")
    path = repo / rel
    raw = path.read_bytes()
    originals[rel] = raw
    nl = "\r\n" if b"\r\n" in raw else "\n"
    text = raw.decode("utf-8").replace("\r\n", "\n")

    old = '''    stems = cached_stem_paths(audio_hash)
    speech = _load_speech(audio_hash)
    structure = _load_structure(audio_hash)
    words = list((speech or {}).get("words", []) or [])

    # ========================================================
'''
    new = '''    stems = cached_stem_paths(audio_hash)
    speech = _load_speech(audio_hash)
    structure = _load_structure(audio_hash)
    words = list((speech or {}).get("words", []) or [])

    # Non-régression Chant / Chœurs :
    # sur une analyse fraîche, la BDD peut être neuve et le cache vocal absent.
    # Le lecteur/éditeur historiques savent déjà exploiter
    # whisper_vocals_small.json ; on garantit simplement sa production ici,
    # dans Analyse, dès que STEM + transcription originale sont disponibles.
    if (
        speech is not None
        and words
        and stems_cache_complete(audio_hash)
        and not (_work_dir(audio_hash) / "whisper_vocals_small.json").is_file()
    ):
        try:
            from ezscore.player.karaoke_stem_webaudio import (
                _ensure_vocal_whisper_supplement,
            )
            with st.spinner("Analyse complémentaire Chant / Chœurs…"):
                _ensure_vocal_whisper_supplement(
                    source,
                    cached_stem_paths(audio_hash),
                    _work_dir(audio_hash) / "browser_preview",
                    words,
                )
        except Exception as exc:
            st.warning(
                "Analyse complémentaire Chant / Chœurs indisponible : "
                + str(exc)
            )

    # ========================================================
'''
    text = replace_once(text, old, new, "CHOEURS cache vocal Analyse")
    compile(text, str(path), "exec")
    new_texts[rel] = text.replace("\n", nl).encode("utf-8")

    checks = {
        Path("ezscore/auth/ui.py"): [
            "if users == 0:",
            "_render_initial_admin_setup()",
            "user = current_user()",
        ],
        Path("ezscore/auth/session.py"): [
            "def initialize_auth() -> None:",
            "ensure_persistent_session_schema()",
        ],
        Path("ezscore/ui/stem_lab_analysis.py"): [
            "Analyse complémentaire Chant / Chœurs",
            "_ensure_vocal_whisper_supplement",
            "whisper_vocals_small.json",
        ],
    }
    for rel, needles in checks.items():
        s = new_texts[rel].decode("utf-8")
        for needle in needles:
            if needle not in s:
                raise RuntimeError(f"Validation incomplète {rel}: {needle}")

    backup_root = Path("H:/temp") if Path("H:/temp").exists() else Path(tempfile.gettempdir())
    backup_dir = backup_root / "EZScore_FIX_AUTH_CHOIRS_R1_backup"
    backup_dir.mkdir(parents=True, exist_ok=True)

    try:
        for rel, data in originals.items():
            dest = backup_dir / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)

        for rel, data in new_texts.items():
            (repo / rel).write_bytes(data)

        for rel in TARGETS:
            run([sys.executable, "-m", "py_compile", str(rel)], repo)

        diff = run(
            ["git", "diff", "--check", "--", *[str(x) for x in TARGETS]],
            repo,
            check=False,
        )
        if diff.returncode != 0:
            raise RuntimeError(diff.stdout.strip() or "git diff --check a échoué")

    except Exception:
        for rel, data in originals.items():
            (repo / rel).write_bytes(data)
        raise

    print("OK - EZScore_FIX_AUTH_CHOIRS_R1 appliqué")
    print("Fichiers modifiés :")
    for rel in TARGETS:
        print(" -", rel)
    print("Aucune BDD ni donnée d'analyse existante n'a été supprimée.")
    print("Backup :", backup_dir)


if __name__ == "__main__":
    main()
