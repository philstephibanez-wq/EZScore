#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else r"H:\EZScore_v1").resolve()
PS1 = ROOT / "scripts" / "launch_ezscore_backend.ps1"
HTA = ROOT / "EZScore-Launcher.hta"
BOM = b"\xef\xbb\xbf"

def read_bom_utf8(path: Path) -> str:
    data = path.read_bytes()
    assert data.startswith(BOM), f"UTF-8 BOM absent: {path}"
    body = data[len(BOM):]
    text = body.decode("utf-8")
    assert "\ufffd" not in text, f"Unicode replacement char: {path}"
    return text

ps1 = read_bom_utf8(PS1)
hta = read_bom_utf8(HTA)

for token in ("Vérification", "persistés", "nécessaires", "état", "prêt", "Échec"):
    assert token in ps1, f"PS1 accent literal missing: {token}"

for token in ("Démarrage", "états", "Aucune page web", "Ouverture"):
    assert token in hta, f"HTA accent literal missing: {token}"

assert "Start-Process ($BrowserUrl" not in ps1
assert "$BrowserUrl =" not in ps1
assert "Aucune page web n'est ouverte automatiquement." in ps1

assert '<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />' in hta
assert 'new ActiveXObject("ADODB.Stream")' in hta
assert 'stream.Charset = "utf-8";' in hta

print("R40_0K_FULL_UTF8_BOM_SPLASH_CONTRACT_OK")
