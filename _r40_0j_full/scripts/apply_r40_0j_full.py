#!/usr/bin/env python3
from __future__ import annotations
import subprocess, sys
from pathlib import Path
BASE_COMMIT='e786dc41269460fda2270ae87c677937484fd429'
ROOT=Path(sys.argv[1] if len(sys.argv)>1 else r'H:\EZScore_v1').resolve()
LAUNCH_REL='scripts/launch_ezscore_backend.ps1'
HTA_REL='EZScore-Launcher.hta'
LAUNCH=ROOT/LAUNCH_REL
HTA=ROOT/HTA_REL

def git(*args):
    return subprocess.run(['git',*args],cwd=str(ROOT),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',errors='replace',check=False)

def git_show(path):
    p=git('show',f'HEAD:{path}')
    if p.returncode!=0: raise RuntimeError(f'git show failed: {path}: {p.stderr.strip()}')
    return p.stdout.replace('\r\n','\n').replace('\r','\n')

def repl(text,old,new,label):
    n=text.count(old)
    if n!=1: raise RuntimeError(f'{label}: expected 1 anchor, found {n}')
    return text.replace(old,new,1)

def guard():
    p=git('rev-parse','HEAD')
    if p.returncode!=0: raise RuntimeError('git rev-parse HEAD failed')
    if p.stdout.strip()!=BASE_COMMIT: raise RuntimeError(f'HEAD={p.stdout.strip()}; expected {BASE_COMMIT}. STOP.')
    if git('diff','--quiet').returncode!=0: raise RuntimeError('Tracked working-tree changes detected. STOP.')
    if git('diff','--cached','--quiet').returncode!=0: raise RuntimeError('Staged changes detected. STOP.')

def write_atomic(path,text):
    tmp=path.with_suffix(path.suffix+'.r40j.tmp')
    tmp.write_text(text,encoding='utf-8',newline='\n')
    tmp.replace(path)

def main():
    guard()
    originals={LAUNCH:LAUNCH.read_bytes(),HTA:HTA.read_bytes()}
    launch=git_show(LAUNCH_REL)
    hta=git_show(HTA_REL)
    try:
        launch=repl(launch,'    $BrowserUrl = if ($env:EZSCORE_BROWSER_URL) { $env:EZSCORE_BROWSER_URL.TrimEnd(\'/\') } else { "https://ezscore.logandplay.com" }\n    $ControlFile = Join-Path $RuntimeDir "ezscore-server-control.json"\n    try {\n        if (Test-Path $ControlFile) {\n            $Control = Get-Content $ControlFile -Raw | ConvertFrom-Json\n            if ($Control.worker.target -eq "local") {\n                $BrowserUrl = "http://127.0.0.1:8502"\n            }\n        }\n    } catch {}\n\n    Set-LauncherStatus "browser" "Ouverture de EZScore..." 92 "running" $BrowserUrl\n    Start-Process ($BrowserUrl + "/fr/catalog")\n\n    Set-LauncherStatus "ready" "EZScore est prêt." 100 "ready" "Le Worker gère les serveurs ONLINE et LOCAL ainsi que leurs états persistés."\n','    Set-LauncherStatus "ready" "EZScore Worker prêt." 100 "ready" "Aucune page web n\'est ouverte automatiquement. Utilisez le bouton Ouvrir du serveur ONLINE ou LOCAL."\n','remove auto browser')
        hta=repl(hta,'<meta http-equiv="X-UA-Compatible" content="IE=Edge" />\n','<meta http-equiv="X-UA-Compatible" content="IE=Edge" />\n<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />\n','utf8 meta')
        hta=repl(hta,'        var file = fso.OpenTextFile(statusFile, 1, false, -1);\n        var text = file.ReadAll();\n        file.Close();\n\n        var data = JSON.parse(text);\n','        var stream = new ActiveXObject("ADODB.Stream");\n        stream.Type = 2;\n        stream.Charset = "utf-8";\n        stream.Open();\n        stream.LoadFromFile(statusFile);\n        var text = stream.ReadText();\n        stream.Close();\n\n        var data = JSON.parse(text);\n','utf8 reader')
        hta=repl(hta,'    setDetail(\n        "Serveur local :\\n" +\n        "php -S 127.0.0.1:8501 -t " + root + "\\\\public\\n\\n" +\n        "Site ouvert dans Chrome :\\n" +\n        "https://ezscore.logandplay.com/"\n    );\n','    setDetail(\n        "Initialisation du Worker et restauration des états ONLINE / LOCAL.\\n\\n" +\n        "Aucune page web ne sera ouverte automatiquement."\n    );\n','launcher detail')
        assert 'Start-Process ($BrowserUrl' not in launch
        assert '$BrowserUrl =' not in launch
        assert 'ADODB.Stream' in hta
        assert 'Charset = "utf-8"' in hta
        write_atomic(LAUNCH,launch)
        write_atomic(HTA,hta)
        print('R40_0J_FULL_NO_AUTO_BROWSER_UTF8_SPLASH_INSTALL_OK')
        return 0
    except Exception:
        for p,data in originals.items(): p.write_bytes(data)
        raise

if __name__=='__main__':
    try: raise SystemExit(main())
    except Exception as exc:
        print(f'ERROR: {exc}',file=sys.stderr)
        raise SystemExit(1)
