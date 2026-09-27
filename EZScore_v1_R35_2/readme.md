# EZScore_v1 — R35.2

**R35.2 remplace intégralement R35.1. Ne pas appliquer R35.1 avant.**

Base attendue :

`d2a7dc22588044c81f67f8610f4b9820620e91c4` (`EZScore_v1_R34_5_HARD_FIX`)

## R35.2

### Analysis Worker

- démarrage automatique du serveur local puis du Worker ;
- `Démarrer Worker` lorsqu'il est arrêté ;
- `Redémarrer Worker` lorsqu'il tourne ;
- redémarrage interdit pendant un job actif ;
- attente réelle (`join`) de l'ancien thread avant toute relance ;
- commandes serveur indépendantes : `Démarrer serveur` / `Arrêter serveur` ;
- nouvelle zone **Traitements en cours / à faire** ;
- lecture toutes les 2 secondes de la file persistée dans `AnalysisJob` ;
- colonnes : ID, état, type, chanson, progression ;
- affichage des jobs `running` et `queued` : fermer l'UI n'efface donc pas cette liste côté serveur.

### Éditeur

Dans le sélecteur du répertoire admin :

- suppression de `Conserver l'éditeur — ...` ;
- l'éditeur courant est affiché uniquement par son nom ;
- les autres choix restent uniquement les noms des éditeurs ;
- si aucun éditeur n'est affecté : `—`.

### R35.1 inclus

R35.2 reprend directement les fonctions prévues dans R35.1 :

- Auto métrique `2/4`, `3/4`, `4/4`, `6/8` ;
- batterie prioritaire, basse et harmonie complémentaires ;
- hypothèses signature × phase sur plusieurs mesures, sans assimiler l'accent maximal au temps 1 ;
- réimport audio destructif des analyses dérivées avec retour à `Importée` ;
- source audio identifiée par SHA, ce qui empêche la réutilisation des artefacts stems/accords de l'ancien audio.

## Installation — PowerShell

```powershell
cd H:\EZScore_v1

git rev-parse HEAD
# attendu :
# d2a7dc22588044c81f67f8610f4b9820620e91c4

# Décompresser R35.2 directement. NE PAS installer R35.1.
tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R35_2.zip" -C H:\EZScore_v1

# Appliquer
python .\EZScore_v1_R35_2\scripts\apply_r35_2.py H:\EZScore_v1

# Symfony
php bin\console cache:clear
php bin\console lint:container
php bin\console lint:twig templates
php bin\console debug:router | findstr /I "analysis desktop queue reimport"

# Python
python -m py_compile .\worker_app\ezscore_analysis_worker.pyw
python -m py_compile .\analysis\meter_detection_r35_2.py
python -m py_compile .\analysis\chord_timeline_analysis.py

# Contrat R35.2
php .\EZScore_v1_R35_2\tests\r35_2_contract.php H:\EZScore_v1

# Avant TON push
git status --short
git diff --check
git diff
```

Résultat attendu :

```text
R35_2_CONTRACT_OK
```

Le script ne committe et ne pousse rien. Il refuse de modifier une autre base Git que le commit prévu.
