# SESSION R1.A/B HOTFIX 4

HOTFIX3 a dédupliqué la clé `validated` sans tenir compte de son niveau YAML :
la clé de message `event.validated` a été conservée, mais `event.status.validated`
a été supprimée.

HOTFIX4 rétablit uniquement :
- `event.status.validated: Validée` en français ;
- `event.status.validated: Validated` en anglais.

Le correctif est idempotent.
