# R37.1 — Prompteur karaoké continu accords + syllabes

Objectif :
- une seule ligne d'accords ;
- une seule ligne de paroles ;
- aucun retour à la ligne ;
- aucune barre verticale fixe ;
- accord courant allumé ;
- mot courant légèrement renforcé ;
- syllabe courante fortement allumée ;
- accords et paroles déplacés par **un seul transform temporel** ;
- aucun `scrollIntoView()` ;
- la vitesse suit directement l'horloge audio, donc les changements de vitesse restent synchronisés.

Important : si l'analyse fournit plus tard de vraies syllabes acoustiques (`event.syllables` avec `start_ms/end_ms`), elles sont utilisées directement. En attendant, R37.1 découpe visuellement le mot et répartit ses syllabes à l'intérieur de son intervalle temporel existant.

Installation :

```powershell
cd H:\EZScore_v1

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R37_1_KARAOKE_SYLLABLE_PROMPTER.zip" -C H:\EZScore_v1

php .\tests\r37_1_contract.php H:\EZScore_v1

php bin\console cache:clear

git diff --check
git status --short
```

Attendu :

```text
R37_1_CONTRACT_OK
```

Puis `Ctrl+F5`.

Ce livrable ne touche ni ChordsLab, ni le Worker, ni les contrôleurs d'analyse.
