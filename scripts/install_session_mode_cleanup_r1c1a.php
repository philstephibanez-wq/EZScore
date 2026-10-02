<?php
declare(strict_types=1);

$root = dirname(__DIR__);

function readFileStrict(string $path): string {
    if (!is_file($path)) throw new RuntimeException("Missing file: ".$path);
    return file_get_contents($path);
}
function writeFileStrict(string $path, string $text): void {
    file_put_contents($path, $text);
}
function removeBlock(string $src, string $block): string {
    if (str_contains($src, $block)) {
        return str_replace($block, '', $src);
    }
    return $src;
}
function mustNotContain(string $path, array $needles): void {
    $src = readFileStrict($path);
    foreach ($needles as $needle) {
        if (str_contains($src, $needle)) {
            throw new RuntimeException("Residual obsolete mode in ".$path.": ".$needle);
        }
    }
}

$event = $root.'/src/Domain/Event/Event.php';
$controller = $root.'/src/Controller/EventController.php';
$index = $root.'/templates/events/index.html.twig';
$show = $root.'/templates/events/show.html.twig';
$base = $root.'/templates/base.html.twig';
$fr = $root.'/translations/event.fr.yaml';
$en = $root.'/translations/event.en.yaml';
$enum = $root.'/src/Domain/Event/EventMode.php';
$migrationSrc = __DIR__.'/../payload/migrations/Version20261002201000.php';
$migrationDst = $root.'/migrations/Version20261002201000.php';

foreach ([$event,$controller,$index,$show,$base,$fr] as $p) {
    if (!is_file($p)) throw new RuntimeException("Required file missing: ".$p);
}
if (!is_file($migrationSrc)) throw new RuntimeException("Migration payload missing");
copy($migrationSrc, $migrationDst);

/* Event domain */
$s = readFileStrict($event);
$s = preg_replace("/\n\s*#\[ORM\\\\Column\(length: 16, enumType: EventMode::class\)\]\n\s*private EventMode \$mode = EventMode::Onsite;\n/", "\n", $s) ?? $s;
$s = preg_replace("/\n\s*public function getMode\(\): EventMode \{ return \$this->mode; \}\n\s*public function setMode\(EventMode \$mode\): self \{ \$this->mode = \$mode; return \$this->touch\(\); \}/", "", $s) ?? $s;
writeFileStrict($event, $s);

/* Event controller */
$s = readFileStrict($controller);
$s = str_replace("use App\\Domain\\Event\\EventMode;\n", "", $s);
$s = preg_replace("/\n\s*->setMode\(EventMode::tryFrom\(\(string\) \$request->request->get\('mode'\)\) \?\? EventMode::Onsite\)/", "", $s) ?? $s;
$s = preg_replace("/\n\s*\\$mode = \(string\) \$request->query->get\('mode', ''\);/", "", $s) ?? $s;
$s = preg_replace("/\n\s*if \(in_array\(\$mode, array_map\(static fn\(EventMode \$case\): string => \$case->value, EventMode::cases\(\)\), true\)\) \{\n\s*\\$qb->andWhere\('e\.mode = :mode'\)->setParameter\('mode', \$mode\);\n\s*\} else \{\n\s*\\$mode = '';\n\s*\}/", "", $s) ?? $s;
$s = str_replace("                'mode' => $mode,\n", "", $s);
writeFileStrict($controller, $s);

/* Index template */
$s = readFileStrict($index);
$s = preg_replace("/\n\s*<label>\{\{ 'event\.fields\.mode'\|trans\(\{\}, 'event'\) \}\}.*?<\/label>/s", "", $s) ?? $s;
$s = preg_replace("/\n\s*<label class=\"list-filter-field\"><span>\{\{ 'event\.fields\.mode'.*?<\/label>/s", "", $s) ?? $s;
$s = str_replace(", mode: filters.mode ?: null", "", $s);
$s = preg_replace("/<small>\{\{ \('event\.mode\.' ~ event\.mode\.value\)\|trans\(\{\}, 'event'\) \}\}\{% if event\.group %\} · \{\{ event\.group\.name \}\}\{% endif %\}\{% if event\.playlist %\} · \{\{ event\.playlist\.name \}\}\{% endif %\}<\/small>/",
    "<small>{% if event.group %}{{ event.group.name }}{% endif %}{% if event.group and event.playlist %} · {% endif %}{% if event.playlist %}{{ event.playlist.name }}{% endif %}</small>", $s) ?? $s;
writeFileStrict($index, $s);

/* Show template */
$s = readFileStrict($show);
$s = preg_replace("/\n\s*<p class=\"page-note\">\{\{ event\.startsAt\|date\('d\/m\/Y H:i'\) \}\} · \{\{ \('event\.mode\.' ~ event\.mode\.value\)\|trans\(\{\}, 'event'\) \}\}<\/p>/",
    "\n    <p class=\"page-note\">{{ event.startsAt|date('d/m/Y H:i') }}</p>", $s) ?? $s;
$s = preg_replace("/\n\s*<label>\{\{ 'event\.fields\.mode'\|trans\(\{\}, 'event'\) \}\}\n\s*<select name=\"mode\">.*?<\/select>\n\s*<\/label>/s", "", $s) ?? $s;
writeFileStrict($show, $s);

/* Base topbar: Session must open real Session list, never legacy /concert/control */
$s = readFileStrict($base);
$s = preg_replace(
    "/<a class=\"ez-concert-link\"\s+href=\"\{\{ path\('app_concert_control'\) \}\}\"\s+title=\"Session concert\"\s+aria-label=\"Session concert\">Session<\/a>/s",
    '<a class="ez-concert-link" href="{{ path(\'app_events\', {\'_locale\': app.request.locale}) }}" title="Sessions" aria-label="Sessions">Session</a>',
    $s
) ?? $s;
writeFileStrict($base, $s);

/* Translations: remove mode field and mode block */
$s = readFileStrict($fr);
$s = preg_replace("/^\s{4}mode: Mode\r?\n/m", "", $s) ?? $s;
$s = preg_replace("/^\s{2}mode:\r?\n(?:\s{4}.+\r?\n){3}/m", "", $s) ?? $s;
writeFileStrict($fr, $s);

if (is_file($en)) {
    $s = readFileStrict($en);
    $s = preg_replace("/^\s{4}mode: Mode\r?\n/m", "", $s) ?? $s;
    $s = preg_replace("/^\s{2}mode:\r?\n(?:\s{4}.+\r?\n){3}/m", "", $s) ?? $s;
    writeFileStrict($en, $s);
}

/* Remove obsolete enum entirely */
if (is_file($enum)) {
    unlink($enum);
}

/* Strict contract guards */
mustNotContain($event, ['EventMode', '$mode']);
mustNotContain($controller, ['EventMode', "get('mode'", "'mode' => \$mode"]);
mustNotContain($index, ['event.fields.mode', 'event.mode.', 'filters.mode']);
mustNotContain($show, ['event.fields.mode', 'event.mode.', 'event.mode.value']);
mustNotContain($base, ["path('app_concert_control')"]);

echo "SESSION_MODE_CLEANUP_R1C1A_INSTALL_OK\n";
