#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT=Path(sys.argv[1] if len(sys.argv)>1 else r'H:\EZScore_v1').resolve()
launch=(ROOT/'scripts/launch_ezscore_backend.ps1').read_text(encoding='utf-8')
hta=(ROOT/'EZScore-Launcher.hta').read_text(encoding='utf-8')
assert 'Start-Process ($BrowserUrl' not in launch
assert '$BrowserUrl =' not in launch
assert 'Aucune page web n\'est ouverte automatiquement.' in launch
assert '<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />' in hta
assert 'new ActiveXObject("ADODB.Stream")' in hta
assert 'stream.Charset = "utf-8";' in hta
assert 'Aucune page web ne sera ouverte automatiquement.' in hta
print('R40_0J_FULL_NO_AUTO_BROWSER_UTF8_SPLASH_CONTRACT_OK')
