# EZScore_STEM_CONDUCTOR_R2

Base GitHub vérifiée :

```text
master = 6e48c339dfff9c7d64ceeb274ff1d6d421438528
EZScore_STEM_LAZY_UI_R1
```

## Cause exacte

Le moteur historique déclarait `activeWordIndex` dans une portion de JavaScript
qui a été remplacée par le conducteur continu.

Le nouveau code utilisait encore :

```javascript
if (wordIndex !== activeWordIndex) {
    activeWordIndex = wordIndex;
}
```

mais la variable n'était plus déclarée.

Le navigateur interrompait donc l'initialisation du conducteur avec un
`ReferenceError`, alors que le mixer WebAudio restait visible.

R2 ajoute :

```javascript
let activeWordIndex = -2;
```

et effectue le premier layout dans `requestAnimationFrame()`.

## Contrôle des données

La légende du conducteur affiche maintenant :

```text
Payload : N beats · M mots
```

Pour les deux analyses déjà diagnostiquées, on attend typiquement :

```text
338 beats · 139 mots
528 beats · 430 mots
```

## Ergonomie

Le bouton `✕ Fermer le lecteur STEM` est supprimé.

Le lecteur reste ouvert tant que l'utilisateur reste dans STEM, puis il est
automatiquement déchargé lorsqu'il quitte l'étape STEM. Cela évite un bouton
inutile dans le parcours télécommande Android.

## Application

```powershell
cd H:\EZScore

tar -xf "$env:USERPROFILE\Downloads\EZScore_STEM_CONDUCTOR_R2.zip" -C H:\EZScore

.\.venv-py313\Scripts\python.exe .\scripts\apply_stem_conductor_r2.py

.\.venv-py313\Scripts\python.exe -m py_compile `
  .\ezscore\player\stem_analysis_conductor.py `
  .\ezscore\ui\stem_lab_analysis.py `
  .\scripts\test_stem_conductor_r2_contract.py

$env:PYTHONPATH = "H:\EZScore"
.\.venv-py313\Scripts\python.exe .\scripts\test_stem_conductor_r2_contract.py
```

Attendu :

```text
PATCH OK
 - bug JS activeWordIndex corrigé
 - premier rendu conducteur différé après layout
 - compteurs beats/mots visibles
 - bouton Fermer le lecteur STEM supprimé

STEM CONDUCTOR R2 CONTRACT OK
activeWordIndex declared: YES
initial conductor layout deferred: YES
payload counts visible: YES
explicit close button removed: YES
```

Puis redémarrer Streamlit.
