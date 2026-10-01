<?php
declare(strict_types=1);
$root = dirname(__DIR__);
$apply = file_get_contents($root.'/scripts/apply_r29_master_fx_compact_mixer.py');
$mixer = file_get_contents($root.'/payload/r29-stems-mixer.js');
$css = file_get_contents($root.'/payload/r29-master.css');
$checks = [
    'master bus exists' => str_contains($apply, 'this.masterInput'),
    'low shelf 110 Hz' => str_contains($apply, 'frequency.value = 110'),
    'mid bell 900 Hz' => str_contains($apply, 'frequency.value = 900'),
    'high shelf 3.6 kHz' => str_contains($apply, 'frequency.value = 3600'),
    'master compressor exists' => str_contains($apply, 'this.masterCompressor'),
    'safety limiter exists' => str_contains($apply, 'this.masterLimiter'),
    'tracks feed master bus' => str_contains($apply, 'gain.connect(this.masterInput)'),
    'per-track UI has no EQ controls' => !str_contains($mixer, 'data-track-low'),
    'master EQ persists' => str_contains($mixer, 'master_eq'),
    'compression persists' => str_contains($mixer, 'master_compression'),
    'schema v2 persists' => str_contains($apply, 'ezscore.stem_mix.v2'),
    'desktop row compact target' => str_contains($css, 'min-height:42px'),
    'tablet breakpoint exists' => str_contains($css, '@media(max-width:1024px)'),
    'smartphone breakpoint exists' => str_contains($css, '@media(max-width:640px)'),
    'narrow phone breakpoint exists' => str_contains($css, '@media(max-width:390px)'),
    'mobile touch controls enlarged' => str_contains($css, 'min-height:40px'),
    'mobile mixer avoids forced width' => str_contains($css, 'min-width:0'),
    'master FX panel exists' => str_contains($css, '.stem-master-fx'),
];
foreach ($checks as $label => $ok) {
    if (!$ok) { fwrite(STDERR, "FAIL: {$label}\n"); exit(1); }
    fwrite(STDOUT, "OK: {$label}\n");
}
fwrite(STDOUT, "\n".count($checks)." R29 master-FX responsive checks passed.\n");
