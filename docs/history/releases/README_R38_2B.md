# R38.2B — premier mot + mail admin obligatoire

Deux corrections ciblées.

## 1. Premier mot de la timeline

Le bug venait de `SequenceMatcher` :
un bloc `replace` pouvait fournir un faux timestamp au début et placer `Je` sur le premier beat.

R38.2B :
- seuls les blocs **exactement reconnus et consécutifs** de 2 mots ou plus créent des ancres acoustiques ;
- les blocs `replace` ne créent plus jamais d'ancre ;
- si le premier mot (`Je`) appartient au premier bloc exact, il prend directement le timestamp Whisper réel ;
- si un ou plusieurs mots précèdent la première ancre fiable, ils sont placés juste avant celle-ci (190 ms/mot), **jamais répartis jusqu'à t=0** ;
- aucun mot ne doit donc apparaître pendant une longue intro instrumentale à cause de l'interpolation.

Après installation il faut relancer **Analyser les paroles** afin de recalculer les timestamps stockés.

## 2. Mail administrateur

Le destinataire du formulaire `Contact admin` est maintenant déterminé depuis la base :
- premier utilisateur, par ID de création, possédant `ROLE_ADMIN` ;
- c'est l'administrateur créé au premier démarrage ;
- `MAILER_FROM` reste uniquement l'adresse expéditrice ;
- `EZSCORE_ADMIN_CONTACT_EMAIL` n'est plus utilisé comme destinataire.

## Installation

```powershell
cd H:\EZScore_v1

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R38_2B_FIRST_WORD_ADMIN_MAIL_FIX.zip" -C H:\EZScore_v1

python .\scripts\install_r38_2b.py H:\EZScore_v1

python -m py_compile .\analysis\lyrics_timeline_analysis.py

php -l .\src\Controller\ContactController.php
php -l .\src\Domain\User\UserRepository.php

php .\tests\r38_2b_contract.php H:\EZScore_v1

php bin\console cache:clear

git diff --check
git status --short
```

Attendu :

```text
R38_2B_INSTALL_OK
No syntax errors detected in .\src\Controller\ContactController.php
No syntax errors detected in .\src\Domain\User\UserRepository.php
R38_2B_CONTRACT_OK
```

Ensuite :
1. `Ctrl+F5`
2. relancer **Analyser les paroles**
3. vérifier l'intro
4. envoyer un message test via `Contact admin`
