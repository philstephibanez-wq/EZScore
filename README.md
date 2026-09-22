# EZScore_STEM_SHARED_CONDUCTOR_R2_FULL

Livraison complète autonome. Elle remplace R1 / R1b / R1c / TESTFIX.

Base GitHub auditée :

```text
8e6fb686445132189df0afcd860f4803ef221cc6
```

## Cible

```text
                         [Diagramme accord courant]

┌─────────────────────────────────────────────────────┐
│ Structure │ Intro   Couplet 1   Refrain   ...       │
│ Accords   │ Em---   G---        D-Em-     ...       │
│ Chant     │ même moteur visuel que 2 · Paroles      │
└─────────────────────────────────────────────────────┘
```

Le left panel Analyse conserve uniquement la zone métier utile :

```text
Mode
Time signature
Capodastre
```

## Cette livraison est autonome

Elle ne dépend d'aucun marqueur R1/R1b/R1c local.

Elle contient le fichier métier COMPLET :

```text
files/ezscore/player/stem_analysis_conductor.py
```

SHA256 attendu :

```text
e7cee0bc83b2e48bdb380587cf384bde2272136261b2e7afefe4b60d5b214462
```

L'installateur :
1. vérifie le Git HEAD ;
2. construit/valide l'état final de `EZScore.py` de manière idempotente ;
3. valide les deux Python complets ;
4. sauvegarde les fichiers courants ;
5. copie le fichier STEM complet ;
6. vérifie immédiatement son SHA256 après copie.

## Application

Arrêter Streamlit puis :

```powershell
cd H:\EZScore

tar -xf "$env:USERPROFILE\Downloads\EZScore_STEM_SHARED_CONDUCTOR_R2_FULL.zip" -C H:\EZScore

$env:PYTHONPATH = "H:\EZScore"

.\.venv-py313\Scripts\python.exe .\scripts\apply_stem_shared_conductor_r2_full.py

.\.venv-py313\Scripts\python.exe .\scripts\test_stem_shared_conductor_r2_full_contract.py
```

Attendu :

```text
STEM SHARED CONDUCTOR R2 FULL CONTRACT OK
exact installed STEM SHA256: OK
real module import / runtime transforms: OK
same Paroles CSS/layout engine: YES
Structure / Accords / Chant: YES
1 MMS_FA word = 1 DOM node: YES
mixer before conductor: YES
transport under conductor: YES
Time signature in left panel: YES
Capodastre in left panel: YES
```

Puis :

```powershell
.\.venv-py313\Scripts\python.exe -m streamlit run EZScore.py `
  --server.address 127.0.0.1 `
  --server.port 8501 `
  --server.headless true
```

## Contrôle visuel

Dans `Analyse > 1 · STEM` :
- diagramme de l'accord courant au-dessus ;
- ligne Structure = blocs manuels ;
- ligne Accords = accords ajustés par capo et regroupés par Time signature ;
- ligne Chant = même moteur visuel que `2 · Paroles` ;
- mixer au-dessus ;
- transport sous le conducteur.

Aucun commit ni push.
