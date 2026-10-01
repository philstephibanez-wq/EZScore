<?php
declare(strict_types=1);
$root=dirname(__DIR__);
$a=file_get_contents($root.'/analysis/chord_timeline_analysis.py');
$s=file_get_contents($root.'/src/Service/ChordTimelineAnalysisService.php');
$j=file_get_contents($root.'/public/assets/js/chordslab.js');
$p=file_get_contents($root.'/scripts/apply_r33_editable_chord_prompter.py');
$r=file_get_contents($root.'/scripts/_payload/snippets/controller_route.txt');
$checks=[
 'beat detection'=>str_contains($a,'beat_track'),
 'harmonic chroma'=>str_contains($a,'chroma_cqt'),
 'key detection'=>str_contains($a,'detect_key'),
 'three levels'=>str_contains($a,'"beginner"')&&str_contains($a,'"expert"'),
 'project venv'=>str_contains($s,'.venv-py313'),
 'source audio'=>str_contains($s,'sourcePath($song)'),
 'analysis endpoint'=>str_contains($r,'app_song_chordslab_analyze'),
 'timeline reset'=>str_contains($p,'deleteMusicalAnalysisForSong'),
 'override preservation'=>str_contains($r,'$overrides'),
 'guitar label'=>str_contains($p,'chordslab.guitar_chords'),
 'inline editing'=>str_contains($j,'editEvent'),
 'beat highlight'=>str_contains($j,'data-beat-seq'),
 'time-signature projection'=>str_contains($j,'Math.floor(seq/sig.num)'),
 'capo transform'=>str_contains($j,'pc-capo'),
 'mobile actions'=>str_contains(file_get_contents($root.'/scripts/_payload/snippets/css_add.txt'),'@media(max-width:640px)'),
 'no migration'=>!str_contains($p,'doctrine:migrations'),
];
foreach($checks as $label=>$ok){if(!$ok){fwrite(STDERR,"FAIL: $label\n");exit(1);}echo "OK: $label\n";}
echo "\n".count($checks)." R33 editable-prompter checks passed.\n";
