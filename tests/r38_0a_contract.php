<?php
declare(strict_types=1);
$root=$argv[1]??dirname(__DIR__,2);
$a=(string)file_get_contents($root.'/analysis/lyrics_timeline_analysis.py');
$s=(string)file_get_contents($root.'/src/Service/LyricsTimelineResultService.php');
$j=(string)file_get_contents($root.'/public/assets/js/lyricslab-r37.js');
foreach(['def normalise_section_type(label: str)','def section_label(line: str)','def is_chord_line(line: str)',"'section_label':current_section","'section_type':current_section_type"] as $t){
    if(!str_contains(str_replace(' ','',$a),str_replace(' ','',$t))) throw new RuntimeException("analysis token absent: ".$t);
}
foreach(["'section_label'=>","'section_type'=>"] as $t){
    if(!str_contains($s,$t)) throw new RuntimeException("service token absent: ".$t);
}
foreach(['lyrics-simple-chord','lyrics-simple-section','data-lyrics-diagram-toggle','ezscore:audio-timeupdate'] as $t){
    if(!str_contains($j,$t)) throw new RuntimeException("js token absent: ".$t);
}
echo "R38_0A_CONTRACT_OK\n";
