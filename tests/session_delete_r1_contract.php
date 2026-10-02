<?php
declare(strict_types=1);

$root = dirname(__DIR__);
$tpl = file_get_contents($root.'/templates/events/show.html.twig');

$must = [
    'data-session-delete-open',
    'data-session-delete-dialog',
    'data-session-delete-cancel',
    'session-delete-confirm-r1.js',
    'session-delete-confirm-r1.css',
    "csrf_token('event_delete_' ~ event.id)",
    "event.delete_confirm_button",
];

foreach ($must as $needle) {
    if (!str_contains($tpl, $needle)) {
        fwrite(STDERR, "SESSION_DELETE_R1 missing: {$needle}\n");
        exit(1);
    }
}

if (str_contains($tpl, 'return confirm(')) {
    fwrite(STDERR, "SESSION_DELETE_R1 native confirm still present\n");
    exit(1);
}

foreach ([
    'public/assets/js/events/session-delete-confirm-r1.js',
    'public/assets/css/events/session-delete-confirm-r1.css',
] as $rel) {
    if (!is_file($root.'/'.$rel)) {
        fwrite(STDERR, "SESSION_DELETE_R1 missing file: {$rel}\n");
        exit(1);
    }
}

echo "SESSION_DELETE_R1_CONTRACT_OK\n";
