# EZScore Analysis HQ R14.1 — BS-RoFormer API fix

Correctif ciblé sur **Analyse / STEM uniquement**.

R14 utilisait à tort `BSRoformerSession`, symbole inexistant dans
`bs-roformer-infer` 0.1.3.

R14.1 utilise les points d'entrée officiels :

- `MODEL_REGISTRY`
- `python -m bs_roformer.download`
- `python -m bs_roformer.inference`

Le package upstream traite les WAV du dossier d'entrée ; EZScore convertit donc
l'original en WAV via FFmpeg avant séparation.

Les modèles restent hors Git et doivent être placés sur H: via :

`BS_ROFORMER_MODELS_PATH=H:\EZScoreModels\bs-roformer`

Aucun fichier MIDI n'est modifié.
