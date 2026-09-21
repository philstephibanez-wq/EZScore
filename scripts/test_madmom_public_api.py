from __future__ import annotations

import importlib.metadata as metadata

import madmom_infer as mm

version = metadata.version("madmom-infer")
detect = getattr(mm, "detect_beats", None)

print("madmom-infer version:", version)
print("detect_beats callable:", callable(detect))

if version != "0.2.0":
    raise SystemExit(
        "Version inattendue. Installez: "
        "python -m pip install --upgrade --force-reinstall madmom-infer==0.2.0"
    )

if not callable(detect):
    raise SystemExit("API publique madmom_infer.detect_beats absente.")

print("MADMOM PUBLIC API OK")
