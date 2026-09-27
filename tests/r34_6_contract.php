<?php
declare(strict_types=1);

$root = dirname(__DIR__);
$main = file_get_contents($root.'/public/assets/js/chordslab.js');
$secondary = file_get_contents($root.'/public/assets/js/chordslab-r33-1.js');
$css = file_get_contents($root.'/public/assets/css/chordslab.css');
$template = file_get_contents($root.'/templates/song/chordslab.html.twig');

$checks = [
    'old duplicate tempo removed' => !str_contains($main, 'R34.4 tempo display: derived from canonical beat timeline'),
    'tempo de-dup query present' => str_contains($secondary, ".chordslab-tempo-value,[data-chordslab-tempo-runtime]"),
    'root enlarged' => str_contains($css, 'font-size:17px!important'),
    'suffix enlarged' => str_contains($css, 'font-size:12px!important'),
    'maj baseline' => str_contains($css, 'vertical-align:baseline!important'),
    'slot baseline alignment' => str_contains($css, 'align-items:baseline!important'),
    'css cache busted' => str_contains($template, 'chordslab.css?v=20260927r34_6'),
    'main js cache busted' => str_contains($template, 'chordslab.js?v=20260927r34_6'),
    'secondary js cache busted' => str_contains($template, 'chordslab-r33-1.js?v=20260927r34_6'),
];

foreach ($checks as $label => $ok) {
    if (!$ok) {
        fwrite(STDERR, "FAIL: $label\n");
        exit(1);
    }
    echo "OK: $label\n";
}
echo "\n".count($checks)." R34.6 checks passed.\n";
