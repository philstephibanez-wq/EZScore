# EZScore_v1 — R39.2D Shared Visual Settings

Ce lot remplace le panneau de réglages Chords par un composant Twig partagé et l'ajoute dans Lyrics.

## Périmètre

Uniquement :
- Capo
- Signature
- Niveau d'analyse
- Afficher les accords guitare
- layout responsive
- persistance du toggle diagramme
- sauvegarde des réglages dans Lyrics via le même endpoint existant

Aucun changement de :
- timeline Chords ;
- timeline Lyrics ;
- player ;
- analyse ;
- diagramme lui-même.

## Responsive

Desktop :
`Capo | Signature | Niveau | Afficher les accords guitare`

Tablette portrait :
3 contrôles en ligne, toggle dessous.

Smartphone :
Capo + Signature, puis Niveau pleine largeur, puis toggle.

Très petit smartphone :
empilé.

## Important

Dans Chords, `chordslab.js` reste propriétaire du comportement immédiat existant.

Dans Lyrics, le composant sauvegarde puis recharge la page pour appliquer proprement Capo/Signature/Niveau sans toucher au renderer Lyrics dans ce lot.

Le toggle "Afficher les accords guitare" partage déjà son état entre Chords et Lyrics via :
`ezscore:visual:guitar-diagram`

Le raccord effectif du diagramme dans Lyrics viendra dans un lot séparé.

## Installation

```powershell
cd H:\EZScore_v1

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R39_2D_SHARED_VISUAL_SETTINGS.zip" -C H:\EZScore_v1

H:\EZScore\.venv-py313\Scripts\python.exe .\_r39_2d\scripts\apply_r39_2d.py H:\EZScore_v1

H:\EZScore\.venv-py313\Scripts\python.exe .\_r39_2d\tests\r39_2d_shared_visual_settings_contract.py H:\EZScore_v1

php bin\console cache:clear
php bin\console cache:warmup

git diff --check
git status --short
```

Attendu :

```text
R39_2D_SHARED_VISUAL_SETTINGS_INSTALL_OK
R39_2D_SHARED_VISUAL_SETTINGS_CONTRACT_OK
```
