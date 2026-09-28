<?php
declare(strict_types=1);
$root = $argv[1] ?? dirname(__DIR__);
$must = [
  'analysis/lyrics_timeline_analysis.py' => ['detect_first_vocal_onset', 'vocal_stem_acoustic_onset', '--vocal-audio'],
  'worker_app/lyrics_worker_r37.py' => ['--vocal-audio', 'Détection onset vocal'],
  'templates/song/components/_lab_song_card.html.twig' => ['data-lab-song-card', 'data-lab-tempo', 'Tempo = —'],
  'templates/song/chordslab.html.twig' => ['_lab_song_card.html.twig', 'lab-song-card.js'],
  'templates/song/lyricslab.html.twig' => ['_lab_song_card.html.twig', 'lab-song-card.js', 'data-song-id'],
  'public/assets/js/lyricslab-r37.js' => ['root.dataset.songId'],
];
foreach ($must as $rel => $tokens) {
    $path = rtrim($root, '/\\').DIRECTORY_SEPARATOR.str_replace('/', DIRECTORY_SEPARATOR, $rel);
    if (!is_file($path)) { fwrite(STDERR, "MISSING $rel\n"); exit(2); }
    $text = file_get_contents($path);
    foreach ($tokens as $token) {
        if (strpos($text, $token) === false) { fwrite(STDERR, "MISSING TOKEN $token IN $rel\n"); exit(3); }
    }
}
echo "R38_7_CONTRACT_OK\n";
