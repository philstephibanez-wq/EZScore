# EZScore — Chœurs visibles dans l'éditeur

Base GitHub relue avant livraison :

```text
repository : philstephibanez-wq/EZScore
branch     : restore/full-reanalysis-r1
HEAD       : 1226009aa4713380314fb47aa8f47ca707d8944b
```

## Correction

Le Player d'analyse affiche déjà les paroles Chœurs.

L'éditeur utilisait encore l'ancien chemin :

```text
whisper_vocals_small.json
→ _merge_vocal_gap_words()
→ _supplement_only_words()
```

Cette livraison modifie uniquement :

```text
ezscore/ui/lyrics_inline_editor.py
```

L'éditeur lit désormais la même source technique Chœurs que l'analyse :

```text
choir_analysis.json
→ load_choir_analysis()
→ words
→ ligne Chœurs de l'éditeur
```

Aucun changement de l'analyse Chant principale.
Aucun changement du Player.
Aucun fallback Chœurs.
Aucune règle spécifique à une chanson.

`chords_lyrics_editor.py` appelle déjà `lyrics_inline_editor._load_backing_words()`,
donc cette correction alimente aussi la ligne Chœurs de cet éditeur sans autre
modification.

## Installation PowerShell

```powershell
$zip = "$env:USERPROFILE\Downloads\EZScore_EDITOR_CHOIRS_R1.zip"
$tmp = "$env:USERPROFILE\Downloads\EZScore_EDITOR_CHOIRS_R1"

Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue

Expand-Archive `
  -Path $zip `
  -DestinationPath $tmp `
  -Force

Copy-Item `
  "$tmp\ezscore\ui\lyrics_inline_editor.py" `
  "H:\EZScore\ezscore\ui\lyrics_inline_editor.py" `
  -Force

cd H:\EZScore

python -m py_compile .\ezscore\ui\lyrics_inline_editor.py

git diff --check
git diff -- .\ezscore\ui\lyrics_inline_editor.py
git status --short
```

Redémarrer ensuite Streamlit :

```powershell
cd H:\EZScore
python -m streamlit run EZScore.py
```

Le résultat attendu est que la ligne Chœurs visible dans le Player d'analyse
soit également alimentée dans l'éditeur à partir de `choir_analysis.json`.
