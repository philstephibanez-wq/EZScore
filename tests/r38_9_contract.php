<?php
$root=$argv[1]??dirname(__DIR__);
$checks=[
['analysis/lyrics_timeline_analysis.py','_r389_legacy_align'],
['analysis/lyrics_timeline_analysis.py','acoustic_trigger_global_offset'],
['analysis/lyrics_timeline_analysis.py','timeline_offset_ms'],
['analysis/lyrics_timeline_analysis.py','align_provided_text(provided, words, vocal_onset_ms)'],
['public/assets/js/lyricslab-r37.js','Analyse des paroles en échec. Voir le journal du Worker.'],
['templates/song/lyricslab.html.twig','lyricslab-r37.js?v=20260928r38_9'],
];
foreach($checks as [$rel,$tok]){
 $p=rtrim($root,"\\/").DIRECTORY_SEPARATOR.str_replace('/',DIRECTORY_SEPARATOR,$rel);
 if(!is_file($p)){fwrite(STDERR,"MISSING FILE $rel\n");exit(1);}
 $t=file_get_contents($p);
 if(strpos($t,$tok)===false){fwrite(STDERR,"MISSING TOKEN $tok IN $rel\n");exit(2);}
}
echo "R38_9_CONTRACT_OK\n";
