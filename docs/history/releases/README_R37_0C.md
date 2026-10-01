# R37.0c — Correction du test de contrat

Le code applicatif et la route sont corrects.

Le test `r37_0b_contract.php` était faux : il utilisait une chaîne PHP entre guillemets doubles contenant `$jobs`, `$song` et `$user`, donc PHP interpolait ces variables au lieu de rechercher le texte littéral.

Ce correctif remplace uniquement le test.

```powershell
cd H:\EZScore_v1

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R37_0C_CONTRACT_FIX.zip" -C H:\EZScore_v1

php .\tests\r37_0c_contract.php H:\EZScore_v1
```

Attendu :

```text
R37_0C_CONTRACT_OK
```
