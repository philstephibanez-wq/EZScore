<?php
declare(strict_types=1);

$root = $argv[1] ?? 'H:\\EZScore_v1';

function fail_contract(string $message): never
{
    fwrite(STDERR, $message.PHP_EOL);
    exit(1);
}

$repo = @file_get_contents($root.'/src/Domain/Song/LyricsSourceRevisionRepository.php');
$ctrl = @file_get_contents($root.'/src/Controller/LyricsHistoryController.php');
$service = @file_get_contents($root.'/src/Service/LyricsSourceHistoryService.php');

if ($repo === false || $ctrl === false || $service === false) {
    fail_contract('Missing lyrics history files');
}

foreach ([
    'public function findCurrentForSong(',
    "->andWhere('revision.content = :content')",
    "->orderBy('revision.createdAt', 'DESC')",
    "->addOrderBy('revision.id', 'DESC')",
    '->setMaxResults(1)',
] as $needle) {
    if (strpos($repo, $needle) === false) {
        fail_contract('Current revision repository contract missing: '.$needle);
    }
}

foreach ([
    '$currentRevision = $revisions->findCurrentForSong($song);',
    '$currentRevisionId = $currentRevision?->getId();',
    "'is_current' => \$currentRevisionId !== null && \$revision->getId() === \$currentRevisionId",
] as $needle) {
    if (strpos($ctrl, $needle) === false) {
        fail_contract('Single-current controller contract missing: '.$needle);
    }
}

if (strpos($ctrl, '$revision->getContent() === $current') !== false) {
    fail_contract('Old content-equality current marker still present');
}

foreach ([
    '$currentRevision = $this->revisions->findCurrentForSong($song);',
    '$currentRevision->getId() === $revision->getId()',
] as $needle) {
    if (strpos($service, $needle) === false) {
        fail_contract('Delete protection contract missing: '.$needle);
    }
}

if (strpos($service, '$revision->getContent() === $this->normaliseContent') !== false) {
    fail_contract('Old delete protection by content still present');
}

echo "R38_16K_SINGLE_CURRENT_LYRICS_REVISION_CONTRACT_OK".PHP_EOL;
