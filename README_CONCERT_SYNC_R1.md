# EZScore — CONCERT SYNC R1

Base GitHub utilisée :

```text
485af5e0aed1acdfc527821feccedda680f5738d
EZScore_CAST_R1_FOUNDATION
```

Ce livrable repart du GitHub actuel et ne réutilise aucun fichier du POC Projector abandonné.

## But

Valider le premier axe du contrat concert :

```text
CLIENT MASTER
    │
    │ Session Sync
    ▼
CLIENT FOLLOWER
```

R1 ne fait pas encore le mirroring vers projecteur/TV, WebRTC caméra/micro, ni le branchement sur le vrai AudioEngine. Il valide d’abord l’autorité unique du Master et le suivi d’un second client.

## Implémenté

- session éphémère sous `var/concert_sessions` ;
- TTL 4 h prolongé par activité ;
- ID session, clé Master, invitation et clés Followers aléatoires ;
- secrets stockés sous forme SHA-256 ;
- verrouillage `flock` ;
- un seul Master autorisé à modifier le transport ;
- Follower lecture seule ;
- heartbeat ;
- état `song_id`, `song_title`, `playing`, `position_ms`, `tempo`, `updated_at_ms`, `revision` ;
- interpolation locale de position côté Follower ;
- entrée `Session` dans le header authentifié ;
- aucun changement AudioEngine, timeline, ChordsLab, LyricsLab ou Python.

## Installation

```powershell
cd H:\EZScore
tar -xf "$env:USERPROFILE\Downloads\EZScore_CONCERT_SYNC_R1.zip" -C H:\EZScore
```

Puis :

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install_concert_sync_r1.ps1
```

Attendu :

```text
CONCERT_SYNC_R1_INSTALL_OK
```

## Premier test — ne pas enchaîner

```powershell
php .\tests\concert_sync_r1_contract.php
```

Attendu :

```text
CONCERT_SYNC_R1_CONTRACT_OK
```

Après validation seulement, on vérifiera les routes Symfony puis le test réel Master → second navigateur/appareil.
