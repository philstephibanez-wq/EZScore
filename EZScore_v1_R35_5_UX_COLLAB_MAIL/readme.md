# EZScore_v1 — R35.5 UX + COLLAB + MAIL

À appliquer après R35.4 + R35.4a.

- un seul onglet supérieur : **Tableau de bord** ;
- cartes workflow immédiatement sous le titre, sans grand vide ;
- lien global **Répertoire** à la place de Retour ;
- équipe éditoriale visible depuis le dashboard ;
- écran explicite d’ajout/retrait d’éditeurs délégués ;
- accès réel des éditeurs délégués à Édition, StemsLab et ChordsLab ;
- propriétaire affiché dans le répertoire et rendu immuable après création ;
- formulaire contact admin remis en page ;
- mail avec `From`, et erreur Mailer capturée sans HTTP 500.

## Installation

```powershell
cd H:\EZScore_v1

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R35_5_UX_COLLAB_MAIL.zip" -C H:\EZScore_v1
python .\EZScore_v1_R35_5_UX_COLLAB_MAIL\scripts\apply_r35_5.py H:\EZScore_v1

php bin\console cache:clear
php bin\console lint:container
php bin\console lint:twig templates
php bin\console debug:router | findstr /I "contact collaborator"

php .\EZScore_v1_R35_5_UX_COLLAB_MAIL\tests\r35_5_contract.php H:\EZScore_v1

git diff --check
git status --short
```

Attendu : `R35_5_APPLIED_OK` puis `R35_5_CONTRACT_OK`.

Le script ne committe et ne pousse rien.
