# EZScore — correctif pré-roll / post-roll des paroles

Base vérifiée : `master` au commit `f2c6a6fc066e6a77d932f8e0e6e666de0a3529bc`
(`EZScore_R30_ANALYSIS_V2`).

## But

Corriger la disparition des paroles chantées avant la première mesure détectée,
sans toucher au moteur R33 de découpage intelligent et sans déplacer aucun
timestamp.

Exemple concerné : **Tombe la neige**.

Le chanteur peut commencer avant la première mesure musicale. Ces mots doivent
donc rester visibles et synchronisés.

## Correction

`ezscore/ui/app_shell.py` conserve la compatibilité R30 existante et ajoute un
pont temporaire vers l'architecture à trois timelines.

Le moteur R33 fournit déjà une enveloppe visuelle correcte :

- premier bloc : peut commencer avant la mesure 1 ;
- dernier bloc : peut finir après la dernière mesure détectée.

Le code R30 reconstruisait ensuite les bornes depuis les mesures et perdait
cette information.

Le correctif :

1. conserve l'enveloppe temporelle R33 lors de la matérialisation ;
2. étend uniquement le premier et le dernier intervalle visuel ;
3. applique la même enveloppe dans l'éditeur **Paroles des blocs** ;
4. ne touche jamais aux frontières temporelles des blocs intermédiaires.

## Invariants

```text
timestamp accord  : inchangé
timestamp phonème : inchangé
timestamp mot     : inchangé
moteur structure R33 : inchangé
```

Les blocs restent une vue éditoriale.

## Trace

Quand un pré-roll ou post-roll est effectivement récupéré :

```text
[EZTRACE][LYRICS_ENVELOPE] measure=... visual=...
```

## Fichiers

```text
ezscore/ui/app_shell.py
readme.md
```

Aucun fichier SSO/auth modifié.
Aucune base SQLite.
Aucun audio.
Aucun script `apply_*.py`.

## Installation

Dézipper le ZIP directement dans `H:\EZScore` en conservant l'arborescence.

Puis :

```powershell
cd H:\EZScore
python -m py_compile .\ezscore\ui\app_shell.py
python -m py_compile .\EZScore.py
python -m compileall -q .\ezscore
python -m streamlit run .\EZScore.py
```

## Recette immédiate

Ouvrir **Tombe la neige** puis `Blocs > Édition`.

Le premier bloc doit maintenant contenir aussi les mots Whisper situés avant
le début de la mesure 1.

Aucune réanalyse Demucs / Whisper n'est nécessaire pour ce test.
