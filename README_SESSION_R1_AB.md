# EZScore SESSION R1.A/B

Premier livrable conforme aux issues #2 et #4.

## Ce lot
- création en Brouillon ;
- Groupe obligatoire + Playlist obligatoire ;
- brouillon privé ;
- aucune invitation lors de l'affectation du Groupe ;
- validation explicite par le propriétaire ;
- participants du Groupe + e-mails à la validation ;
- `validated_at` ;
- date passée non caduque par défaut.

LiveRun et notification globale viennent dans R1.C/R1.D.

## Installation enchaînée

Extraire le ZIP dans `H:\EZScore_v1`, puis depuis `H:\EZScore_v1` :

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install_session_r1_ab.ps1 ; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; php bin\console cache:clear ; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; php bin\console doctrine:migrations:migrate --no-interaction ; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; php -l .\src\Domain\Event\Event.php ; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; php -l .\src\Controller\EventController.php ; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; php -l .\src\Security\Acl\EventVoter.php ; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; php .\tests\session_r1_ab_contract.php
```

Attendu :
`SESSION_R1_AB_CONTRACT_OK`

## Git
NE PAS PUSHER avant validation navigateur.

Après le contrat :
1. création sans Groupe/Playlist refusée ;
2. création valide => Brouillon ;
3. autre compte du Groupe ne voit pas le brouillon ;
4. aucun mail avant validation ;
5. `Valider la session` => participants + invitations ;
6. autre compte voit la Session après validation.

Après ces six points : décision PUSH / JETTE.
