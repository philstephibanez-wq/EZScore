# EZScore_v1 R38.6 — paroles, tempo, diagramme, audit mail admin

Ne pas pousser R38.5.

## Corrections

### Paroles
R38.5 pouvait trouver une première phrase correcte puis la réécrire pendant un alignement global sur une répétition beaucoup plus tardive.
R38.6 supprime ce passage global : première phrase chronologique immuable, puis recherche locale uniquement vers l'avant (fenêtre bornée). Aucun titre, artiste, numéro de mesure ou offset spécifique à une chanson.

### Tempo
LyricsLab affiche le tempo à partir de la timeline de beats partagée avec ChordsLab. Il apparaît dans la carte morceau et près du profil.

### Diagramme
La préférence `Diagramme d'accord` est stockée par ID stable du morceau et non plus par URL.

### Mail admin
Admin attendu : `xpertdev@hotmail.com`.
Le dépôt public actuel ne montre pas de mailer d'erreur explicite. On ne redirige donc pas arbitrairement tous les mails (inscriptions/invitations/publications doivent rester destinés aux utilisateurs). Le livrable conserve les commandes R38.5 si déjà présentes et ajoute un audit local qui cherche le vrai chemin d'envoi d'erreur.

## Installation

```powershell
cd H:\EZScore_v1

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R38_6_TIMELINE_TEMPO_DIAGRAM_ADMIN_MAIL.zip" -C H:\EZScore_v1

python .\scripts\install_r38_6.py H:\EZScore_v1
python -m py_compile .\analysis\lyrics_timeline_analysis.py
python -m py_compile .\worker_app\lyrics_worker_r37.py
php .\tests\r38_6_contract.php H:\EZScore_v1
php bin\console cache:clear

php bin\console ezscore:admin-mail-sync
php bin\console ezscore:admin-mail-audit
php .\scripts\audit_admin_error_mail_r38_6.php H:\EZScore_v1 xpertdev@hotmail.com

git diff --check
git status --short
```

Ensuite redémarrer le worker permanent et relancer `Analyser les paroles`.

## Validation avant push

1. `Tempo = ... BPM` visible dans LyricsLab.
2. Décocher `Diagramme d'accord`, recharger : il reste décoché.
3. Le premier mot reste ancré sur la première phrase chantée et ne saute plus sur une répétition des dizaines de mesures plus loin.
4. Vérifier le destinataire réel du mail d'erreur. Si Gmail reçoit encore le mail, conserver la sortie de l'audit runtime : elle permettra de patcher l'émetteur réel.
