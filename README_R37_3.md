# R37.3 — Cadre fixe + mots sans chevauchement

Objectif validé :
- la bande d'accords défile sous un cadre fixe ;
- pas de barre verticale ;
- les paroles restent sur une seule ligne ;
- mots entiers (pas de pseudo-syllabification) ;
- aucun chevauchement de mots ;
- pas de scrollbar horizontale ;
- pas de déplacement automatique de la page ;
- accords + paroles partagent strictement le même moteur de déplacement.

## Point technique important

Pour éviter le chevauchement sans désynchroniser accords et paroles, R37.3 ne décale pas seulement les mots.

Il construit une **métrique visuelle déformée monotone** :
1. la métrique brute vient des vrais beats (`metricXRaw`);
2. les largeurs réelles des mots sont mesurées dans le navigateur ;
3. si deux mots se touchent, la timeline est dilatée à cet endroit ;
4. cette même dilatation est appliquée aux accords ;
5. le `transform` courant utilise cette même métrique.

Il n'existe donc toujours qu'une seule timeline visuelle.

## Installation

```powershell
cd H:\EZScore_v1

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R37_3_FIXED_FRAME_NO_OVERLAP.zip" -C H:\EZScore_v1

php .\tests\r37_3_contract.php H:\EZScore_v1

php bin\console cache:clear

git diff --check
git status --short
```

Attendu :

```text
R37_3_CONTRACT_OK
```

Puis `Ctrl+F5`.

Le ZIP ne remplace que :
- `public/assets/js/lyricslab-r37.js`
- `public/assets/css/lyricslab-r37.css`

ChordsLab, Worker, analyse et base ne sont pas touchés.
