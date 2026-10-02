# EZScore ROLE_DISPLAY R1

Ajoute le rôle applicatif `ROLE_DISPLAY`, libellé **Passif**.

Ce rôle représente un terminal de restitution (rétroprojecteur, TV, écran), pas un participant humain.

## Installation

```powershell
cd H:\EZScore
powershell -ExecutionPolicy Bypass -File .\scripts\install_role_display_r1.ps1 ; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; php bin\console cache:clear ; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; php -l .\src\Domain\User\User.php ; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; php -l .\src\Service\UserManager.php ; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; php -l .\src\Controller\AdminUserController.php ; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; php .\tests\role_display_r1_contract.php
```

Attendu : `ROLE_DISPLAY_R1_CONTRACT_OK`

Puis dans Administration > Utilisateurs, passer le compte du rétroprojecteur en rôle **Passif**.
