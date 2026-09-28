<?php
declare(strict_types=1);
$root = $argv[1] ?? 'H:\\EZScore_v1';

$template = @file_get_contents($root.'/templates/song/lyricslab.html.twig');
$js = @file_get_contents($root.'/public/assets/js/lyrics-history-r38-15.js');

if ($template === false || $js === false) {
    fwrite(STDERR, "Missing R38.15 assets\n");
    exit(1);
}

if (strpos($template, '/assets/js/lyrics-history-r38-15.js?v=20260929r38_15d') === false) {
    fwrite(STDERR, "JS cache-bust URL missing\n");
    exit(1);
}
if (strpos($template, '/assets/css/lyrics-history-r38-15.css?v=20260929r38_15d') === false) {
    fwrite(STDERR, "CSS cache-bust URL missing\n");
    exit(1);
}
foreach (['confirm(', 'alert(', 'prompt('] as $forbidden) {
    if (strpos($js, $forbidden) !== false) {
        fwrite(STDERR, "Native browser dialog remains: $forbidden\n");
        exit(1);
    }
}
if (strpos($js, 'function ezConfirm(') === false) {
    fwrite(STDERR, "Custom modal missing\n");
    exit(1);
}

echo "R38_15D_FORCE_ASSET_REFRESH_CONTRACT_OK\n";
