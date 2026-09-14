# EZScore — séparation analyse primaire / structure visuelle

Cette livraison pose la séparation demandée sans toucher au SSO/auth ni à
l'éditeur existant.

## 1. Analyse primaire : 3 timelines synchronisées

Nouveau module :

`ezscore/analysis/timelines.py`

Il construit trois timelines sur **la même horloge audio en secondes** :

### Accords

Chaque beat possède :

- `id` stable ;
- `start` / `end` ;
- accord ;
- beat ;
- mesure ;
- confiance.

Cette timeline est destinée à devenir la source unique du MIDI.

### Paroles

Chaque mot Whisper possède :

- `id` stable ;
- `start` / `end` ;
- texte ;
- index mot / segment.

### Phonèmes

Chaque phonème possède :

- `id` stable ;
- `start` / `end` ;
- `word_id` ;
- phonème.

Important : pour l'instant le phonème est **dérivé de Whisper** et son temps est
interpolé à l'intérieur du mot. Il est explicitement marqué :

```text
source = whisper-derived
acoustic = false
```

Il ne faut donc pas le confondre avec une future détection acoustique réelle.

## 2. Analyse secondaire : structure visuelle

Nouveau module :

`ezscore/analysis/structure.py`

Il lit les mesures et les motifs d'accords et propose des blocs visuels.

Les blocs portent :

```text
visual_only = true
```

Ils ne modifient jamais les timestamps accords / phonèmes / paroles.

Le moteur cherche des **séquences harmoniques répétées**, pas un simple
découpage toutes les 4 mesures.

## Compatibilité R30

`ezscore/transcription.py` conserve la fonction historique :

`detecter_sections_structurelles(...)`

mais elle délègue maintenant au nouveau module structure.

Donc l'application existante continue de fonctionner pendant la migration.

## Invariant à respecter pour les prochaines étapes

```text
TIMELINES = vérité temporelle
BLOCS = vue éditoriale / navigation seulement
MIDI = rendu de la timeline accords
```

Déplacer ou renommer un bloc ne doit jamais déplacer un accord, un phonème ou
un mot.

## Fichiers livrés

```text
ezscore/analysis/__init__.py
ezscore/analysis/timelines.py
ezscore/analysis/structure.py
ezscore/transcription.py
readme.md
```

Aucun `apply_*.py`.
Aucun fichier auth/SSO.
Aucune base SQLite.

## Compilation

```powershell
cd H:\EZScore
python -m py_compile .\ezscore\analysis\__init__.py
python -m py_compile .\ezscore\analysis\timelines.py
python -m py_compile .\ezscore\analysis\structure.py
python -m py_compile .\ezscore\transcription.py
python -m py_compile .\EZScore.py
python -m compileall -q .\ezscore
```

## Test immédiat

Relancer EZScore et réinitialiser la structure depuis l'analyse.

La console doit maintenant montrer :

```text
[EZTRACE][VISUAL_STRUCTURE] ...
```

La prochaine étape sera de brancher explicitement le MIDI sur
`timeline["chords"]`, puis les corrections de paroles et d'accords sur leurs IDs
stables, sans dépendre des bornes de blocs.


---

# R33 — découpage intelligent variable

Le moteur de structure ne travaille plus avec des blocs finaux de 4 mesures.

Il analyse maintenant les **mesures individuellement** et recherche des phrases
harmoniques répétées de longueur variable.

Plage de recherche automatique :

```text
6/8 mesures minimum selon la longueur du morceau
jusqu'à 24 mesures
```

Cette plage est interne au moteur : ce n'est pas une taille de bloc imposée.

Les paroles n'interviennent qu'en second niveau pour départager des candidats
harmoniques proches.

Le moteur refuse volontairement le fallback :

```text
1-4 / 5-8 / 9-12 / ...
```

En l'absence de structure suffisamment fiable, il préfère un grand bloc ou une
coupure de forte nouveauté harmonique plutôt qu'un faux découpage régulier.

Trace attendue :

```text
[EZTRACE][VISUAL_STRUCTURE_R33]
top_candidates=[...]
selected=[...]
ranges=[...]
```

`top_candidates` permet de voir ce que le moteur reconnaît réellement.
`selected` contient seulement les répétitions retenues comme ancres de
structure. Toutes les ressemblances ne deviennent donc plus une frontière.

Le premier et le dernier bloc étendent aussi leur enveloppe visuelle aux
paroles situées avant la première mesure ou après la dernière mesure, sans
modifier aucun timestamp.
