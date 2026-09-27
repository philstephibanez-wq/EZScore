<?php
declare(strict_types=1);
$root=$argv[1]??dirname(__DIR__,2);
$checks=[
 'config/routes.yaml'=>['localized_song_collaboration:','localized_contact:'],
 'templates/base.html.twig'=>['app_contact_admin','r35-4a-contact-header.css'],
 'src/Domain/Analysis/AnalysisJob.php'=>['function touchLease'],
 'src/Controller/AnalysisDesktopController.php'=>['touchLease()','current_job'],
 'worker_app/ezscore_analysis_worker.pyw'=>['locally_running','current_id'],
 'public/assets/css/r35-4a-contact-header.css'=>['ez-contact-admin-link'],
];
foreach($checks as $rel=>$tokens){
 $p=$root.DIRECTORY_SEPARATOR.str_replace('/',DIRECTORY_SEPARATOR,$rel);
 if(!is_file($p)) throw new RuntimeException("Fichier absent: $rel");
 $s=(string)file_get_contents($p);
 foreach($tokens as $t) if(!str_contains($s,$t)) throw new RuntimeException("$rel: token absent: $t");
}
$dash=(string)file_get_contents($root.'/templates/song/analysis_dashboard.html.twig');
if(str_contains($dash,"app_contact_admin")) throw new RuntimeException("Le contact admin doit être global, pas dans le dashboard chanson.");
echo "R35_4A_CONTRACT_OK\n";
