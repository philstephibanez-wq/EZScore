# EZScore_LEAD_ONLY_LYRICS_R1

Base GitHub vérifiée avant livraison :

```text
master = cfd9a1cc2f10eb3c313e32366dc127ff4bf83fdb
```

## Décision temporaire

Stabiliser d'abord le **Chant principal**.

Les Chœurs restent séparés en audio mais leur couche texte est retirée du
chemin actif.

## Actif

```text
original audio
lead_vocals.wav
backing_vocals.wav      (audio uniquement)
drums / bass / other
accords
paroles Chant
timeline canonique
```

## Désactivé

```text
Whisper Chœurs
choir_analysis
choir_timeline
whisper_vocals supplement
whisper_backing
ligne Chœurs texte du conducteur
fallback R12c vers anciennes paroles vocales
```

Les stems WAV ne sont jamais supprimés.

## Nettoyage automatique

Les anciens artefacts texte Chœurs sont supprimés lorsqu'on ouvre Analyse :

```text
whisper_vocals_small.json
whisper_backing_small.json
choir_words_from_vocals.json
choir_analysis.json
```

## Application

```powershell
cd H:\EZScore

tar -xf "$env:USERPROFILE\Downloads\EZScore_LEAD_ONLY_LYRICS_R1.zip" -C H:\EZScore

.\.venv-py313\Scripts\python.exe -m py_compile `
  .\ezscore\integration\choir_pipeline.py `
  .\scripts\test_lead_only_lyrics.py

.\.venv-py313\Scripts\python.exe .\scripts\test_lead_only_lyrics.py
```

Attendu :

```text
LEAD-ONLY LYRICS CONTRACT OK
lead lyrics: ENABLED
choir lyrics/transcription: DISABLED
lead/backing audio stems: PRESERVED
canonical timeline/cache guard: PRESERVED
```

Puis redémarrage complet de Streamlit.
