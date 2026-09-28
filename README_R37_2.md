# R37.2 — Prompteur LyricsLab synchronisé sur la métrique EZScore historique

Correction de R37.1 :
- métrique `metricX(t)` reprise de l'ancien player EZScore ;
- accords et syllabes dans la même géométrie temporelle ;
- un seul `translate3d()` pour les deux lignes ;
- aucune scrollbar horizontale ;
- aucun `scrollLeft`, `scrollIntoView`, `scrollTo`, scroll-snap ou recentrage automatique ;
- aucune barre verticale ;
- aucune transition CSS de position ;
- navigation verticale de la page conservée ;
- beat courant et syllabe courante uniquement allumés.

Ce ZIP remplace seulement :
- `public/assets/js/lyricslab-r37.js`
- `public/assets/css/lyricslab-r37.css`

Installation :

```powershell
cd H:\EZScore_v1

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R37_2_PROMPTER_METRIC_SYNC.zip" -C H:\EZScore_v1

php .\tests\r37_2_contract.php H:\EZScore_v1
php bin\console cache:clear

git diff --check
git status --short
```

Attendu : `R37_2_CONTRACT_OK`, puis `Ctrl+F5`.
