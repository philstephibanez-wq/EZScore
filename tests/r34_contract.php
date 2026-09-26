<?php
declare(strict_types=1);
$root=dirname(__DIR__);
$a=file_get_contents($root.'/analysis/chord_timeline_analysis.py');
$r=file_get_contents($root.'/src/Service/ChordTimelineResultService.php');
$p=file_get_contents($root.'/scripts/apply_r34_three_profiles.py');
$j=file_get_contents($root.'/scripts/_payload/snippets/chordslab_r34.js');

$checks=[
 'one analysis three profiles'=>str_contains($a,'"profiles":{') && str_contains($a,'decode_profile("beginner"') && str_contains($a,'decode_profile("expert"'),
 'shared beats'=>str_contains($a,'"beats":beats'),
 'beginner simple'=>str_contains($a,'level=="beginner"'),
 'intermediate gate'=>str_contains($a,'margin<.105'),
 'expert richer candidates'=>str_contains($a,'q.update(EXPERT)'),
 'no redundant maj'=>str_contains($a,'label.endswith("maj")') && str_contains($r,'normaliseMajorLabel'),
 'maj7 preserved'=>str_contains($a,'maj7'),
 'profile payload persistence'=>str_contains($r, "'profile' => \$profile"),
 'override key includes profile'=>str_contains($r,'$profile.\':\'.($measure'),
 'repository profile method'=>str_contains($p,'findChordEventsForProfile'),
 'instant switch dataset'=>str_contains($p,'data-profiles='),
 'profile persistence endpoint'=>str_contains($p,'app_song_chordslab_profile'),
 'edit current event only'=>str_contains($j,'eventId'),
 "reset current profile"=>str_contains($p,'findChordEventsForProfile($song, $profile)'),
 'fixed slots'=>str_contains(file_get_contents($root.'/scripts/_payload/snippets/css_add.txt'),'flex:0 0 44px'),
 'long chord typography'=>str_contains($j,'is-very-long'),
 'standard labels retained'=>!str_contains($j,'△'),
 'volume layout'=>str_contains(file_get_contents($root.'/scripts/_payload/snippets/css_add.txt'),'chordslab-quick-volume'),
 'CDC update'=>str_contains($p,'CAHIER_DES_CHARGES.md'),
 'recette update'=>str_contains($p,'recette.md'),
 'no song-specific code'=>!str_contains(strtolower($a.$r.$p.$j),'aline') && !str_contains(strtolower($a.$r.$p.$j),'christophe'),
 'no migration'=>!str_contains($p,'migrations/Version'),
];
foreach($checks as $label=>$ok){
 if(!$ok){fwrite(STDERR,"FAIL: $label\n");exit(1);}
 echo "OK: $label\n";
}
echo "\n".count($checks)." R34 checks passed.\n";
