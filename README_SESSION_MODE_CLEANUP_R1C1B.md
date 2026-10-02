# EZScore SESSION MODE CLEANUP R1.C1B

Hotfix de récupération après échec de R1.C1A.

R1.C1A a échoué avant migration à cause de variables PHP interpolées dans des expressions régulières du script d'installation. Ce lot n'utilise plus ces regex fragiles.

Il est idempotent et sait repartir d'un dépôt partiellement modifié par R1.C1A.

Objectif :
- supprimer `EventMode` de la Session ;
- supprimer le champ/filtres/libellés `Mode` ;
- supprimer `events.mode` par migration ;
- faire pointer le bouton topbar `Session` vers la vraie page Sessions ;
- conserver le LiveRun R1.C1.
