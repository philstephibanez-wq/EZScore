<?php
declare(strict_types=1);
$root=$argv[1]??dirname(__DIR__,2);
$a=(string)file_get_contents($root.'/analysis/lyrics_timeline_analysis.py');
$w=(string)file_get_contents($root.'/worker_app/lyrics_worker_r37.py');
$c=(string)file_get_contents($root.'/src/Command/AdminMailSyncCommand.php');

foreach([
    'def _earliest_phrase_anchor(',
    'A lone word such as "Je" is never enough evidence.',
    'Seed the first real phrase directly with Whisper timestamps.',
    'if sim < 0.82 or conf < 0.30:',
] as $token){
    if(!str_contains($a,$token)) throw new RuntimeException('lyrics token absent: '.$token);
}
foreach([
    'lyrics_output_tail=[]',
    'lyrics_output_tail.append(line)',
    'lyrics_python_exit_{rc}: {tail}',
] as $token){
    if(!str_contains($w,$token)) throw new RuntimeException('worker diagnostic absent: '.$token);
}
foreach([
    "name: 'ezscore:admin-mail-sync'",
    "'EZSCORE_ADMIN_EMAIL'",
    "'EZSCORE_ERROR_RECIPIENT'",
    'MAILER_FROM non modifié.',
] as $token){
    if(!str_contains($c,$token)) throw new RuntimeException('mail sync token absent: '.$token);
}
echo "R38_4B_CONTRACT_OK\n";
