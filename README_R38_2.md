# R38.2 — alignement intro + profils + mail admin

Corrections :
- le premier mot non ancré n'est plus extrapolé jusqu'à `t=0` à travers une longue intro ;
- LyricsLab permet maintenant de choisir `Débutant / Intermédiaire / Expert` ;
- le changement de profil recharge immédiatement les événements d'accords existants de ChordsLab ;
- les emails `Contact admin` ne ciblent plus `EZSCORE_ADMIN_CONTACT_EMAIL` ;
- leur destinataire est désormais le premier utilisateur ayant `ROLE_ADMIN`, c.-à-d. l'admin créé au premier démarrage ;
- `MAILER_FROM` reste uniquement l'adresse expéditrice.

Le ruban R38.1A est conservé :
- zone de lecture à gauche ;
- accords visibles avant/après ;
- notation `Em - - -` ;
- diagramme optionnel ;
- paroles lisibles sans chevauchement ;
- navigation sections.

## Installation

```powershell
cd H:\EZScore_v1

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R38_2_ALIGNMENT_PROFILE_ADMIN_MAIL.zip" -C H:\EZScore_v1

python .\scripts\install_r38_2.py H:\EZScore_v1

python -m py_compile .\analysis\lyrics_timeline_analysis.py

php -l .\src\Controller\ContactController.php
php -l .\src\Domain\User\UserRepository.php

php .\tests\r38_2_contract.php H:\EZScore_v1

php bin\console cache:clear

git diff --check
git status --short
```

Attendu :
`R38_2_INSTALL_OK`
`R38_2_CONTRACT_OK`

Puis :
1. `Ctrl+F5`
2. relancer **Analyser les paroles** pour recalculer les timestamps du début.
