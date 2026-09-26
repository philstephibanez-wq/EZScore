<?php
declare(strict_types=1);

$root = dirname(__DIR__);
$p = file_get_contents($root . '/scripts/apply_r34_1a_profile_route_fix.py');

$checks = [
    'route requirement removed' => str_contains($p, "name: 'app_song_chordslab_profile_data', methods: ['GET']"),
    'placeholder no longer blocked by router' => str_contains($p, "requirements: ['profile' => 'beginner|intermediate|expert']") === true,
    'controller validates profile' => str_contains($p, "invalid_profile"),
    'allowed profiles explicit' => str_contains($p, "['beginner', 'intermediate', 'expert']"),
    'no migration' => !str_contains($p, 'migrations/Version'),
];

foreach ($checks as $label => $ok) {
    if (!$ok) {
        fwrite(STDERR, "FAIL: $label\n");
        exit(1);
    }
    echo "OK: $label\n";
}
echo "\n" . count($checks) . " R34.1a checks passed.\n";
