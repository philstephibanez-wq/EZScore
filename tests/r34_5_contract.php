<?php
declare(strict_types=1);

$root = dirname(__DIR__);
$css = file_get_contents($root.'/public/assets/css/chordslab.css');
$js = file_get_contents($root.'/public/assets/js/chordslab-r33-1.js');
$template = file_get_contents($root.'/templates/song/chordslab.html.twig');
$fr = file_get_contents($root.'/translations/stems.fr.yaml');

$checks = [
    'CSS hard override loaded' => str_contains($css, 'R34.5 — hard visual override'),
    'root absolute size' => str_contains($css, '.chord-label-root') && str_contains($css, 'font-size: 15px !important'),
    'maj independent size' => str_contains($css, '.chord-quality-maj') && str_contains($css, 'font-size: 8px !important'),
    'guitar checkbox full row' => str_contains($css, 'grid-column: 1 / -1 !important'),
    'pause blocks auto-scroll' => str_contains($js, 'if(!playbackActive||!slot)return'),
    'tempo runtime present' => str_contains($js, 'Tempo = ${tempo}'),
    'tempo derived from beats' => str_contains($js, '60000/median'),
    'CSS cache busted' => str_contains($template, 'chordslab.css?v=20260927r34_5'),
    'main JS cache busted' => str_contains($template, 'chordslab.js?v=20260927r34_5'),
    'secondary JS cache busted' => str_contains($template, 'chordslab-r33-1.js?v=20260927r34_5'),
    'missing stems reset translated' => str_contains($fr, '    reset: Réinitialiser'),
];

foreach ($checks as $label => $ok) {
    if (!$ok) {
        fwrite(STDERR, "FAIL: $label\n");
        exit(1);
    }
    echo "OK: $label\n";
}
echo "\n".count($checks)." R34.5 checks passed.\n";
