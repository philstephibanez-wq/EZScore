<?php
declare(strict_types=1);

$root = $argv[1] ?? 'H:\\EZScore_v1';

function fail_contract(string $m): never {
    fwrite(STDERR, $m.PHP_EOL);
    exit(1);
}

$song = @file_get_contents($root.'/src/Domain/Song/Song.php');
$svc = @file_get_contents($root.'/src/Service/LyricsSourceHistoryService.php');
$ctl = @file_get_contents($root.'/src/Controller/LyricsHistoryController.php');

if ($song === false || $svc === false || $ctl === false) {
    fail_contract('Missing R38.16l1 files');
}

foreach ([
    'lyrics_current_revision_id',
    'getLyricsCurrentRevisionId()',
    'setLyricsCurrentRevisionId(?int $revisionId)',
] as $n) {
    if (strpos($song, $n) === false) fail_contract('Song missing '.$n);
}

$a = strpos($svc, 'public function restore(');
$b = strpos($svc, 'public function delete(', $a);
$r = substr($svc, $a, $b - $a);

foreach ([
    '$song->setLyricsSourceText($target->getContent());',
    '$song->setLyricsCurrentRevisionId($target->getId());',
    'return $target;',
] as $n) {
    if (strpos($r, $n) === false) fail_contract('Restore missing '.$n);
}

foreach (['saveVersion(', 'archiveCurrentIfChanged(', 'new LyricsSourceRevision('] as $n) {
    if (strpos($r, $n) !== false) fail_contract('Restore still duplicates: '.$n);
}

if (strpos($svc, '$song->getLyricsCurrentRevisionId() === $revision->getId()') === false) {
    fail_contract('Delete protection wrong');
}

if (strpos($ctl, '$currentRevisionId = $song->getLyricsCurrentRevisionId();') === false) {
    fail_contract('Controller exact current ID missing');
}

echo "R38_16L1_RESTORE_EXACT_REVISION_REPAIR_CONTRACT_OK".PHP_EOL;
