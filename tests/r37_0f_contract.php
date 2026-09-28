<?php
declare(strict_types=1);

$root=$argv[1]??dirname(__DIR__,2);
$path=$root.'/public/assets/js/lyricslab-r37.js';
if(!is_file($path)) throw new RuntimeException('lyricslab-r37.js absent');

$s=(string)file_get_contents($path);

$tokens=[
    'const form=e.currentTarget;',
    'if(await saveSource()){',
    'form.submit();',
];

foreach($tokens as $token){
    if(!str_contains($s,$token)){
        throw new RuntimeException("Token absent: ".$token);
    }
}

if(str_contains($s,'if(await saveSource())e.currentTarget.submit();')){
    throw new RuntimeException('Ancien submit async encore présent');
}

echo "R37_0F_CONTRACT_OK\n";
