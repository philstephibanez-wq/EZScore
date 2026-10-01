# Problèmes connus / à investiguer

## Remplacement de `progress.json` sous Windows

Erreur observée :

```text
[WinError 5] Accès refusé:
'H:\EZScore_v1\var\storage\stems\song-...\progress.json.tmp'
->
'H:\EZScore_v1\var\storage\stems\song-...\progress.json'
```

Statut : **à investiguer séparément**.

Ne pas conclure automatiquement à une limite de quota. Une limite de file de jobs a également été évoquée ; la cause exacte devra être reproduite et journalisée avant correction.

Le nettoyage du dépôt ne modifie pas ce mécanisme.

## Quotas / file de jobs

Le réglage d'administration des quotas est reporté à une étape dédiée. Le message d'erreur utilisateur devra être explicite lorsque la cause sera identifiée.
