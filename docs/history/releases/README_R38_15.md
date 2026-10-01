# EZScore_v1 — R38.15 — Historique illimité des blocs de paroles

## Objectif

Versionner le **bloc complet** des paroles, sans créer de version à chaque mot ou à chaque frappe.

Usage visé :

1. conserver une version correcte ;
2. tester une autre source (ex. Lyrics.ovh, Whisper, saisie manuelle) ;
3. restaurer instantanément une version précédente si la nouvelle source est moins bonne ;
4. ajouter un commentaire personnel ;
5. jeter manuellement une ancienne sauvegarde.

## Comportement

- historique **illimité** ;
- sauvegarde explicite du bloc complet ;
- provenance structurée :
  - Manuel
  - Lyrics.ovh
  - Whisper
  - Autre
  - Restauration
  - Version initiale
- commentaire libre utilisateur ;
- date/heure ;
- auteur ;
- restauration non destructive ;
- bouton poubelle avec confirmation ;
- la version actuellement utilisée ne peut pas être jetée ;
- avant **Extraire les paroles**, le texte courant est automatiquement archivé s'il ne l'est pas déjà ;
- la migration conserve automatiquement le texte existant de tous les morceaux comme première sauvegarde.

L'autosave existant du textarea reste disponible pour le confort d'édition, mais **il ne crée aucune révision**.

## Installation

```powershell
cd H:\EZScore_v1

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R38_15_LYRICS_HISTORY.zip" -C H:\EZScore_v1

python .\scripts\install_r38_15_lyrics_history.py H:\EZScore_v1

php .\tests\r38_15_lyrics_history_contract.php H:\EZScore_v1

php -l .\src\Domain\Song\LyricsSourceRevision.php
php -l .\src\Domain\Song\LyricsSourceRevisionRepository.php
php -l .\src\Service\LyricsSourceHistoryService.php
php -l .\src\Controller\LyricsHistoryController.php
php -l .\migrations\Version20260929090000.php

php bin\console cache:clear
php bin\console doctrine:migrations:migrate --no-interaction
php bin\console cache:warmup
```

## Contrôle

```powershell
php bin\console debug:router | Select-String "lyrics_history"
php bin\console doctrine:migrations:status
git status --short
```

Puis `Ctrl+F5` dans LyricsLab.

## Test fonctionnel recommandé

1. ouvrir un morceau avec des paroles existantes ;
2. déplier **Historique des paroles** ;
3. modifier le texte ;
4. choisir `Lyrics.ovh`, saisir par exemple `paroles cherchées avec OVH`, puis **Sauvegarder cette version** ;
5. modifier de nouveau le texte ;
6. restaurer la version Lyrics.ovh ;
7. vérifier que le bloc complet revient ;
8. jeter une ancienne sauvegarde ;
9. vérifier que la sauvegarde marquée **Actuelle** ne peut pas être jetée ;
10. lancer **Extraire les paroles** et vérifier que la version présente juste avant Whisper reste dans l'historique.

## Portée

R38.15 ne modifie pas la projection, le défilement ou le calage de la timeline harmonique R38.13c.
