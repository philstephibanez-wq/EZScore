#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else r"H:\EZScore_v1").resolve()
TARGET = ROOT / "worker_app" / "lyrics_worker_r37.py"

def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one anchor, found {count}")
    return text.replace(old, new, 1)

def main() -> int:
    if not TARGET.is_file():
        raise SystemExit(f"Missing file: {TARGET}")

    src = TARGET.read_text(encoding="utf-8")

    if "R38.13a: cache validated Lyrics Python" in src:
        print("R38_13A_ALREADY_INSTALLED")
        return 0

    old_sig = "def _discover_lyrics_python(engine) -> str:\n"
    new_sig = '''def _discover_lyrics_python(engine, force: bool = False) -> str:
    # R38.13a: cache validated Lyrics Python for the whole Worker lifetime.
    # Do not re-import torch/whisper/CUDA before every lyrics job.
    cached = getattr(engine, "_lyrics_python_cache", None)
    if not force and isinstance(cached, dict):
        cached_python = str(cached.get("python") or "")
        if cached_python and Path(cached_python).is_file():
            engine.log(
                f"Python Lyrics (cache): {cached_python}"
                + (f" · {cached.get('gpu')}" if cached.get("gpu") else "")
            )
            return cached_python
        engine._lyrics_python_cache = None
'''
    src = replace_once(src, old_sig, new_sig, "discover signature/cache")

    old_timeout = "                timeout=20,check=False,\n"
    new_timeout = "                timeout=60,check=False,\n"
    src = replace_once(src, old_timeout, new_timeout, "probe timeout")

    old_success = '''            engine.log(f"Python Lyrics: {data.get('python')} · {data.get('gpu')}")
            return str(data["python"])
'''
    new_success = '''            resolved_python = str(data["python"])
            engine._lyrics_python_cache = {
                "python": resolved_python,
                "gpu": data.get("gpu"),
                "validated_at": time.time(),
            }
            engine.log(f"Python Lyrics: {resolved_python} · {data.get('gpu')}")
            return resolved_python
'''
    src = replace_once(src, old_success, new_success, "cache successful probe")

    old_popen = '''    engine.log("Commande LYRICS lancée.")
    proc=subprocess.Popen(
        command,cwd=str(engine.root),env=env,
        stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
        text=True,encoding="utf-8",errors="replace",bufsize=1,
        creationflags=WINDOWS_NO_WINDOW if os.name=="nt" else 0,
    )
'''
    new_popen = '''    engine.log("Commande LYRICS lancée.")
    try:
        proc=subprocess.Popen(
            command,cwd=str(engine.root),env=env,
            stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
            text=True,encoding="utf-8",errors="replace",bufsize=1,
            creationflags=WINDOWS_NO_WINDOW if os.name=="nt" else 0,
        )
    except (FileNotFoundError, OSError) as exc:
        # Invalidate only when the interpreter itself can no longer be launched.
        engine.log(f"Python Lyrics cache invalidé au lancement: {exc}")
        engine._lyrics_python_cache = None
        python = _discover_lyrics_python(engine, force=True)
        command[0] = python
        proc=subprocess.Popen(
            command,cwd=str(engine.root),env=env,
            stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
            text=True,encoding="utf-8",errors="replace",bufsize=1,
            creationflags=WINDOWS_NO_WINDOW if os.name=="nt" else 0,
        )
'''
    src = replace_once(src, old_popen, new_popen, "Popen retry")

    TARGET.write_text(src, encoding="utf-8")
    print("R38_13A_WORKER_CACHE_OK")
    print("R38_13A_INSTALL_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
