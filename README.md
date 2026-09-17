# EZScore — EDITOR R1

Base de référence obligatoire :
`stable-karaoke-pre-editor` / `45a912e322129359c1a7bbb9aa36feae8d256a6e`

## Analyse d'impact

### Fichier modifié
- `ezscore/backoffice/player.py`

### Fichiers explicitement non modifiés
- `ezscore/player/karaoke_stem_webaudio_r12c.py`
- `ezscore/player/karaoke_stem_webaudio.py`
- `ezscore/ui/__init__.py`
- `ezscore/ui/stem_lab_analysis.py`
- `ezscore/analysis/*`
- `ezscore/persistence.py`
- `ezscore/printing.py`
- `EZScore.py`
- `data/*`

Le moteur audio validé n'est donc pas modifié.

## Fonctions ajoutées

Dans le player d'édition uniquement :

1. `⚑ Ancres + paroles`
   - modification du nom de section ;
   - modification de l'ancre de début en numéro de mesure ;
   - ancres strictement croissantes ;
   - première ancre obligatoirement mesure 1 ;
   - les fins de sections sont dérivées de l'ancre suivante ;
   - paroles éditables avec sauts de ligne ;
   - validation commune ancres + paroles.

2. `♬ Accords beat par beat`
   - mesure et beat non modifiables ;
   - timestamp visible mais non modifiable ;
   - seul le symbole d'accord est éditable ;
   - stockage via la couche `measure_edits` déjà utilisée par EZScore ;
   - aucun timestamp ni résultat d'analyse n'est modifié.

## Zéro fallback

Le nouveau code n'invente aucune structure ni aucune valeur :
- structure absente => erreur explicite ;
- ancre invalide => sauvegarde refusée ;
- nombre de blocs incohérent => sauvegarde refusée ;
- beat manquant => sauvegarde refusée ;
- symbole vide / avec espace / excessivement long => sauvegarde refusée ;
- aucune correction automatique ou valeur de secours n'est appliquée.

Les valeurs non modifiées restent simplement les valeurs canoniques existantes :
ce n'est pas un fallback d'exécution.

## Non-régression attendue

À retester après installation :
- player karaoké stable inchangé en Vue ;
- Original / Mix STEM ;
- volumes et EQ ;
- vitesse pitch-preserved ;
- seek / pause / reprise ;
- Chant ;
- Chœurs / `la la la` ;
- diagrammes ;
- mesure ;
- accord courant ;
- grille Vue ;
- paroles Vue ;
- impression.

## Installation

```powershell
cd H:\EZScore

Expand-Archive `
  -Path "$env:USERPROFILE\Downloads\EZScore_EDITOR_R1_anchors_lyrics_chords.zip" `
  -DestinationPath . `
  -Force

python -m py_compile .\ezscore\backoffice\player.py

git diff --check
git status --short
```

## Contrôle de portée Git avant test

La commande suivante doit montrer uniquement :

`ezscore/backoffice/player.py`

```powershell
git diff --name-only stable-karaoke-pre-editor
```

Ne pas pousser avant validation fonctionnelle.
