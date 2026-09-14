# EZScore R34 — Stabilisation blocs / paroles

Cette livraison repart de la version redevenue fonctionnelle.

## Corrections

- paroles validées rattachées à `block_id` via la clé `block:<id>` ;
- aucune migration SQLite ;
- un bloc vide validé reste instrumental ;
- récupération conservatrice des anciennes corrections `t0/t1` ;
- suppression du second `st.rerun()` lors d'une modification de `Fin` ;
- maintien de `Blocs > Édition` ;
- phonèmes visibles dans `Blocs > Édition`.

## Installation

Arrêter Streamlit, dézipper, puis :

```powershell
cd H:\EZScore
python .\EZScore_R34_STABLE_BLOCKS\apply_r34.py --root H:\EZScore
```

L'applicateur crée automatiquement un backup `_backup_R34_YYYYMMDD-HHMMSS`.

## Contrôle

```powershell
cd H:\EZScore
python -m compileall -q .
git status --porcelain=v1 -uall
python -m streamlit run .\EZScore.py --server.address 127.0.0.1 --server.port 8501 --server.headless true
```

Tester d'abord `http://127.0.0.1:8501`.

## La Bohème

Ne pas réanalyser avant le test.

1. Ouvrir La Bohème.
2. `Blocs > Édition`.
3. Vérifier l'intro et les paroles.
4. Modifier la fin d'un bloc et vérifier que la vue ne change pas.
5. Ouvrir `🔤 Phonèmes / beats`.
6. Quand l'état est correct, cliquer `Valider blocs + paroles`.

À partir de cette validation, le texte est persisté par `block_id`.
