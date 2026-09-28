<?php
$root=$argv[1]??dirname(__DIR__);
$checks=[
['analysis/lyrics_timeline_analysis.py','detect_first_vocal_onset'],
['analysis/lyrics_timeline_analysis.py','_r388_fill_unmatched'],
['analysis/lyrics_timeline_analysis.py','first_vocal_onset_ms'],
['analysis/lyrics_timeline_analysis.py','--vocal-audio'],
['worker_app/lyrics_worker_r37.py','--vocal-audio'],
['templates/song/components/_lab_song_card.html.twig','data-lab-tempo'],
['templates/song/chordslab.html.twig','_lab_song_card.html.twig'],
['templates/song/lyricslab.html.twig','_lab_song_card.html.twig'],
['templates/song/lyricslab.html.twig','data-song-id="{{ song.id }}"'],
['public/assets/js/lyricslab-r37.js','root.dataset.songId'],
['public/assets/js/lab-song-card.js','Tempo = ${bpm}'],
];
foreach($checks as [$rel,$tok]){
 $p=rtrim($root,"\\/").DIRECTORY_SEPARATOR.str_replace('/',DIRECTORY_SEPARATOR,$rel);
 if(!is_file($p)){fwrite(STDERR,"MISSING FILE $rel\n");exit(1);}
 $t=file_get_contents($p);
 if(strpos($t,$tok)===false){fwrite(STDERR,"MISSING TOKEN $tok IN $rel\n");exit(2);}
}
echo "R38_8_CONTRACT_OK\n";
