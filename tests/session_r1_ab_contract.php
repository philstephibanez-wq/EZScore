<?php
declare(strict_types=1);

$root = dirname(__DIR__);
$checks = [
    'src/Domain/Event/Event.php' => [
        'EventStatus::Draft',
        'private ?\\DateTimeImmutable $validatedAt = null;',
        'public function validate(): self',
    ],
    'src/Domain/Event/EventStatus.php' => ["case Validated = 'validated';"],
    'src/Controller/EventController.php' => [
        "get('group_id')",
        "get('playlist_id')",
        "->setStatus(EventStatus::Draft)",
        "name: 'app_event_validate'",
        "required_group_playlist",
        "session_not_validated",
    ],
    'src/Security/Acl/EventVoter.php' => [
        'EventStatus::Draft',
        'if ($subject->getStatus() === EventStatus::Draft && !$creator)',
    ],
    'templates/events/index.html.twig' => ['name="group_id"', 'name="playlist_id"'],
    'templates/events/show.html.twig' => ['app_event_validate'],
    'translations/event.fr.yaml' => ['validated: Validée', 'validate_button:', 'required_group_playlist:'],
    'translations/event.en.yaml' => ['validated: Validated', 'validate_button:', 'required_group_playlist:'],
    'migrations/Version20261002170000.php' => ['validated_at'],
];

foreach ($checks as $rel => $needles) {
    $path = $root.DIRECTORY_SEPARATOR.str_replace('/', DIRECTORY_SEPARATOR, $rel);
    if (!is_file($path)) { fwrite(STDERR, "MISSING_FILE $rel\n"); exit(1); }
    $text = file_get_contents($path);
    foreach ($needles as $needle) {
        if (!str_contains($text, $needle)) {
            fwrite(STDERR, "MISSING_CONTRACT $rel :: $needle\n");
            exit(1);
        }
    }
}

$controller = file_get_contents($root.'/src/Controller/EventController.php');
$a = strpos($controller, 'public function setGroup(');
$b = strpos($controller, 'public function setPlaylist(');
if ($a === false || $b === false) { fwrite(STDERR, "SET_GROUP_BLOCK_MISSING\n"); exit(1); }
$setGroup = substr($controller, $a, $b - $a);
if (str_contains($setGroup, 'sendInvitation(') || str_contains($setGroup, 'new EventParticipant(')) {
    fwrite(STDERR, "DRAFT_GROUP_ASSIGNMENT_STILL_INVITES\n"); exit(1);
}

echo "SESSION_R1_AB_CONTRACT_OK\n";
