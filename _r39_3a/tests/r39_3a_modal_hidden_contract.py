#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else r"H:\EZScore_v1").resolve()

css = (ROOT/"public/assets/css/chordslab.css").read_text(encoding="utf-8")
twig = (ROOT/"templates/song/chordslab.html.twig").read_text(encoding="utf-8")

assert "/* R39.3A — closed dialogs must never participate in layout */" in css
assert "dialog.ez-modal:not([open])" in css
assert "dialog[data-chord-analyze-dialog]:not([open])" in css
assert "display:none!important" in css
assert "dialog.ez-modal[open]" in css
assert "/assets/css/chordslab.css?v=20260930r39_3a" in twig

# Ensure the consolidated prompter itself is untouched.
assert "/* R39.3 — consolidated fixed-focus prompter." in css
assert "/assets/js/chordslab.js?v=20260930r39_3" in twig
assert "/assets/js/components/ezscore-focus-track.js?v=20260930r39_3" in twig
assert "/assets/js/components/ezscore-chord-diagram.js?v=20260930r39_3" in twig

print("R39_3A_MODAL_HIDDEN_CONTRACT_OK")
