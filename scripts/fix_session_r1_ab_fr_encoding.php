<?php
declare(strict_types=1);

$root = dirname(__DIR__);
$path = $root . DIRECTORY_SEPARATOR . 'translations' . DIRECTORY_SEPARATOR . 'event.fr.yaml';

if (!is_file($path)) {
    fwrite(STDERR, "SESSION_R1_AB_HOTFIX6 missing file: {$path}\n");
    exit(1);
}

$text = file_get_contents($path);
if ($text === false) {
    fwrite(STDERR, "SESSION_R1_AB_HOTFIX6 cannot read translation file\n");
    exit(1);
}

/* Repair common UTF-8 mojibake byte sequences. */
$map = [
    'c383c2a9' => 'c3a9',
    'c383c2a8' => 'c3a8',
    'c383c2a0' => 'c3a0',
    'c383c2a2' => 'c3a2',
    'c383c2aa' => 'c3aa',
    'c383c2b4' => 'c3b4',
    'c383c2a7' => 'c3a7',
    'c383c2b9' => 'c3b9',
    'c383c2bb' => 'c3bb',
    'c383c2ae' => 'c3ae',
];

foreach ($map as $badHex => $goodHex) {
    $text = str_replace(hex2bin($badHex), hex2bin($goodHex), $text);
}

$canonical = '    validated: Valid' . hex2bin('c3a9') . "e";
$lines = preg_split('/\R/', $text);
if ($lines === false) {
    fwrite(STDERR, "SESSION_R1_AB_HOTFIX6 cannot split YAML\n");
    exit(1);
}

$insideStatus = false;
$fixedStatus = false;

foreach ($lines as &$line) {
    if ($line === '  status:') {
        $insideStatus = true;
        continue;
    }

    if ($insideStatus && preg_match('/^  [A-Za-z0-9_]+:/', $line) === 1 && !str_starts_with($line, '    ')) {
        $insideStatus = false;
    }

    if ($insideStatus && preg_match('/^    validated:/', $line) === 1) {
        $line = $canonical;
        $fixedStatus = true;
    }
}
unset($line);

if (!$fixedStatus) {
    fwrite(STDERR, "SESSION_R1_AB_HOTFIX6 status.validated not found\n");
    exit(1);
}

$out = implode(PHP_EOL, $lines);
if (file_put_contents($path, $out) === false) {
    fwrite(STDERR, "SESSION_R1_AB_HOTFIX6 cannot write translation file\n");
    exit(1);
}

echo "SESSION_R1_AB_HOTFIX6_OK\n";
