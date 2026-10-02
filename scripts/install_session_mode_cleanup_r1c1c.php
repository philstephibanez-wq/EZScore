<?php
declare(strict_types=1);

$root = dirname(__DIR__);

function readStrict(string $path): string {
    if (!is_file($path)) {
        throw new RuntimeException('Missing file: '.$path);
    }
    return file_get_contents($path);
}

function writeStrict(string $path, string $text): void {
    file_put_contents($path, $text);
}

function cleanEvent(string $path): void {
    $lines = preg_split('/\R/', readStrict($path));
    $out = [];

    foreach ($lines as $line) {
        if (str_contains($line, 'EventMode')) {
            continue;
        }
        if (str_contains($line, '$mode')) {
            continue;
        }
        $out[] = $line;
    }

    writeStrict($path, implode(PHP_EOL, $out).PHP_EOL);
}

function cleanController(string $path): void {
    $lines = preg_split('/\R/', readStrict($path));
    $out = [];
    $skipModeFilter = false;
    $sawElse = false;

    foreach ($lines as $line) {
        if ($skipModeFilter) {
            if (str_contains($line, '} else {')) {
                $sawElse = true;
            } elseif ($sawElse && trim($line) === '}') {
                $skipModeFilter = false;
                $sawElse = false;
            }
            continue;
        }

        if (str_contains($line, 'if (in_array($mode, array_map(static fn(EventMode')) {
            $skipModeFilter = true;
            $sawElse = false;
            continue;
        }

        if (str_contains($line, 'use App\\Domain\\Event\\EventMode;')) {
            continue;
        }
        if (str_contains($line, '->setMode(EventMode::tryFrom')) {
            continue;
        }
        if (str_contains($line, '$mode = (string) $request->query->get(\'mode\'')) {
            continue;
        }
        if (str_contains($line, '\'mode\' => $mode')) {
            continue;
        }

        $out[] = $line;
    }

    writeStrict($path, implode(PHP_EOL, $out).PHP_EOL);
}

function replaceIfPresent(string $path, string $from, string $to): void {
    $text = readStrict($path);
    if (str_contains($text, $from)) {
        $text = str_replace($from, $to, $text);
        writeStrict($path, $text);
    }
}

function stripTranslationModeBlock(string $path): void {
    if (!is_file($path)) return;

    $lines = preg_split('/\R/', readStrict($path));
    $out = [];
    $skip = false;

    foreach ($lines as $line) {
        if ($skip) {
            if (preg_match('/^  [A-Za-z0-9_]+:/', $line)) {
                $skip = false;
            } else {
                continue;
            }
        }

        if (trim($line) === 'mode: Mode') {
            continue;
        }

        if ($line === '  mode:') {
            $skip = true;
            continue;
        }

        $out[] = $line;
    }

    writeStrict($path, implode(PHP_EOL, $out).PHP_EOL);
}

$event = $root.'/src/Domain/Event/Event.php';
$controller = $root.'/src/Controller/EventController.php';
$index = $root.'/templates/events/index.html.twig';
$show = $root.'/templates/events/show.html.twig';
$base = $root.'/templates/base.html.twig';
$fr = $root.'/translations/event.fr.yaml';
$en = $root.'/translations/event.en.yaml';
$enum = $root.'/src/Domain/Event/EventMode.php';
$migrationPath = $root.'/migrations/Version20261002201000.php';
$payloadMigration = __DIR__.'/../payload/migrations/Version20261002201000.php';

foreach ([$event, $controller, $index, $show, $base, $fr] as $path) {
    if (!is_file($path)) {
        throw new RuntimeException('Required file missing: '.$path);
    }
}

if (!is_file($migrationPath)) {
    if (!copy($payloadMigration, $migrationPath)) {
        throw new RuntimeException('Cannot install migration');
    }
}

cleanEvent($event);
cleanController($controller);

/* Creation form mode */
replaceIfPresent(
    $index,
    <<<'FROM'
    <label>{{ 'event.fields.mode'|trans({}, 'event') }}
      <select name="mode"><option value="onsite">{{ 'event.mode.onsite'|trans({}, 'event') }}</option><option value="remote">{{ 'event.mode.remote'|trans({}, 'event') }}</option><option value="hybrid">{{ 'event.mode.hybrid'|trans({}, 'event') }}</option></select>
    </label>
FROM,
    ''
);

/* Filter mode */
replaceIfPresent(
    $index,
    <<<'FROM'
    <label class="list-filter-field"><span>{{ 'event.fields.mode'|trans({}, 'event') }}</span>
      <select name="mode">
        <option value="">&mdash;</option>
        {% for mode in ['onsite','remote','hybrid'] %}<option value="{{ mode }}" {{ filters.mode == mode ? 'selected' : '' }}>{{ ('event.mode.' ~ mode)|trans({}, 'event') }}</option>{% endfor %}
      </select>
    </label>
FROM,
    ''
);

replaceIfPresent($index, ', mode: filters.mode ?: null', '');

replaceIfPresent(
    $index,
    <<<'FROM'
      <small>{{ ('event.mode.' ~ event.mode.value)|trans({}, 'event') }}{% if event.group %} · {{ event.group.name }}{% endif %}{% if event.playlist %} · {{ event.playlist.name }}{% endif %}</small>
FROM,
    <<<'TO'
      <small>{% if event.group %}{{ event.group.name }}{% endif %}{% if event.group and event.playlist %} · {% endif %}{% if event.playlist %}{{ event.playlist.name }}{% endif %}</small>
TO
);

/* Show header/edit mode */
replaceIfPresent(
    $show,
    <<<'FROM'
    <p class="page-note">{{ event.startsAt|date('d/m/Y H:i') }} · {{ ('event.mode.' ~ event.mode.value)|trans({}, 'event') }}</p>
FROM,
    <<<'TO'
    <p class="page-note">{{ event.startsAt|date('d/m/Y H:i') }}</p>
TO
);

replaceIfPresent(
    $show,
    <<<'FROM'
    <label>{{ 'event.fields.mode'|trans({}, 'event') }}
      <select name="mode">
        {% for mode in ['onsite','remote','hybrid'] %}<option value="{{ mode }}" {{ event.mode.value == mode ? 'selected' : '' }}>{{ ('event.mode.' ~ mode)|trans({}, 'event') }}</option>{% endfor %}
      </select>
    </label>
FROM,
    ''
);

/* Topbar: real Sessions, not old ConcertSession POC */
replaceIfPresent(
    $base,
    <<<'FROM'
            <a class="ez-concert-link"
               href="{{ path('app_concert_control') }}"
               title="Session concert"
               aria-label="Session concert">Session</a>
FROM,
    <<<'TO'
            <a class="ez-concert-link"
               href="{{ path('app_events', {'_locale': app.request.locale}) }}"
               title="Sessions"
               aria-label="Sessions">Session</a>
TO
);

stripTranslationModeBlock($fr);
stripTranslationModeBlock($en);

if (is_file($enum)) {
    unlink($enum);
}

$checksAbsent = [
    $event => ['EventMode', '$mode', 'getMode(', 'setMode('],
    $controller => ['EventMode', "get('mode'", 'e.mode = :mode', "'mode' => \$mode"],
    $index => ['event.fields.mode', 'event.mode.', 'filters.mode', 'name="mode"'],
    $show => ['event.fields.mode', 'event.mode.', 'name="mode"'],
    $base => ["path('app_concert_control')"],
];

foreach ($checksAbsent as $path => $needles) {
    $text = readStrict($path);
    foreach ($needles as $needle) {
        if (str_contains($text, $needle)) {
            throw new RuntimeException('Residual obsolete token in '.$path.': '.$needle);
        }
    }
}

if (is_file($enum)) {
    throw new RuntimeException('Residual EventMode.php');
}

$baseText = readStrict($base);
if (!str_contains($baseText, "path('app_events'")) {
    throw new RuntimeException('Topbar Session link not repaired');
}

$showText = readStrict($show);
if (!str_contains($showText, 'Tester la session')) {
    throw new RuntimeException('LiveRun R1.C1 control missing');
}

echo "SESSION_MODE_CLEANUP_R1C1C_INSTALL_OK\n";
