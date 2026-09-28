<?php
$root = $argv[1] ?? 'H:\\EZScore_v1';
$file = $root . '/worker_app/lyrics_worker_r37.py';
$src = file_get_contents($file);
$required = [
    'def _discover_lyrics_python(engine, force: bool = False) -> str:',
    'R38.13a: cache validated Lyrics Python',
    'getattr(engine, "_lyrics_python_cache", None)',
    'timeout=60,check=False',
    'engine._lyrics_python_cache = {',
    'Python Lyrics (cache):',
    'engine._lyrics_python_cache = None',
    '_discover_lyrics_python(engine, force=True)',
];
foreach ($required as $needle) {
    if (strpos($src, $needle) === false) {
        fwrite(STDERR, "Missing invariant: $needle\n");
        exit(1);
    }
}
if (strpos($src, 'timeout=20,check=False') !== false) {
    fwrite(STDERR, "Old 20s Lyrics probe timeout still present\n");
    exit(1);
}
echo "R38_13A_WORKER_CACHE_CONTRACT_OK\n";
