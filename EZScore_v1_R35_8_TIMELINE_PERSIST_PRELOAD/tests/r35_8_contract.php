<?php
declare(strict_types=1);
$root=$argv[1]??dirname(__DIR__,2);
$checks=[
'src/Domain/Song/Song.php'=>['chordNoiseFilterEnabled','isChordNoiseFilterEnabled','setChordNoiseFilterEnabled'],
'src/Controller/SongLabController.php'=>['app_song_chordslab_noise_filter','setChordNoiseFilterEnabled','has_chord_overrides'],
'templates/song/chordslab.html.twig'=>['data-noise-filter','song.chordNoiseFilterEnabled','has_chord_overrides','20260928r35_8'],
'templates/stems/index.html.twig'=>['20260928r35_8'],
'public/assets/js/stems-mixer.js'=>['engine.warmUp({enabledFirst: true})'],
'public/assets/js/audio/ezscore-audio-engine.js'=>["media.preload = 'auto'"],
'public/assets/js/chordslab.js'=>['data-noise-filter','text=\'.\''],
'analysis/chord_timeline_analysis.py'=>['MP3 t=0','top3_ratio','has_harmony','r35.8-absolute-timeline'],
'migrations/Version20260928013000.php'=>['chord_noise_filter_enabled'],
];
foreach($checks as $rel=>$tokens){$p=$root.DIRECTORY_SEPARATOR.str_replace('/',DIRECTORY_SEPARATOR,$rel);if(!is_file($p))throw new RuntimeException("Fichier absent: $rel");$s=(string)file_get_contents($p);foreach($tokens as $token)if(!str_contains($s,$token))throw new RuntimeException("$rel token absent: $token");}
echo "R35_8_CONTRACT_OK\n";
