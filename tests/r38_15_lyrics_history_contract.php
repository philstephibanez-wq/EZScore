<?php
declare(strict_types=1);

$root = $argv[1] ?? 'H:\\EZScore_v1';

$required = [
    'src/Domain/Song/LyricsSourceRevision.php',
    'src/Domain/Song/LyricsSourceRevisionRepository.php',
    'src/Service/LyricsSourceHistoryService.php',
    'src/Controller/LyricsHistoryController.php',
    'migrations/Version20260929090000.php',
    'public/assets/js/lyrics-history-r38-15.js',
    'public/assets/css/lyrics-history-r38-15.css',
];

foreach ($required as $relative) {
    if (!is_file($root.'/'.$relative)) {
        fwrite(STDERR, "Missing file: $relative\n");
        exit(1);
    }
}

$repository = file_get_contents($root.'/src/Domain/Song/LyricsSourceRevisionRepository.php');
if (strpos($repository, 'setMaxResults(1)') === false) {
    fwrite(STDERR, "Latest revision query contract missing\n");
    exit(1);
}
if (strpos($repository, "findForSong") === false || strpos($repository, "setMaxResults(10)") !== false) {
    fwrite(STDERR, "History must be unlimited\n");
    exit(1);
}

$service = file_get_contents($root.'/src/Service/LyricsSourceHistoryService.php');
foreach (['lyrics_ovh', 'whisper', 'restore', 'archiveCurrentIfChanged', 'current_revision'] as $needle) {
    if (strpos($service, $needle) === false) {
        fwrite(STDERR, "Missing history service contract: $needle\n");
        exit(1);
    }
}

$controller = file_get_contents($root.'/src/Controller/LyricsHistoryController.php');
foreach ([
    "song_lyrics_history_",
    "app_song_lyrics_history_restore",
    "app_song_lyrics_history_delete",
    "Response::HTTP_CONFLICT",
] as $needle) {
    if (strpos($controller, $needle) === false) {
        fwrite(STDERR, "Missing history controller contract: $needle\n");
        exit(1);
    }
}

$songLab = file_get_contents($root.'/src/Controller/SongLabController.php');
if (strpos($songLab, 'Sauvegarde automatique avant extraction Whisper') === false) {
    fwrite(STDERR, "Whisper pre-replacement snapshot missing\n");
    exit(1);
}

$template = file_get_contents($root.'/templates/song/lyricslab.html.twig');
foreach (['data-lyrics-history', 'Commentaire personnel', 'Lyrics.ovh', 'lyrics-history-r38-15.js'] as $needle) {
    if (strpos($template, $needle) === false) {
        fwrite(STDERR, "Missing LyricsLab UI contract: $needle\n");
        exit(1);
    }
}

$js = file_get_contents($root.'/public/assets/js/lyrics-history-r38-15.js');
if (strpos($js, "addEventListener('input'") !== false) {
    fwrite(STDERR, "History JS must not create versions per keystroke\n");
    exit(1);
}
if (strpos($js, 'Jeter définitivement cette sauvegarde') === false) {
    fwrite(STDERR, "Trash confirmation missing\n");
    exit(1);
}

/* Harmonic ribbon remains outside this patch. */
$lyricsLabJs = file_get_contents($root.'/public/assets/js/lyricslab-r37.js');
if (strpos($lyricsLabJs, 'R38.13b: time-signature agnostic continuous projection.') === false ||
    strpos($lyricsLabJs, 'R38.13c: restore chord lane runtime declaration') === false) {
    fwrite(STDERR, "R38.13 harmonic ribbon invariants missing\n");
    exit(1);
}

echo "R38_15_LYRICS_HISTORY_CONTRACT_OK\n";
