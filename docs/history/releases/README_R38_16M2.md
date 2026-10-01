# EZScore_v1 — R38.16m2 — Analyze lyrics vs dirty guard

Regression ciblée:
- clic sur **Analyser les paroles**
- aucun job Lyrics en queue
- la page bouge/scroll mais le POST n'atteint pas le contrôleur

Cause:
`lyrics-dirty-guard-r38-16j.js` intercepte tous les formulaires lorsque le textarea est
modifié, sauf le formulaire de sauvegarde d'historique. Or `lyrics-analyze-form`
DOIT pouvoir être soumis avec le texte courant : le textarea lui est explicitement
associé par `form="lyrics-analyze-form"`.

Correction:
- `lyrics-analyze-form` est exempté du dirty guard;
- le dirty guard reste actif pour les navigations et pour `Extraire les paroles`
  lorsqu'un texte non sauvegardé serait perdu;
- aucun autosave sur frappe;
- cache-bust du JS.

Commandes:

```powershell
cd H:\EZScore_v1

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R38_16M2_ANALYZE_DIRTY_GUARD_FIX.zip" -C H:\EZScore_v1

python .\scripts\install_r38_16m2_analyze_dirty_guard_fix.py H:\EZScore_v1

php .\tests\r38_16m2_analyze_dirty_guard_fix_contract.php H:\EZScore_v1

php bin\console cache:clear
php bin\console cache:warmup

git status --short
```

Attendu:
- `R38_16M2_ANALYZE_DIRTY_GUARD_FIX_INSTALL_OK`
- `R38_16M2_ANALYZE_DIRTY_GUARD_FIX_CONTRACT_OK`
