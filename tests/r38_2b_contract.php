<?php
declare(strict_types=1);

$root=$argv[1]??dirname(__DIR__,2);
$a=(string)file_get_contents($root.'/analysis/lyrics_timeline_analysis.py');
$c=(string)file_get_contents($root.'/src/Controller/ContactController.php');
$u=(string)file_get_contents($root.'/src/Domain/User/UserRepository.php');

foreach([
    'Only exact consecutive runs are allowed to create acoustic anchors.',
    'if block.size >= 2',
    'replace" blocks are deliberately ignored',
    'A prefix before the first reliable acoustic anchor is NOT spread toward t=0.',
] as $token){
    if(!str_contains($a,$token)) throw new RuntimeException('alignment token absent: '.$token);
}

$alignStart=strpos($a,'def align_provided_text(');
$alignEnd=strpos($a,"\ndef main()", $alignStart);
$align=substr($a,$alignStart,$alignEnd-$alignStart);
if(str_contains($align,"elif tag == 'replace'")){
    throw new RuntimeException('replace opcode still creates anchors');
}

foreach([
    'findFirstCreatedAdmin()',
    '->to($admin->getEmail())',
    "%env(MAILER_FROM)%",
] as $token){
    if(!str_contains($c,$token) && !str_contains($u,$token)){
        throw new RuntimeException('mail token absent: '.$token);
    }
}

if(str_contains($c,'EZSCORE_ADMIN_CONTACT_EMAIL')){
    throw new RuntimeException('legacy EZSCORE_ADMIN_CONTACT_EMAIL recipient still present');
}

echo "R38_2B_CONTRACT_OK\n";
