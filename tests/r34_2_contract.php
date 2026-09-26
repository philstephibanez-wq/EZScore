<?php
declare(strict_types=1);

$root = dirname(__DIR__);

function findChordJs(string $root): ?string {
    $base = $root . DIRECTORY_SEPARATOR . 'public' . DIRECTORY_SEPARATOR . 'assets' . DIRECTORY_SEPARATOR . 'js';
    if (!is_dir($base)) {
        return null;
    }
    $it = new RecursiveIteratorIterator(new RecursiveDirectoryIterator($base, FilesystemIterator::SKIP_DOTS));
    foreach ($it as $file) {
        if (!$file->isFile() || strtolower($file->getExtension()) !== 'js') {
            continue;
        }
        $text = file_get_contents($file->getPathname());
        if (str_contains($text, 'data-chordslab') && str_contains($text, 'formatChordHtml(')) {
            return $file->getPathname();
        }
    }
    return null;
}

$js = findChordJs($root);
if ($js === null) {
    fwrite(STDERR, "FAIL: chordslab js file not found or not patched\n");
    exit(1);
}
$text = file_get_contents($js);
$checks = [
    'formatter helper present' => str_contains($text, 'function formatChordHtml('),
    'maj suffix class present' => str_contains($text, 'chord-quality-maj'),
    'expanded Gmaj7 diagram present' => str_contains($text, "Gmaj7:'320002'"),
    'expanded Fadd9 diagram present' => str_contains($text, "Fadd9:'103211'"),
    'checkbox inline styling hook present' => str_contains($text, "diagramToggle?.closest('label')"),
    'slot rich rendering active' => str_contains($text, "b.innerHTML=formatChordHtml(slot.text);"),
    'diagram rich rendering active' => str_contains($text, 'chord-diagram-title'),
];
foreach ($checks as $label => $ok) {
    if (!$ok) {
        fwrite(STDERR, "FAIL: {$label}\n");
        exit(1);
    }
    echo "OK: {$label}\n";
}

echo "\n" . count($checks) . " R34.2 checks passed.\n";
