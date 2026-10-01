#!/usr/bin/env python3
from __future__ import annotations

import ast, subprocess, sys
from pathlib import Path

BASE_COMMIT = '282e46195f3be16dd8fbbeab9b4a57a5dbe8ede4'
ROOT = Path(sys.argv[1] if len(sys.argv)>1 else r'H:\EZScore_v1').resolve()
RELS = {
 'worker':'worker_app/ezscore_analysis_worker.pyw',
 'start':'scripts/start_analysis_worker_desktop.ps1',
 'finder':'scripts/find_analysis_python.ps1',
 'backend':'scripts/launch_ezscore_backend.ps1',
 'ci':'.github/workflows/ci.yml',
 'js':'public/assets/js/chordslab.js',
 'css':'public/assets/css/chordslab.css',
 'twig':'templates/song/chordslab.html.twig',
}
FILES={k:ROOT/v for k,v in RELS.items()}

def git(*args):
    return subprocess.run(['git',*args],cwd=str(ROOT),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',errors='replace',check=False)

def git_show(rel):
    p=git('show',f'HEAD:{rel}')
    if p.returncode!=0: raise RuntimeError(f'git show HEAD:{rel} failed: {p.stderr.strip()}')
    return p.stdout.replace('\r\n','\n').replace('\r','\n').lstrip('\ufeff')

def rep(text,old,new,label):
    n=text.count(old)
    if n!=1: raise RuntimeError(f'{label}: expected 1 anchor, found {n}')
    return text.replace(old,new,1)

def write_atomic(path,text,bom=False):
    tmp=path.with_suffix(path.suffix+'.r41f.tmp')
    tmp.write_text(text,encoding=('utf-8-sig' if bom else 'utf-8'),newline='\n')
    tmp.replace(path)

def guard():
    h=git('rev-parse','HEAD')
    if h.returncode!=0: raise RuntimeError('git rev-parse HEAD failed')
    actual=h.stdout.strip()
    if actual!=BASE_COMMIT: raise RuntimeError(f'HEAD={actual}; expected {BASE_COMMIT}. STOP.')
    if git('diff','--quiet').returncode!=0: raise RuntimeError('Tracked working-tree changes detected. Discard local R41.0E before this consolidated FULL. STOP.')
    if git('diff','--cached','--quiet').returncode!=0: raise RuntimeError('Staged changes detected. STOP.')

def main():
    guard()
    original={k:p.read_bytes() for k,p in FILES.items()}
    src={k:git_show(v) for k,v in RELS.items()}
    baseline=[
      ('APP_VERSION = "R41.0D"' in src['worker'],'worker R41.0D'),
      ('timeout=20,' in src['worker'],'worker probe timeout'),
      ('find_analysis_python.ps1' in src['start'],'desktop finder'),
      ('import bs_roformer' in src['finder'],'finder baseline'),
      ('Set-LauncherStatus "worker"' in src['backend'],'backend baseline'),
      ('- name: Install dependencies' in src['ci'],'CI baseline'),
      ("document.querySelector('[data-stem-mixer]')?.addEventListener('ezscore:audio-timeupdate',e=>highlightAt(Number(e.detail?.time||0)));\ncapoSelect?.addEventListener('change',()=>{capo=Number(capoSelect.value||0);render();autoSaveSettings()});\n" in src['js'],'seeker anchor'),
      ('/assets/js/chordslab.js?v=20260930r39_3' in src['twig'],'JS cache'),
      ('/assets/css/chordslab.css?v=20260930r39_3a' in src['twig'],'CSS cache'),
    ]
    bad=[n for ok,n in baseline if not ok]
    if bad: raise RuntimeError('R41.0F baseline mismatch: '+', '.join(bad)+'. STOP.')
    try:
        w=src['worker']
        w=rep(w,'APP_VERSION = "R41.0D"','APP_VERSION = "R41.0F"','worker version')
        w=rep(w,'                    timeout=20,\n','                    timeout=60,\n','worker timeout')
        w=rep(w,'        if not self.engine_python:\n            raise RuntimeError(\n                "Aucun Python compatible trouvé. Il faut bs_roformer + mel_band_roformer + lv-chordia."\n            )\n','        if not self.engine_python:\n            errors = self.capabilities.get("errors") or []\n            detail = " | ".join(str(item) for item in errors[-5:]) or "aucun détail disponible"\n            raise RuntimeError(\n                "Aucun Python compatible trouvé. "\n                "Requis: bs_roformer + mel_band_roformer + lv-chordia + CUDA. "\n                f"Diagnostics: {detail}"\n            )\n','worker diagnostic')
        ast.parse(w)

        f=src['finder']
        f=rep(f,'import mel_band_roformer\nimport torch\n','import mel_band_roformer\nimport lv_chordia\nimport torch\n','finder lv')

        s=src['start']
        s=rep(s,'$Pythonw = Join-Path (Split-Path -Parent $Python) "pythonw.exe"\nif (-not (Test-Path $Pythonw)) {\n    $Pythonw = $Python\n}\n','$ExpectedPython = Join-Path $Project ".venv-py313\\Scripts\\python.exe"\nif ([System.IO.Path]::GetFullPath($Python) -ne [System.IO.Path]::GetFullPath($ExpectedPython)) {\n    throw "Unexpected Worker Python: $Python (expected $ExpectedPython)"\n}\n\n# Child Worker inherits this explicit interpreter path. No .pyw association or global Python.\n$env:EZSCORE_STEM_PYTHON = $ExpectedPython\n\n$Pythonw = Join-Path (Split-Path -Parent $ExpectedPython) "pythonw.exe"\nif (-not (Test-Path $Pythonw)) {\n    throw "pythonw.exe missing in Worker venv: $Pythonw"\n}\n','explicit pythonw')

        b=src['backend']
        b=rep(b,'    Set-LauncherStatus "worker" "Ouverture de EZScore Analysis Worker..." 58 "running" "Le Worker restaure les modes ONLINE/LOCAL persistés et démarre les serveurs nécessaires."\n    & (Join-Path $PSScriptRoot "start_analysis_worker_desktop.ps1") | Out-Null\n\n    Set-LauncherStatus "wait" "Initialisation du Worker…" 78 "running" "Attente de l\'état initial du Worker."\n    $BootstrapFile = Join-Path $RuntimeDir "analysis-worker-bootstrap.json"\n    Remove-Item $BootstrapFile -Force -ErrorAction SilentlyContinue\n','    # Clear stale bootstrap state before the Worker can publish a fresh one.\n    $BootstrapFile = Join-Path $RuntimeDir "analysis-worker-bootstrap.json"\n    Remove-Item $BootstrapFile -Force -ErrorAction SilentlyContinue\n\n    Set-LauncherStatus "worker" "Ouverture de EZScore Analysis Worker..." 58 "running" "Le Worker restaure les modes ONLINE/LOCAL persistés et démarre les serveurs nécessaires."\n    & (Join-Path $PSScriptRoot "start_analysis_worker_desktop.ps1") | Out-Null\n\n    Set-LauncherStatus "wait" "Initialisation du Worker…" 78 "running" "Attente de l\'état initial du Worker."\n','bootstrap race')

        c=src['ci']
        c=rep(c,'      - name: Install dependencies\n        run: composer install --no-interaction --prefer-dist --no-progress\n','      - name: Prepare CI environment file\n        shell: bash\n        run: |\n          cat > .env <<\'EOF\'\n          APP_ENV=test\n          APP_DEBUG=0\n          APP_SECRET=ci-only-secret-not-for-production\n          DATABASE_URL="sqlite:///%kernel.project_dir%/data/ci.sqlite"\n          GOOGLE_CLIENT_ID=ci-placeholder\n          GOOGLE_CLIENT_SECRET=ci-placeholder\n          MAILER_DSN=null://null\n          MAILER_FROM=ci@example.test\n          ANALYSIS_WORKER_TOKEN=ci-worker-token\n          EOF\n\n      - name: Install dependencies\n        run: composer install --no-interaction --prefer-dist --no-progress\n','CI env')

        j=src['js']
        j=rep(j,"document.querySelector('[data-stem-mixer]')?.addEventListener('ezscore:audio-timeupdate',e=>highlightAt(Number(e.detail?.time||0)));\ncapoSelect?.addEventListener('change',()=>{capo=Number(capoSelect.value||0);render();autoSaveSettings()});\n",'const mixerRoot=document.querySelector(\'[data-stem-mixer]\');\nlet manualSeeker=null,manualSeekerOutput=null,manualSeekerDragging=false;\n\nfunction formatSeekerTime(sec){\n sec=Math.max(0,Number(sec)||0);\n const minutes=Math.floor(sec/60),seconds=sec-minutes*60;\n return `${minutes}:${seconds.toFixed(2).padStart(5,\'0\')}`;\n}\n\nfunction installManualSeeker(){\n if(!mixerRoot)return;\n const stage=measuresEl.closest(\'.chordslab-stage\');\n if(!stage||root.querySelector(\'[data-chordslab-manual-seeker]\'))return;\n\n const shell=document.createElement(\'div\');\n shell.className=\'chordslab-manual-seeker\';\n shell.innerHTML=\'<label><span>Position</span><input type="range" min="0" max="1" step="0.01" value="0" data-chordslab-manual-seeker aria-label="Position dans le morceau"><output data-chordslab-manual-seeker-time>0:00.00</output></label>\';\n stage.insertAdjacentElement(\'beforebegin\',shell);\n\n manualSeeker=shell.querySelector(\'[data-chordslab-manual-seeker]\');\n manualSeekerOutput=shell.querySelector(\'[data-chordslab-manual-seeker-time]\');\n const lastBeatSec=Math.max(0,Number(beats.at(-1)?.start_ms||0)/1000);\n manualSeeker.max=String(Math.max(1,lastBeatSec+2));\n\n const requestSeek=()=>{\n  const max=Math.max(0,Number(manualSeeker.max||0));\n  const sec=Math.max(0,Math.min(max,Number(manualSeeker.value)||0));\n  if(manualSeekerOutput)manualSeekerOutput.textContent=formatSeekerTime(sec);\n  mixerRoot.dispatchEvent(new CustomEvent(\'ezscore:request-seek\',{detail:{time:sec}}));\n  highlightAt(sec);\n };\n\n manualSeeker.addEventListener(\'pointerdown\',()=>{manualSeekerDragging=true});\n manualSeeker.addEventListener(\'pointerup\',()=>{manualSeekerDragging=false});\n manualSeeker.addEventListener(\'pointercancel\',()=>{manualSeekerDragging=false});\n manualSeeker.addEventListener(\'input\',requestSeek);\n manualSeeker.addEventListener(\'change\',requestSeek);\n}\n\ninstallManualSeeker();\nmixerRoot?.addEventListener(\'ezscore:audio-timeupdate\',e=>{\n const sec=Math.max(0,Number(e.detail?.time||0));\n const duration=Math.max(0,Number(e.detail?.duration||0));\n if(manualSeeker){\n  if(duration>0&&Math.abs(Number(manualSeeker.max||0)-duration)>.05)manualSeeker.max=String(duration);\n  if(!manualSeekerDragging)manualSeeker.value=String(Math.min(sec,Number(manualSeeker.max||sec)));\n }\n if(manualSeekerOutput)manualSeekerOutput.textContent=formatSeekerTime(sec);\n highlightAt(sec);\n});\ncapoSelect?.addEventListener(\'change\',()=>{capo=Number(capoSelect.value||0);render();autoSaveSettings()});\n','seeker consolidated')
        css=src['css'].rstrip()+'\n\n'+'/* R41.0F — ChordsLab manual seeker on shared audio clock */\n.chordslab-manual-seeker{\n    width:100%;\n    padding:8px 10px;\n    border:1px solid #33424d;\n    border-radius:9px;\n    background:#101920;\n}\n.chordslab-manual-seeker label{\n    display:grid;\n    grid-template-columns:auto minmax(140px,1fr) 72px;\n    align-items:center;\n    gap:10px;\n    margin:0;\n}\n.chordslab-manual-seeker span{\n    color:#9fb1bb;\n    font-size:10px;\n    font-weight:800;\n    letter-spacing:.04em;\n    text-transform:uppercase;\n}\n.chordslab-manual-seeker input[type=range]{width:100%;min-width:0}\n.chordslab-manual-seeker output{\n    min-width:72px;text-align:right;color:#eef5f8;\n    font-family:ui-monospace,SFMono-Regular,Consolas,monospace;\n    font-size:12px;font-weight:700;\n}\n@media(max-width:640px){\n    .chordslab-manual-seeker label{grid-template-columns:auto 1fr}\n    .chordslab-manual-seeker input[type=range]{grid-column:1/-1;grid-row:2}\n    .chordslab-manual-seeker output{grid-column:2;grid-row:1;justify-self:end}\n}\n'
        t=src['twig']
        t=rep(t,'/assets/css/chordslab.css?v=20260930r39_3a','/assets/css/chordslab.css?v=20261001r41_0f','CSS cache')
        t=rep(t,'/assets/js/chordslab.js?v=20260930r39_3','/assets/js/chordslab.js?v=20261001r41_0f','JS cache')

        contracts=[
          ('APP_VERSION = "R41.0F"' in w,'worker version'),
          ('timeout=60,' in w,'60s probe'),
          ('Diagnostics:' in w,'diagnostics'),
          ('import lv_chordia' in f,'finder lv'),
          ('$env:EZSCORE_STEM_PYTHON = $ExpectedPython' in s,'explicit env'),
          ('pythonw.exe missing in Worker venv' in s,'pythonw mandatory'),
          (b.find('Remove-Item $BootstrapFile') < b.find('start_analysis_worker_desktop.ps1'),'bootstrap order'),
          ('Prepare CI environment file' in c,'CI env step'),
          ('data-chordslab-manual-seeker' in j,'seeker'),
          ('new Audio(' not in j and 'new AudioContext' not in j,'no parallel audio'),
          ('/* R41.0F — ChordsLab manual seeker on shared audio clock */' in css,'seeker CSS'),
        ]
        failed=[n for ok,n in contracts if not ok]
        if failed: raise RuntimeError('R41.0F invariant failed: '+', '.join(failed))

        write_atomic(FILES['worker'],w)
        write_atomic(FILES['start'],s,bom=True)
        write_atomic(FILES['finder'],f,bom=True)
        write_atomic(FILES['backend'],b,bom=True)
        write_atomic(FILES['ci'],c)
        write_atomic(FILES['js'],j)
        write_atomic(FILES['css'],css)
        write_atomic(FILES['twig'],t)

        p=subprocess.run([sys.executable,'-m','py_compile',str(FILES['worker'])],cwd=str(ROOT),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace',check=False)
        if p.returncode!=0: raise RuntimeError('Worker py_compile failed:\n'+p.stdout)
        print('R41_0F_FULL_LAUNCHER_CI_SEEKER_INSTALL_OK')
        return 0
    except Exception:
        for k,data in original.items(): FILES[k].write_bytes(data)
        raise

if __name__=='__main__':
    try: raise SystemExit(main())
    except Exception as exc:
        print(f'ERROR: {exc}',file=sys.stderr)
        raise SystemExit(1)
