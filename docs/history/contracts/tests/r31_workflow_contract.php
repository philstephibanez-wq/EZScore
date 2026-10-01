<?php
declare(strict_types=1);
$root = dirname(__DIR__);
$workflow = file_get_contents($root.'/scripts/_r31_workflow_tabs.html.twig');
$controller = file_get_contents($root.'/scripts/_r31_payload/src/Controller/SongLabController.php');
$template = file_get_contents($root.'/scripts/_r31_payload/templates/song/lab_placeholder.html.twig');
$patcher = file_get_contents($root.'/scripts/apply_r31_labs_workflow.py');
$css = file_get_contents($root.'/scripts/_r31_workflow.css');

$checks = [
    '7 workflow steps' =>
        str_contains($workflow, '1 · IMPORT')
        && str_contains($workflow, '2 · ANALYSE')
        && str_contains($workflow, '3 · ÉDITION')
        && str_contains($workflow, '4 · STEMSLAB')
        && str_contains($workflow, '5 · CHORDSLAB')
        && str_contains($workflow, '6 · LYRICSLAB')
        && str_contains($workflow, '7 · PUBLICATION'),
    'analysis route' => str_contains($controller, "name: 'app_song_analysis_lab'"),
    'chordslab route' => str_contains($controller, "name: 'app_song_chordslab'"),
    'lyricslab route' => str_contains($controller, "name: 'app_song_lyricslab'"),
    'publication route' => str_contains($controller, "name: 'app_song_publication_lab'"),
    'editor access guard' => str_contains($controller, 'ROLE_EDITOR'),
    'chordslab shell preview' => str_contains($template, '[ Em--- ]'),
    'desktop seven-column workflow' => str_contains($css, 'repeat(7'),
    'tablet four-column workflow' => str_contains($css, 'repeat(4'),
    'smartphone two-column workflow' => str_contains($css, 'repeat(2'),
    'StemsLab label' => str_contains($patcher, "StemsLab — %title%"),
    'localized routes' => str_contains($patcher, 'localized_song_labs:'),
];

foreach ($checks as $label => $ok) {
    if (!$ok) {
        fwrite(STDERR, "FAIL: {$label}\n");
        exit(1);
    }
    fwrite(STDOUT, "OK: {$label}\n");
}
fwrite(STDOUT, "\n".count($checks)." R31 workflow checks passed.\n");
