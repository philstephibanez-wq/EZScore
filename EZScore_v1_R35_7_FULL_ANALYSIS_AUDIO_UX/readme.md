# EZScore_v1 — R35.7 FULL ANALYSIS + AUDIO + UX

Ce livrable consolide **tout ce qui vient d’être défini**.  
À appliquer sur l’arbre local après R35.5a.

## 1. Modales EZScore — plus de popup navigateur

- remplacement de la confirmation navigateur lors du remplacement audio ;
- remplacement de la confirmation navigateur lors de la suppression catalogue ;
- modale EZScore globale réutilisable ;
- audit automatique des Twig + JS : le patch s’arrête si un `confirm()` ou `alert()` natif subsiste.

## 2. Filtrage live optionnel

Dans ChordsLab :

`☐ Filtrer applaudissements / foule pour l’analyse`

- désactivé par défaut ;
- n’altère jamais le MP3 original ;
- agit uniquement sur les signaux utilisés pour l’analyse ;
- HPSS + détection de frames transitoires / broadband pour atténuer applaudissements et bruit de foule ;
- rythme et harmonie sont filtrés quand l’option est active.

## 3. Timeline musicale complète et mesures vides

La grille ne commence plus au premier accord détecté.

- le beat grid est conservé/reconstruit jusqu’au début de la source ;
- une intro batterie/percussion/ambiance musicale produit donc ses mesures ;
- si aucune harmonie fiable n’est présente, les beats de ces mesures sont `.` ;
- le dernier accord n’est plus artificiellement prolongé à travers une vraie zone sans harmonie ;
- le prompteur reste aligné avec la timeline audio absolue.

## 4. Finalité harmonique : accompagnement guitare

Le moteur ne cherche pas « la guitare existante ».  
Il cherche **l’harmonie utile pour accompagner le chanteur ou le lead à la guitare**.

Sources utilisables :
- guitare ;
- piano ;
- basse / fondamentale ;
- orgue ;
- pads / nappes ;
- synthés ;
- cordes ;
- stem `other` harmonique ;
- mix original en secours.

Ainsi un morceau sans guitare peut quand même produire une grille guitare cohérente.

## 5. Préchargement Opus dès l’ouverture

Le moteur audio ne reste plus en `preload = none`.

À l’ouverture d’une page chanson avec player :
- création des éléments audio ;
- `preload = auto` ;
- lancement immédiat de `_ensureTrackReady()` sans lecture ;
- les pistes activées sont prêtes en priorité ;
- les autres se préparent sans déclencher de son ;
- le cache HTTP existant sur les `.opus` est réutilisé.

**Précharger ≠ lire** : aucun autoplay n’est ajouté.

## Installation PowerShell

```powershell
cd H:\EZScore_v1

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R35_7_FULL_ANALYSIS_AUDIO_UX.zip" -C H:\EZScore_v1

python .\EZScore_v1_R35_7_FULL_ANALYSIS_AUDIO_UX\scripts\apply_r35_7.py H:\EZScore_v1

php bin\console cache:clear
php bin\console lint:container
php bin\console lint:twig templates

python -m py_compile .\analysis\chord_timeline_analysis.py
python -m py_compile .\worker_app\ezscore_analysis_worker.pyw

php .\EZScore_v1_R35_7_FULL_ANALYSIS_AUDIO_UX\tests\r35_7_contract.php H:\EZScore_v1

git diff --check
git status --short
```

Attendu :

```text
R35_7_APPLIED_OK
R35_7_CONTRACT_OK
```

## Tests manuels

1. **Remplacer l’audio** : modale EZScore, aucune popup Chrome.
2. **Supprimer une chanson** : même système de modale.
3. **Live** : analyser une fois filtre OFF puis filtre ON.
4. **Intro sans harmonie** : batterie seule pendant 1–4 mesures → mesures présentes mais vides avant le premier accord.
5. **Sans guitare** : morceau piano/pad/basse → grille guitare quand même générée.
6. **Player** : ouvrir ChordsLab/StemsLab, attendre quelques secondes sans cliquer Lecture, puis lancer → démarrage sensiblement plus immédiat.
7. Vérifier qu’aucun son ne démarre automatiquement.

Le script ne committe et ne pousse rien.
