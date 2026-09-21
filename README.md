# EZScore_FULL_REANALYSIS_DUPKEY_R1

Base vérifiée sur GitHub au moment de la livraison :

```text
master = 0448b6028fed4b826636f852ffda3fcc9a28e263
```

## Erreur corrigée

```text
StreamlitDuplicateElementKey:
full_reanalysis_confirm_<hash>
```

Deux routes legacy peuvent atteindre la même surface Analyse au cours d'un même
rerun Streamlit. Le contrôle destructif `Réanalyse complète` utilisait
correctement une clé stable par chanson, mais était alors créé deux fois.

## Correction

`render_full_reanalysis_control()` est désormais un **singleton par chanson et
par script run**.

Avant de créer l'expander ou ses widgets, il consulte le
`ScriptRunContext.widget_user_keys_this_run` courant :

- si `full_reanalysis_confirm_<hash>` ou `full_reanalysis_<hash>` a déjà été
  enregistré pendant ce rerun, le second rendu est ignoré ;
- sinon le contrôle est rendu normalement.

Aucune clé aléatoire ou suffixée n'est créée. Le reset reste une seule action
sémantique et le comportement de `full_reanalysis_reset()` n'est pas modifié.

## Application

```powershell
cd H:\EZScore

tar -xf "$env:USERPROFILE\Downloads\EZScore_FULL_REANALYSIS_DUPKEY_R1.zip" -C H:\EZScore

.\.venv-py313\Scripts\python.exe -m py_compile `
  .\ezscore\ui\analysis_lifecycle.py `
  .\scripts\test_full_reanalysis_singleton.py

.\.venv-py313\Scripts\python.exe .\scripts\test_full_reanalysis_singleton.py
```

Attendu :

```text
FULL REANALYSIS SINGLETON CONTRACT OK
duplicate widget key: guarded before rendering
reset semantics: unchanged
random/suffixed widget keys: NONE
```

Puis redémarrer complètement Streamlit et relancer `Réanalyse complète`.

Le correctif ne touche ni Whisper, ni STEM, ni SSO, ni la timeline.
