# EZScore — R12 vitesse sans changement de tonalité

Le contrôle de vitesse n'utilise plus l'effet "bande magnétique" de
`AudioBufferSourceNode.playbackRate`.

## Principe

EZScore crée et met en cache des pré-écoutes à :

- 0.75x
- 0.85x
- 1.00x
- 1.10x
- 1.25x

Les variantes autres que 1.00x sont produites par FFmpeg `atempo`, algorithme
WSOLA de changement de tempo. La hauteur/tonalité n'est donc pas transposée
avec la vitesse.

Les fichiers audio/STEM sources et la timeline d'analyse restent immuables.
Seuls des MP3 de pré-écoute sont ajoutés au cache du player.

Le conducteur conserve la timeline originale. Pour une vitesse `r` :

`temps musical = position + temps mural écoulé * r`

et le démarrage dans la pré-écoute étirée utilise :

`offset pré-écoute = temps musical / r`

## Lisibilité du conducteur

Le conducteur est rendu volontairement 350 ms derrière l'horloge audio :

`temps affiché = temps audio - 0.35 s`

C'est seulement un retard d'affichage ; aucun timestamp n'est réécrit.

## Installation depuis Downloads

```powershell
cd H:\EZScore

Expand-Archive `
  -Path "$env:USERPROFILE\Downloads\EZScore_R12_pitch_preserved.zip" `
  -DestinationPath . `
  -Force

python -m py_compile .\ezscore\player\karaoke_stem_webaudio_r12.py
python -m py_compile .\ezscore\ui\__init__.py

git diff --check
git status
```

Puis redémarrer Streamlit.

Le premier chargement peut être plus long : les variantes manquantes sont
générées une fois, puis réutilisées.

## Contrôles avant push

- comparer 1.00x et 0.75x : même tonalité ;
- vérifier 0.85x / 1.10x / 1.25x ;
- vérifier Original puis Mix STEM ;
- vérifier EQ, volumes et Master ;
- vérifier accords / Chant / Chœurs ;
- confirmer que le retard visuel de 350 ms améliore la lecture.

Ne pas pousser avant validation auditive.
