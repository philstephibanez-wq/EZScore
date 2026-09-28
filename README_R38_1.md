# R38.1
- accord courant sous une zone fixe placée à 30% de la largeur ;
- accords précédents/suivants visibles ;
- paroles précédentes/suivantes visibles ;
- tailles conservées (30px / 29px) ;
- aucun chevauchement des mots ;
- notation beat normalisée : `Em - - -` ;
- diagramme guitare optionnel rétabli au-dessus de la zone fixe ;
- navigation sections cliquable sous le titre.

Installation:
```powershell
cd H:\EZScore_v1
tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R38_1_FIXED_ZONE_RIBBONS.zip" -C H:\EZScore_v1
python .\scripts\install_r38_1.py H:\EZScore_v1
php .\tests\r38_1_contract.php H:\EZScore_v1
php bin\console cache:clear
git diff --check
git status --short
```
Attendu: `R38_1_INSTALL_OK` puis `R38_1_CONTRACT_OK`.
Puis Ctrl+F5.
