<?php
declare(strict_types=1);

$root=$argv[1]??dirname(__DIR__,2);

$adminPatterns=[
    'EZSCORE_ADMIN_CONTACT_EMAIL',
    'ADMIN_EMAIL',
    'adminEmail',
];

$bad=[];
$iterator=new RecursiveIteratorIterator(new RecursiveDirectoryIterator($root.'/src'));
foreach($iterator as $file){
    if(!$file->isFile() || $file->getExtension()!=='php') continue;
    $text=(string)file_get_contents($file->getPathname());

    foreach($adminPatterns as $pattern){
        if(str_contains($text,$pattern)){
            $bad[]=$file->getPathname().' :: '.$pattern;
        }
    }
}

if($bad!==[]){
    fwrite(STDERR,"ADMIN_MAIL_AUDIT_FAILED\n".implode("\n",$bad)."\n");
    exit(1);
}

echo "ADMIN_MAIL_AUDIT_OK\n";
