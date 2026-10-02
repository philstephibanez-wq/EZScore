<?php
declare(strict_types=1);

$root = dirname(__DIR__);

function getText(string $path): string {
    if (!is_file($path)) {
        throw new RuntimeException("Missing file: ".$path);
    }
    return file_get_contents($path);
}
function putText(string $path, string $text): void {
    file_put_contents($path, $text);
}
function replaceAll(string $path, array $replacements): void {
    $text = getText($path);
    foreach ($replacements as [$from, $to]) {
        $text = str_replace($from, $to, $text);
    }
    putText($path, $text);
}
function assertAbsent(string $path, array $needles): void {
    $text = getText($path);
    foreach ($needles as $needle) {
        if (str_contains($text, $needle)) {
            throw new RuntimeException("Residual obsolete token in ".$path.": ".$needle);
        }
    }
}
function assertPresent(string $path, array $needles): void {
    $text = getText($path);
    foreach ($needles as $needle) {
        if (!str_contains($text, $needle)) {
            throw new RuntimeException("Missing expected token in ".$path.": ".$needle);
        }
    }
}

$event      = $root.'/src/Domain/Event/Event.php';
$controller = $root.'/src/Controller/EventController.php';
$index      = $root.'/templates/events/index.html.twig';
$show       = $root.'/templates/events/show.html.twig';
$base       = $root.'/templates/base.html.twig';
$fr         = $root.'/translations/event.fr.yaml';
$en         = $root.'/translations/event.en.yaml';
$enum       = $root.'/src/Domain/Event/EventMode.php';
$migration  = $root.'/migrations/Version20261002201000.php';
$payloadMig = __DIR__.'/../payload/migrations/Version20261002201000.php';

foreach ([$event,$controller,$index,$show,$base,$fr] as $p) {
    if (!is_file($p)) throw new RuntimeException("Required file missing: ".$p);
}
if (!is_file($migration) && is_file($payloadMig)) {
    copy($payloadMig, $migration);
}

/* Event.php */
replaceAll($event, [
    [<<<'FROM'
    #[ORM\Column(length: 16, enumType: EventMode::class)]
    private EventMode $mode = EventMode::Onsite;

FROM, ''],
    [<<<'FROM'
    public function getMode(): EventMode { return $this->mode; }
    public function setMode(EventMode $mode): self { $this->mode = $mode; return $this->touch(); }
FROM, ''],
]);

/* EventController.php */
replaceAll($controller, [
    ["use App\\Domain\\Event\\EventMode;\n", ""],
    [<<<'FROM'
                ->setMode(EventMode::tryFrom((string) $request->request->get('mode')) ?? EventMode::Onsite)
FROM, ''],
    [<<<'FROM'
        $mode = (string) $request->query->get('mode', '');
FROM, ''],
    [<<<'FROM'

        if (in_array($mode, array_map(static fn(EventMode $case): string => $case->value, EventMode::cases()), true)) {
            $qb->andWhere('e.mode = :mode')->setParameter('mode', $mode);
        } else {
            $mode = '';
        }
FROM, "\n"],
    ["                'mode' => \$mode,\n", ""],
]);

/* index.html.twig */
replaceAll($index, [
    [<<<'FROM'
    <label>{{ 'event.fields.mode'|trans({}, 'event') }}
      <select name="mode"><option value="onsite">{{ 'event.mode.onsite'|trans({}, 'event') }}</option><option value="remote">{{ 'event.mode.remote'|trans({}, 'event') }}</option><option value="hybrid">{{ 'event.mode.hybrid'|trans({}, 'event') }}</option></select>
    </label>
FROM, ''],
    [<<<'FROM'
    <label class="list-filter-field"><span>{{ 'event.fields.mode'|trans({}, 'event') }}</span>
      <select name="mode">
        <option value="">&mdash;</option>
        {% for mode in ['onsite','remote','hybrid'] %}<option value="{{ mode }}" {{ filters.mode == mode ? 'selected' : '' }}>{{ ('event.mode.' ~ mode)|trans({}, 'event') }}</option>{% endfor %}
      </select>
    </label>
FROM, ''],
    [", mode: filters.mode ?: null", ""],
    [<<<'FROM'
      <small>{{ ('event.mode.' ~ event.mode.value)|trans({}, 'event') }}{% if event.group %} · {{ event.group.name }}{% endif %}{% if event.playlist %} · {{ event.playlist.name }}{% endif %}</small>
FROM, <<<'TO'
      <small>{% if event.group %}{{ event.group.name }}{% endif %}{% if event.group and event.playlist %} · {% endif %}{% if event.playlist %}{{ event.playlist.name }}{% endif %}</small>
TO
    ],
]);

/* show.html.twig */
replaceAll($show, [
    [<<<'FROM'
    <p class="page-note">{{ event.startsAt|date('d/m/Y H:i') }} · {{ ('event.mode.' ~ event.mode.value)|trans({}, 'event') }}</p>
FROM, <<<'TO'
    <p class="page-note">{{ event.startsAt|date('d/m/Y H:i') }}</p>
TO
    ],
    [<<<'FROM'
    <label>{{ 'event.fields.mode'|trans({}, 'event') }}
      <select name="mode">
        {% for mode in ['onsite','remote','hybrid'] %}<option value="{{ mode }}" {{ event.mode.value == mode ? 'selected' : '' }}>{{ ('event.mode.' ~ mode)|trans({}, 'event') }}</option>{% endfor %}
      </select>
    </label>
FROM, ''],
]);

/* base topbar Session link */
replaceAll($base, [
    [<<<'FROM'
            <a class="ez-concert-link"
               href="{{ path('app_concert_control') }}"
               title="Session concert"
               aria-label="Session concert">Session</a>
FROM, <<<'TO'
            <a class="ez-concert-link"
               href="{{ path('app_events', {'_locale': app.request.locale}) }}"
               title="Sessions"
               aria-label="Sessions">Session</a>
TO
    ],
]);

/* translations */
replaceAll($fr, [
    ["    mode: Mode\n", ""],
    [<<<'FROM'
  mode:
    onsite: Présentiel
    remote: À distance
    hybrid: Hybride
FROM, ''],
]);

if (is_file($en)) {
    replaceAll($en, [
        ["    mode: Mode\n", ""],
        [<<<'FROM'
  mode:
    onsite: On-site
    remote: Remote
    hybrid: Hybrid
FROM, ''],
        [<<<'FROM'
  mode:
    onsite: Onsite
    remote: Remote
    hybrid: Hybrid
FROM, ''],
    ]);
}

if (is_file($enum)) {
    unlink($enum);
}

/* final strict checks */
assertAbsent($event, ['EventMode', 'getMode(', 'setMode(', '$mode']);
assertAbsent($controller, ['EventMode', "get('mode'", "e.mode = :mode", "'mode' => \$mode"]);
assertAbsent($index, ['event.fields.mode', 'event.mode.', 'filters.mode', 'name="mode"']);
assertAbsent($show, ['event.fields.mode', 'event.mode.', 'event.mode.value', 'name="mode"']);
assertAbsent($base, ["path('app_concert_control')"]);
assertPresent($base, ["path('app_events'"]);
assertPresent($show, ['Tester la session']);
assertPresent($migration, ['DROP COLUMN mode']);

echo "SESSION_MODE_CLEANUP_R1C1B_INSTALL_OK\n";
