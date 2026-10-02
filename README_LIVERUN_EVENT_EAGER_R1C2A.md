# EZScore LIVERUN EVENT EAGER R1.C2A

Hotfix ciblé pour l'erreur :

`Cannot generate lazy ghost: class "App\Domain\Event\Event" is final.`

Cause :
- `LiveRun -> Event` est une association Doctrine lazy par défaut ;
- `Event` est `final` ;
- Doctrine tente de créer un proxy/lazy ghost impossible pour une classe finale.

Correction :
- `LiveRun -> Event` passe en `fetch: 'EAGER'`.

Aucune migration SQL nécessaire.
Aucune modification du contrat Session/LiveRun.
