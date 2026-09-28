<?php
declare(strict_types=1);
$root=$argv[1]??dirname(__DIR__,2);
$a=(string)file_get_contents($root.'/analysis/lyrics_timeline_analysis.py');
$s=(string)file_get_contents($root.'/src/Command/AdminMailSyncCommand.php');
$q=(string)file_get_contents($root.'/src/Command/AdminMailAuditCommand.php');
foreach(['def _find_first_audible_phrase(','def _seed_first_phrase(','No reliable first audible lyric phrase found'] as $token){
    if(!str_contains($a,$token)) throw new RuntimeException('lyrics token absent: '.$token);
}
foreach(["name: 'ezscore:admin-mail-sync'",'EZSCORE_ERROR_RECIPIENT','ERROR_REPORT_RECIPIENT'] as $token){
    if(!str_contains($s,$token)) throw new RuntimeException('sync token absent: '.$token);
}
foreach(["name: 'ezscore:admin-mail-audit'",'ADMIN_MAIL_AUDIT_OK','ADMIN_MAIL_AUDIT_DIFF='] as $token){
    if(!str_contains($q,$token)) throw new RuntimeException('audit token absent: '.$token);
}
echo "R38_5_CONTRACT_OK\n";
