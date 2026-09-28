<?php
$root=$argv[1]??'H:\\EZScore_v1';
$js=file_get_contents($root.'/public/assets/js/lyricslab-r37.js');$py=file_get_contents($root.'/analysis/lyrics_timeline_analysis.py');$twig=file_get_contents($root.'/templates/song/lyricslab.html.twig');
foreach(['R38.13 canonical ChordsLab projection','function buildCanonicalProjection(inputBeats)',"const beatsPerMeasure=Math.max(1,Number(timeSignature.split('/')[0])||4);",'display_beat_index:slot'] as $n){if(strpos($js,$n)===false){fwrite(STDERR,"Missing JS: $n\n");exit(1);}}
if(strpos($js,'const displayStarts=words.map')!==false||strpos($js,'dataDisplayStart')!==false){fwrite(STDERR,"Rejected display offset detected\n");exit(1);}
foreach(['def _r3813_syllabify_french','def _r3813_attach_syllables','syllabic_acoustic_resample',"'syllables': payload_syllables","'version': 'r38.13-canonical-grid-syllabic-timeline'"] as $n){if(strpos($py,$n)===false){fwrite(STDERR,"Missing PY: $n\n");exit(1);}}
if(strpos($twig,'20260928r38_13')===false){fwrite(STDERR,"Missing cache buster\n");exit(1);}echo "R38_13_CONTRACT_OK\n";
