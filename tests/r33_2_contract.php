<?php
declare(strict_types=1);

$root=dirname(__DIR__);
$a=file_get_contents($root.'/analysis/chord_timeline_analysis.py');
$j=file_get_contents($root.'/src/Service/SongChordJobService.php');
$s=file_get_contents($root.'/src/Service/ChordTimelineStorage.php');
$r=file_get_contents($root.'/src/Service/ChordTimelineResultService.php');
$ui=file_get_contents($root.'/public/assets/js/chordslab-r33-2.js');
$p=file_get_contents($root.'/scripts/apply_r33_2_async_progress.py');

$checks=[
 'progress stages'=>str_contains($a,'progress_file')&&str_contains($a,'"smoothing"'),
 'downbeat phase'=>str_contains($a,'downbeat_phase')&&str_contains($a,'canonical_position')===false ? str_contains($a,'def pos(') : true,
 'beginner smoothing'=>str_contains($a,'"beginner":.155')||str_contains($a,'"beginner": 0.155'),
 'intermediate threshold'=>str_contains($a,'margin<.105')||str_contains($a,'margin < 0.105'),
 'job kind'=>str_contains($j,"KIND = 'chords'"),
 'job latest'=>str_contains($j,'latest(Song $song)'),
 'result storage'=>str_contains($s,'resultPath'),
 'timeline persistence'=>str_contains($r,'deleteMusicalAnalysisForSong'),
 'worker chords'=>str_contains($p,'_run_chord_job'),
 'worker label'=>str_contains($p,'STEMS + CHORDS'),
 'async status endpoint'=>str_contains($p,'app_song_chordslab_status'),
 'progress UI'=>str_contains($p,'data-chord-analysis-progress'),
 'custom reset modal'=>str_contains($ui,'data-chord-reset-dialog'),
 'quick volume'=>str_contains($ui,'data-chordslab-quick-volume'),
 'level explanations'=>str_contains($ui,'levelDescriptions'),
 'canonical renderer'=>str_contains($p,'canonicalSignature'),
 'CDC'=>str_contains($p,'CAHIER_DES_CHARGES.md'),
 'recette'=>str_contains($p,'recette.md'),
 'no migration'=>!str_contains($p,'doctrine:migrations'),
];
foreach($checks as $label=>$ok){
 if(!$ok){fwrite(STDERR,"FAIL: $label\n");exit(1);}
 echo "OK: $label\n";
}
echo "\n".count($checks)." R33.2 checks passed.\n";
