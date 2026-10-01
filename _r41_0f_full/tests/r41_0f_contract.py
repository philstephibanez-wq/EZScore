#!/usr/bin/env python3
from __future__ import annotations
import ast, subprocess, sys
from pathlib import Path

ROOT=Path(sys.argv[1] if len(sys.argv)>1 else r"H:\EZScore_v1").resolve()
rd=lambda p:(ROOT/p).read_text(encoding="utf-8-sig")

worker=rd("worker_app/ezscore_analysis_worker.pyw")
start=rd("scripts/start_analysis_worker_desktop.ps1")
finder=rd("scripts/find_analysis_python.ps1")
backend=rd("scripts/launch_ezscore_backend.ps1")
ci=rd(".github/workflows/ci.yml")
js=rd("public/assets/js/chordslab.js")
css=rd("public/assets/css/chordslab.css")
twig=rd("templates/song/chordslab.html.twig")
mixer=rd("public/assets/js/stems-mixer.js")

assert 'APP_VERSION = "R41.0F"' in worker
assert "timeout=60," in worker
assert "Diagnostics:" in worker
assert "bs_roformer + mel_band_roformer + lv-chordia + CUDA" in worker
assert "import lv_chordia" in finder
assert '$env:EZSCORE_STEM_PYTHON = $ExpectedPython' in start
assert '.venv-py313\\Scripts\\python.exe' in start
assert "pythonw.exe missing in Worker venv" in start
assert backend.find('Remove-Item $BootstrapFile') < backend.find('start_analysis_worker_desktop.ps1')
assert "Prepare CI environment file" in ci
assert "cat > .env <<'EOF'" in ci
assert 'DATABASE_URL="sqlite:///%kernel.project_dir%/data/ci.sqlite"' in ci

assert "data-chordslab-manual-seeker" in js
assert "ezscore:request-seek" in js
assert "ezscore:audio-timeupdate" in js
assert "new Audio(" not in js
assert "new AudioContext" not in js
assert "root.addEventListener('ezscore:request-seek'" in mixer
assert twig.count("data-mixer-seek")==1
assert "/assets/js/chordslab.js?v=20261001r41_0f" in twig
assert "/assets/css/chordslab.css?v=20261001r41_0f" in twig
assert "R41.0F — ChordsLab manual seeker" in css

p=subprocess.run(["git","diff","--name-only"],cwd=str(ROOT),stdout=subprocess.PIPE,text=True,encoding="utf-8",check=True)
changed={x.strip() for x in p.stdout.splitlines() if x.strip()}
expected={
 ".github/workflows/ci.yml",
 "public/assets/css/chordslab.css",
 "public/assets/js/chordslab.js",
 "scripts/find_analysis_python.ps1",
 "scripts/launch_ezscore_backend.ps1",
 "scripts/start_analysis_worker_desktop.ps1",
 "templates/song/chordslab.html.twig",
 "worker_app/ezscore_analysis_worker.pyw",
}
assert changed==expected,(sorted(changed),sorted(expected))
assert "analysis/chord_timeline_analysis.py" not in changed

ast.parse(worker)
subprocess.run([sys.executable,"-m","py_compile",str(ROOT/"worker_app/ezscore_analysis_worker.pyw")],check=True)
print("R41_0F_FULL_LAUNCHER_CI_SEEKER_CONTRACT_OK")
