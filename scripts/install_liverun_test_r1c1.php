<?php
declare(strict_types=1);

$root = dirname(__DIR__);
$payload = __DIR__.'/../payload';

function cpStrict(string $from, string $to): void {
    if (!is_file($from)) throw new RuntimeException("Payload missing: ".$from);
    $dir = dirname($to);
    if (!is_dir($dir) && !mkdir($dir, 0777, true) && !is_dir($dir)) {
        throw new RuntimeException("Cannot create directory: ".$dir);
    }
    if (!copy($from, $to)) throw new RuntimeException("Copy failed: ".$to);
}

foreach ([
    'src/Domain/Event/LiveRun.php',
    'src/Controller/LiveRunController.php',
    'migrations/Version20261002194500.php',
    'templates/live/display.html.twig',
    'public/assets/js/live/live-notification-r1c1.js',
    'public/assets/css/live/live-notification-r1c1.css',
    'public/assets/css/live/display-r1c1.css',
] as $rel) {
    cpStrict($payload.'/'.$rel, $root.'/'.$rel);
}

function patchOnce(string $path, string $needle, string $replacement, string $alreadyMarker): void {
    if (!is_file($path)) throw new RuntimeException("Missing file: ".$path);
    $src = file_get_contents($path);
    if (str_contains($src, $alreadyMarker)) return;
    if (!str_contains($src, $needle)) {
        throw new RuntimeException("Anchor not found in ".$path.": ".$needle);
    }
    file_put_contents($path, str_replace($needle, $replacement, $src));
}

/* routes.yaml */
patchOnce(
    $root.'/config/routes.yaml',
    "concert_session_controller:\n    resource: ../src/Controller/ConcertSessionController.php\n    type: attribute",
    "concert_session_controller:\n    resource: ../src/Controller/ConcertSessionController.php\n    type: attribute\n\nlive_run_controller:\n    resource: ../src/Controller/LiveRunController.php\n    type: attribute",
    'live_run_controller:'
);

/* base.html.twig : CSS + banner + JS */
patchOnce(
    $root.'/templates/base.html.twig',
    '<link rel="stylesheet" href="/assets/css/concert-sync-r1.css?v=20261002r1">',
    '<link rel="stylesheet" href="/assets/css/concert-sync-r1.css?v=20261002r1">'."\n".'<link rel="stylesheet" href="/assets/css/live/live-notification-r1c1.css?v=20261002r1c1">',
    'live-notification-r1c1.css'
);

patchOnce(
    $root.'/templates/base.html.twig',
    '    <main class="ez-main" id="main-content">',
    <<<'TWIG'
    {% if is_granted('ROLE_DISPLAY') %}
    <div class="live-notification" data-live-notification data-live-status-url="{{ path('app_live_open') }}" hidden>
        <div class="live-notification-inner">
            <strong data-live-label>Session ouverte</strong>
            <span data-live-conductor></span>
            <a data-live-join href="#">Rejoindre</a>
        </div>
    </div>
    {% endif %}

    <main class="ez-main" id="main-content">
TWIG,
    'data-live-notification'
);

patchOnce(
    $root.'/templates/base.html.twig',
    '<script src="/assets/js/app.js?v=20260924f"></script>',
    '<script src="/assets/js/app.js?v=20260924f"></script>'."\n".'{% if app.user and is_granted(\'ROLE_DISPLAY\') %}<script src="/assets/js/live/live-notification-r1c1.js?v=20261002r1c1"></script>{% endif %}',
    'live-notification-r1c1.js'
);

/* Session show : test start/stop control only for owner */
patchOnce(
    $root.'/templates/events/show.html.twig',
    "{% if event.createdBy.id == app.user.id and event.status.value == 'draft' %}",
    <<<'TWIG'
{% if event.createdBy.id == app.user.id %}
<section class="panel">
  <h2>Test projection</h2>
  <p class="page-note">Ouvre un LiveRun de test sans envoyer d'invitation.</p>
  <div class="collection-actions">
    <form method="post" action="{{ path('app_live_test_start', {id: event.id}) }}">
      <input type="hidden" name="_token" value="{{ csrf_token('live_test_start_' ~ event.id) }}">
      <button class="primary" type="submit">Tester la session</button>
    </form>
    <form method="post" action="{{ path('app_live_test_stop', {id: event.id}) }}">
      <input type="hidden" name="_token" value="{{ csrf_token('live_test_stop_' ~ event.id) }}">
      <button type="submit">Arrêter le test</button>
    </form>
  </div>
</section>
{% endif %}

{% if event.createdBy.id == app.user.id and event.status.value == 'draft' %}
TWIG,
    'Tester la session'
);

echo "LIVERUN_TEST_R1C1_INSTALL_OK\n";
