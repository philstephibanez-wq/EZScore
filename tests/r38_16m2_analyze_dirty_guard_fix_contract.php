<?php
declare(strict_types=1);
$root=$argv[1]??'H:\\EZScore_v1';
function bad(string $m):never{fwrite(STDERR,$m.PHP_EOL);exit(1);}
$js=@file_get_contents($root.'/public/assets/js/lyrics-dirty-guard-r38-16j.js');
$twig=@file_get_contents($root.'/templates/song/lyricslab.html.twig');
if($js===false||$twig===false)bad('Missing files');
if(strpos($js,"form.id==='lyrics-analyze-form'")===false)bad('Analyze form is still blocked by dirty guard');
if(strpos($twig,'lyrics-dirty-guard-r38-16j.js?v=20260929r38_16m2')===false)bad('Asset cache-bust missing');
if(strpos($twig,'id="lyrics-analyze-form"')===false)bad('Analyze form id missing');
if(strpos($twig,'form="lyrics-analyze-form"')===false)bad('Textarea is not associated with analyze form');
echo "R38_16M2_ANALYZE_DIRTY_GUARD_FIX_CONTRACT_OK".PHP_EOL;
