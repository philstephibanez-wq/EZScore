<?php
declare(strict_types=1);

$root = $argv[1] ?? dirname(__DIR__, 2);
$checks = [
    'worker_app/ezscore_analysis_worker.pyw' => [
        'APP_VERSION = "R35.2"',
        'Traitements en cours / à faire',
        '/internal/analysis/desktop/jobs/queue',
        'Redémarrer Worker',
        'Démarrer serveur',
        'Arrêter serveur',
        'stop_and_wait',
    ],
    'src/Controller/AnalysisDesktopController.php' => [
        "#[Route('/jobs/queue'",
        'findDesktopQueue',
    ],
    'src/Domain/Analysis/AnalysisJobRepository.php' => [
        'findDesktopQueue',
        'AnalysisJobStatus::Queued',
        'AnalysisJobStatus::Running',
    ],
    'analysis/chord_timeline_analysis.py' => [
        'meter_detection_r35_2',
        'meter_candidates',
    ],
    'analysis/meter_detection_r35_2.py' => [
        'CANDIDATES = ("2/4", "3/4", "4/4", "6/8")',
        '0.62 * drums + 0.25 * bass + 0.13 * harmony',
    ],
    'src/Controller/SongImportController.php' => [
        "name: 'app_song_reimport'",
        'deleteAllForSong',
        'deleteForSong',
        'markImported',
    ],
    'templates/song/workspace.html.twig' => [
        'Réimporter',
        'invalide stems, accords, paroles, alignements',
    ],
    'templates/catalog/index.html.twig' => [
        '<option value="0">{{ song.editor.displayName }}</option>',
        '<option value="0">—</option>',
    ],
];
foreach ($checks as $relative => $needles) {
    $path = rtrim($root, DIRECTORY_SEPARATOR).DIRECTORY_SEPARATOR.str_replace('/', DIRECTORY_SEPARATOR, $relative);
    if (!is_file($path)) {
        throw new RuntimeException("Fichier absent: $relative");
    }
    $content = (string) file_get_contents($path);
    foreach ($needles as $needle) {
        if (!str_contains($content, $needle)) {
            throw new RuntimeException("$relative: contrat absent: $needle");
        }
    }
}
echo "R35_2_CONTRACT_OK\n";
