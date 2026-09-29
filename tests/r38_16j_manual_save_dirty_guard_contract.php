<?php
declare(strict_types=1);
$root=$argv[1]??'H:\\EZScore_v1';
function f(string $m): never {fwrite(STDERR,$m.PHP_EOL);exit(1);}
$template=@file_get_contents($root.'/templates/song/lyricslab.html.twig');
$lab=@file_get_contents($root.'/public/assets/js/lyricslab-r37.js');
$hist=@file_get_contents($root.'/public/assets/js/lyrics-history-r38-15.js');
$guard=@file_get_contents($root.'/public/assets/js/lyrics-dirty-guard-r38-16j.js');
if($template===false||$lab===false||$hist===false||$guard===false)f('Missing R38.16j files');
foreach(['timer=setTimeout(save,450)','data-lyrics-save-state'] as $x) if(strpos($lab,$x)!==false) f('Autosave remains: '.$x);
foreach(['Sauvegarder cette version','data-lyrics-history-save','Historique des paroles','data-lyrics-history-list','data-lyrics-manual-state'] as $x) if(strpos($template,$x)===false) f('Missing save/history UI: '.$x);
$save=strpos($template,'data-lyrics-history-save');$details=strpos($template,'<details class="lyrics-history"');if($save===false||$details===false||$save>$details)f('Save controls must remain visible before history');
foreach(['Voulez-vous quitter la page sans sauvegarder vos modifications ?','Rester sur la page','Quitter sans sauvegarder'] as $x) if(strpos($guard,$x)===false) f('Dirty modal missing: '.$x);
foreach(['beforeunload','confirm(','alert(','prompt('] as $x) if(strpos($guard,$x)!==false) f('Forbidden browser-native behavior: '.$x);
foreach(['ezscore:lyrics-history-saved','ezscore:lyrics-history-restored'] as $x) if(strpos($hist,$x)===false) f('Dirty reset event missing: '.$x);
foreach(['R38.13b: time-signature agnostic continuous projection.','R38.13c: restore chord lane runtime declaration'] as $x) if(strpos($lab,$x)===false) f('Harmonic ribbon regression: '.$x);
foreach(['data-lyrics-ovh','Chercher les paroles','Extraire les paroles','Analyser les paroles'] as $x) if(strpos($template,$x)===false) f('LyricsLab action regression: '.$x);
echo "R38_16J_MANUAL_SAVE_DIRTY_GUARD_CONTRACT_OK".PHP_EOL;
