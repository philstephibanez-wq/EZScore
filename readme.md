# EZScore_v1 — R35.2

**R35.2 remplace intégralement R35.1. Ne pas appliquer R35.1 avant.**

Base corrigée pour ton dépôt actuel :

`535ac59dbbb4797d41779ca0c36ba102d81712c2` (`EZScore_v1_R34_6_TEMPO_TYPOGRAPHY`)

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
# 535ac59dbbb4797d41779ca0c36ba102d81712c2

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


## Correctif de packaging

Cette reconstruction corrige l’erreur du premier ZIP R35.2 qui était verrouillé par erreur sur R34.5.
Elle s’applique directement sur R34.6 (`535ac59`) et conserve toutes les corrections R34.6.

Après application, `debug:router` DOIT afficher :

```text
/internal/analysis/desktop/jobs/queue
```

et la fenêtre Analysis doit contenir `Traitements en cours / à faire`.


## R35.3 WORKFLOW DASHBOARD
Analyse devient le tableau de bord chanson; workflow strict Import → Stems → Accords → Paroles → Publication.


## R35.4 RECOVERY + COLLAB + CONTACT
Jobs orphelins >120s requeue; propriétaire inchangé; délégations owner/admin; doublons import; contact admin indirect.


## R35.4a HOTFIX
- routes Contact/Collaborateurs enregistrées ;
- contact admin déplacé dans l’entête globale authentifiée ;
- lease des jobs réellement rafraîchi par heartbeat Worker ;
- queue desktop cohérente avec le job local réellement en cours.


## R35.5 UX + COLLAB + MAIL
Dashboard simplifié, Répertoire, délégations visibles et fonctionnelles, propriétaire explicite, contact admin corrigé.


## R35.5a WORKFLOW TABS FIX
Restaure la navigation complète du workflow. Seul le premier onglet devient `TABLEAU DE BORD`; Import, Édition, StemsLab, ChordsLab, LyricsLab et Publication restent présents et gardent leur verrouillage par prérequis.
