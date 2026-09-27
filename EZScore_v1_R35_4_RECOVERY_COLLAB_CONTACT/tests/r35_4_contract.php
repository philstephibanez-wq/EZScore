<?php
declare(strict_types=1);
$root=$argv[1]??dirname(__DIR__,2);
$checks=['src/Domain/Analysis/AnalysisJob.php'=>['function requeue'],'src/Domain/Analysis/AnalysisJobRepository.php'=>['findStaleRunning'],'src/Controller/AnalysisDesktopController.php'=>['recoverStaleJobs','-120 seconds'],'src/Domain/Song/SongCollaborator.php'=>['uniq_song_collaborator'],'src/Service/SongAccessPolicy.php'=>['canManageDelegation'],'src/Controller/SongCollaborationController.php'=>['app_song_collaborator_add'],'src/Domain/Song/SongRepository.php'=>['findByAudioSha256','findLikelyDuplicate'],'src/Controller/ContactController.php'=>['EZSCORE_ADMIN_CONTACT_EMAIL','replyTo'],'migrations/Version20260927093000.php'=>['song_collaborators','contact_messages'],'worker_app/ezscore_analysis_worker.pyw'=>['APP_VERSION = "R35.4"']];
foreach($checks as $rel=>$tokens){$p=$root.DIRECTORY_SEPARATOR.str_replace('/',DIRECTORY_SEPARATOR,$rel);if(!is_file($p))throw new RuntimeException("Fichier absent: $rel");$s=(string)file_get_contents($p);foreach($tokens as $t)if(!str_contains($s,$t))throw new RuntimeException("$rel: token absent: $t");}
echo "R35_4_CONTRACT_OK\n";
