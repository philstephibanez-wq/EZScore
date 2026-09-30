#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else r"H:\EZScore_v1").resolve()
BASE_COMMIT = "50d20748f151c5f047f2b7c6ad09122bc5c2b92d"

PS1_REL = "scripts/launch_ezscore_backend.ps1"
HTA_REL = "EZScore-Launcher.hta"

PS1 = ROOT / PS1_REL
HTA = ROOT / HTA_REL
UTF8_BOM = b"\xef\xbb\xbf"

def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="strict",
        check=False,
    )

def git_show(path: str) -> str:
    p = git("show", f"HEAD:{path}")
    if p.returncode != 0:
        raise RuntimeError(f"git show HEAD:{path} failed: {p.stderr.strip()}")
    return p.stdout.replace("\r\n", "\n").replace("\r", "\n").lstrip("\ufeff")

def write_utf8_bom_atomic(path: Path, text: str) -> None:
    tmp = path.with_suffix(path.suffix + ".r40k.tmp")
    data = UTF8_BOM + text.encode("utf-8")
    tmp.write_bytes(data)
    tmp.replace(path)

def guard() -> None:
    p = git("rev-parse", "HEAD")
    if p.returncode != 0:
        raise RuntimeError("git rev-parse HEAD failed")
    head = p.stdout.strip()
    if head != BASE_COMMIT:
        raise RuntimeError(f"HEAD={head}; expected {BASE_COMMIT}. STOP.")
    if git("diff", "--quiet").returncode != 0:
        raise RuntimeError("Tracked working-tree changes detected. STOP.")
    if git("diff", "--cached", "--quiet").returncode != 0:
        raise RuntimeError("Staged changes detected. STOP.")

def assert_source_contract(ps1_text: str, hta_text: str) -> None:
    # R40.0J behavior must remain intact.
    if "Start-Process ($BrowserUrl" in ps1_text or "$BrowserUrl =" in ps1_text:
        raise RuntimeError("Automatic browser opening unexpectedly present.")
    if "Aucune page web n'est ouverte automatiquement." not in ps1_text:
        raise RuntimeError("R40.0J no-auto-browser contract missing.")
    if '<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />' not in hta_text:
        raise RuntimeError("HTA UTF-8 meta missing.")
    if 'new ActiveXObject("ADODB.Stream")' not in hta_text:
        raise RuntimeError("HTA UTF-8 JSON reader missing.")
    if 'stream.Charset = "utf-8";' not in hta_text:
        raise RuntimeError("HTA UTF-8 charset contract missing.")

    # Representative accented literals that must survive PowerShell 5.1 / HTA parsing.
    required_ps1 = (
        "Vérification",
        "persistés",
        "nécessaires",
        "état",
        "prêt",
        "Échec",
    )
    required_hta = (
        "Démarrage",
        "états",
        "Aucune page web",
        "Ouverture",
    )
    for token in required_ps1:
        if token not in ps1_text:
            raise RuntimeError(f"Accented PowerShell literal missing: {token}")
    for token in required_hta:
        if token not in hta_text:
            raise RuntimeError(f"Accented HTA literal missing: {token}")

def main() -> int:
    guard()

    originals = {
        PS1: PS1.read_bytes(),
        HTA: HTA.read_bytes(),
    }

    ps1_text = git_show(PS1_REL)
    hta_text = git_show(HTA_REL)
    assert_source_contract(ps1_text, hta_text)

    try:
        write_utf8_bom_atomic(PS1, ps1_text)
        write_utf8_bom_atomic(HTA, hta_text)

        for path in (PS1, HTA):
            data = path.read_bytes()
            if not data.startswith(UTF8_BOM):
                raise RuntimeError(f"UTF-8 BOM missing after write: {path}")
            decoded = data[len(UTF8_BOM):].decode("utf-8")
            if "\ufffd" in decoded:
                raise RuntimeError(f"Unicode replacement character found: {path}")

        print("R40_0K_FULL_UTF8_BOM_SPLASH_INSTALL_OK")
        return 0
    except Exception:
        for path, data in originals.items():
            path.write_bytes(data)
        raise

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
