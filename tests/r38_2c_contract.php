<?php
declare(strict_types=1);

$root=$argv[1]??dirname(__DIR__,2);
$a=(string)file_get_contents($root.'/analysis/lyrics_timeline_analysis.py');
$r=(string)file_get_contents($root.'/src/Service/AdminRecipientResolver.php');
$c=(string)file_get_contents($root.'/src/Controller/ContactController.php');
$u=(string)file_get_contents($root.'/src/Domain/User/UserRepository.php');

foreach([
    'if left is None:',
    'Keeping start_ms=None prevents any word from being serialized at t=0.',
    'if block.size >= 2',
    'anchored_rows = [row for row in rows if row.get(\'start_ms\') is not None]',
] as $token){
    if(!str_contains($a,$token)) throw new RuntimeException('alignment token absent: '.$token);
}

$alignStart=strpos($a,'def align_provided_text(');
$alignEnd=strpos($a,"\ndef main()", $alignStart);
$align=substr($a,$alignStart,$alignEnd-$alignStart);
if(str_contains($align,"elif tag == 'replace'")){
    throw new RuntimeException('replace opcode still creates anchors');
}
if(str_contains($a,"'start_ms': int(row.get('start_ms') or 0)")){
    throw new RuntimeException('unanchored word still coerced to t=0');
}

foreach([
    'final class AdminRecipientResolver',
    'findFirstCreatedAdmin()',
    '$adminRecipient->resolve()',
    '->to($admin->getEmail())',
] as $token){
    if(!str_contains($r,$token) && !str_contains($c,$token) && !str_contains($u,$token)){
        throw new RuntimeException('admin recipient token absent: '.$token);
    }
}

$iterator=new RecursiveIteratorIterator(new RecursiveDirectoryIterator($root.'/src'));
foreach($iterator as $file){
    if(!$file->isFile() || $file->getExtension()!=='php') continue;
    $text=(string)file_get_contents($file->getPathname());
    if(str_contains($text,'EZSCORE_ADMIN_CONTACT_EMAIL')){
        throw new RuntimeException('legacy admin recipient env still used in '.$file->getPathname());
    }
}

echo "R38_2C_CONTRACT_OK\n";
