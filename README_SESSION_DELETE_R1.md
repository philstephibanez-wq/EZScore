# EZScore Session Delete R1

Correctif ciblé du bouton **Supprimer la session**.

Le `confirm()` natif du navigateur est retiré et remplacé par un `<dialog>` EZScore :
- Annuler ferme la boîte ;
- Supprimer définitivement soumet le POST existant ;
- CSRF et route serveur restent inchangés ;
- aucun changement du domaine Session/LiveRun.

## Installation

Extraire à la racine de `H:\EZScore`, puis :

```powershell
cd H:\EZScore
powershell -ExecutionPolicy Bypass -File .\scripts\install_session_delete_r1.ps1 ; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; php bin\console cache:clear ; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; php .\tests\session_delete_r1_contract.php
```

Attendu :

```text
SESSION_DELETE_R1_INSTALL_OK
SESSION_DELETE_R1_CONTRACT_OK
```

Ensuite test navigateur : ouvrir une Session, cliquer Supprimer, vérifier Annuler puis refaire et confirmer la suppression.
