<?php
$root=$argv[1]??dirname(__DIR__);
$checks=[
 ['analysis/lyrics_timeline_analysis.py','_r3810_sequential_mapping'],
 ['analysis/lyrics_timeline_analysis.py','acoustic_trigger'],
 ['analysis/lyrics_timeline_analysis.py','acoustic_resample'],
 ['analysis/lyrics_timeline_analysis.py','r38.10-sequential-variable-timeline'],
 ['public/assets/js/lyricslab-r37.js','const left=xBeat(i),next=i+1<beats.length?xBeat(i+1):left+spacing'],
 ['public/assets/js/lyricslab-r37.js','chordLane.style.transform=`translate3d(${x-rawMetric(lastTime)}px,0,0)`'],
 ['public/assets/js/lyricslab-r37.js','wordLane.style.transform=`translate3d(${x-visMetric(lastTime)}px,0,0)`'],
 ['public/assets/js/lyricslab-r37.js','lyrics-section-chip.current'],
 ['templates/song/lyricslab.html.twig','lyricslab-r37.js?v=20260928r38_10'],
];
foreach($checks as [$rel,$tok]){
 $p=rtrim($root,"\\/").DIRECTORY_SEPARATOR.str_replace('/',DIRECTORY_SEPARATOR,$rel);
 if(!is_file($p)){fwrite(STDERR,"MISSING FILE $rel\n");exit(1);}
 $t=file_get_contents($p);
 if(strpos($t,$tok)===false){fwrite(STDERR,"MISSING TOKEN $tok IN $rel\n");exit(2);}
}
echo "R38_10_CONTRACT_OK\n";
