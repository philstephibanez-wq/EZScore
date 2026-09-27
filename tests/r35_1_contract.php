<?php
declare(strict_types=1);
$root = $argv[1] ?? dirname(__DIR__, 2);
$checks = [
 'worker_app/ezscore_analysis_worker.pyw'=>['APP_VERSION = "R35.1"','Redémarrer Worker','Démarrer serveur','Arrêter serveur','stop_and_wait'],
 'analysis/chord_timeline_analysis.py'=>['meter_detection_r35_1','"meter_candidates"','"meter_sources"'],
 'analysis/meter_detection_r35_1.py'=>['("2/4", "3/4", "4/4", "6/8")','0.62*rhythm+0.25*bass+0.13*harmony'],
 'src/Controller/SongImportController.php'=>["name: 'app_song_reimport'",'deleteAllForSong','markImported'],
 'templates/song/workspace.html.twig'=>['Réimporter','SUPPRIME/INVALIDE stems, accords, paroles, alignements'],
 'templates/catalog/index.html.twig'=>['R35.1_ROLE_ACTIONS'],
];
foreach($checks as $rel=>$tokens){$p=$root.DIRECTORY_SEPARATOR.str_replace('/',DIRECTORY_SEPARATOR,$rel);if(!is_file($p))throw new RuntimeException("Missing $rel");$s=(string)file_get_contents($p);foreach($tokens as $t)if(!str_contains($s,$t))throw new RuntimeException("$rel missing $t");}
echo "R35_1_CONTRACT_OK\n";
