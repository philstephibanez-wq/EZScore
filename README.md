# EZScore Choir Analyzer V4.2

Base vérifiée : `restore/full-reanalysis-r1`
commit `6ad15d81ab689e99de9b838eb400f5d4641e4904` (V4.1).

Livraison différentielle : uniquement le fichier modifié complet à son chemin
final, plus ce `readme.md`.

V4.2 conserve le rejet V4.1 des hallucinations à backing_share quasi nul et
ajoute :
- waveform_correlation
- residual_ratio
- classe backing_independent_weak pour les vrais doublages faibles.

Application :

```powershell
cd H:\EZScore
tar -xf "$env:USERPROFILE\Downloads\EZScore_CHOIR_V4_2_FULL.zip" -C H:\EZScore
python -m py_compile .\ezscore\analysis\choirs.py
python -m ezscore.analysis.choirs `
  --audio-hash "41ea46f13ff411c003e180e719844f944af3366aad4183060121e78f99c478d0" `
  --force
```

La bannière doit être `CHOIR ANALYSIS V4.2`.
