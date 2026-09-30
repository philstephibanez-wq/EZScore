# EZScore_v1 — R39.3A Modal hidden

Micro-correctif strictement limité à la popup de réanalyse des accords.

## Problème

Le `<dialog data-chord-analyze-dialog>` reste visuellement présent alors qu'il n'a pas
l'attribut `open`.

## Correction

Le CSS impose explicitement :

```css
dialog.ez-modal:not([open]),
dialog[data-chord-analyze-dialog]:not([open]){
    display:none!important;
}
```

et rétablit `display:block` uniquement lorsque le dialog porte `[open]`.

Aucune modification :
- prompteur ;
- timeline ;
- diagramme ;
- moteur `translate3d()` ;
- player ;
- analyse harmonique ;
- visual settings.

## Installation

```powershell
cd H:\EZScore_v1

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R39_3A_MODAL_HIDDEN.zip" -C H:\EZScore_v1

H:\EZScore\.venv-py313\Scripts\python.exe .\_r39_3a\scripts\apply_r39_3a.py H:\EZScore_v1

H:\EZScore\.venv-py313\Scripts\python.exe .\_r39_3a\tests\r39_3a_modal_hidden_contract.py H:\EZScore_v1

php bin\console cache:clear

git diff --check
git status --short
```

Attendu :

```text
R39_3A_MODAL_HIDDEN_INSTALL_OK
R39_3A_MODAL_HIDDEN_CONTRACT_OK
```
