# EZScore R29 FIX8 — Analyse + sauts de ligne paroles

Correctif cumulatif basé sur FIX7.

## 1. Vue Analyse

Régression corrigée :

```text
ValueError: too many values to unpack (expected 2)
```

`create_harmonic_timeline()` retourne une seule figure Plotly. Le code appelant ne tente plus de déballer un second retour inutile.

## 2. Sauts de ligne des paroles

Les retours à la ligne saisis dans `Blocs > Édition` sont de nouveau récupérés.

Cause :
- l'ancienne convention enregistrait la fin du bloc à `fin` ;
- FIX6 a normalisé la fin à `fin + 0,001 s` ;
- la clé persistée ne correspondait donc plus exactement, même si le bloc était le même.

FIX8 conserve l'identification exacte en priorité, puis accepte uniquement un ancien enregistrement dont les bornes diffèrent de quelques millisecondes. Le texte corrigé et ses retours à la ligne sont alors réutilisés.

Cette résolution est appliquée à :
- Blocs > Édition ;
- Paroles + accords ;
- impression ;
- timeline canonique utilisée par les players.

## 3. Ergonomie

La sidebar compacte FIX7 est conservée :
- profil compact dans Chanson / Import ;
- commandes globales secondaires repliées ;
- Vue / Édition / Capo accessibles sans parcourir toute la sidebar.

## Fichiers du livrable

- `EZScore.py`
- `readme.md`
- `ezscore/persistence.py`
- `ezscore/ui/app_shell.py`
- `ezscore/player/web_player.py`
- `ezscore/backoffice/player.py`
