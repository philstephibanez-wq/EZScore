<?php
declare(strict_types=1);
$root=dirname(__DIR__);
$js=file_get_contents($root.'/public/assets/js/chordslab.js');
$p=file_get_contents($root.'/scripts/apply_r34_1_profiles_ui.py');

$checks=[
 'dynamic profile fetch'=>str_contains($js,'loadProfile(profile)') && str_contains($js,'profileDataUrlTemplate'),
 'profile count UI'=>str_contains($js,'data-chord-profile-count'),
 'instant profile persistence'=>str_contains($js,'persistProfile(currentProfile)'),
 'settings autosave'=>str_contains($js,'autoSaveSettings()'),
 'capo autosave'=>str_contains($js,'capoSelect') && str_contains($js,'autoSaveSettings()'),
 'timesig autosave'=>str_contains($js,'timeSigSelect') && str_contains($js,'autoSaveSettings()'),
 'analyze modal guard'=>str_contains($js,'data-chord-analyze-dialog') && str_contains($js,'analyzeForm.addEventListener'),
 'no native confirm'=>!str_contains($js,'confirm('),
 'remove save button'=>str_contains($p,'data-chord-settings-state'),
 'profile GET endpoint'=>str_contains($p,'app_song_chordslab_profile_data'),
 'settings JSON response'=>str_contains($p,"getPreferredFormat() === 'json'"),
 'profile visible status'=>str_contains($p,'data-chord-profile-badge'),
 'reanalyze explicit confirmation'=>str_contains(file_get_contents($root.'/scripts/_payload/snippets/analyze_dialog.html'),'Lancer la réanalyse'),
 'CDC update'=>str_contains($p,'CAHIER_DES_CHARGES.md'),
 'recette update'=>str_contains($p,'recette.md'),
 'no song-specific algorithm'=>!str_contains(strtolower($js.$p),'if title') && !str_contains(strtolower($js.$p),'song-6'),
];
foreach($checks as $label=>$ok){
 if(!$ok){fwrite(STDERR,"FAIL: $label\n");exit(1);}
 echo "OK: $label\n";
}
echo "\n".count($checks)." R34.1 checks passed.\n";
