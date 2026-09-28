<?php
declare(strict_types=1);
$root=$argv[1]??dirname(__DIR__,2);
$checks=[
 'src/Domain/Song/Song.php'=>['lyricsSourceText','getLyricsSourceText','setLyricsSourceText'],
 'src/Controller/SongLabController.php'=>['app_song_lyricslab_source','app_song_lyricslab_analyze','app_song_lyricslab_status','app_song_lyricslab_word',"render('song/lyricslab.html.twig'"],
 'src/Controller/AnalysisDesktopController.php'=>['SongLyricsJobService','LyricsTimelineStorage','LyricsTimelineResultService',"'lyrics_file' =>"],
 'src/Service/SongLyricsJobService.php'=>["public const KIND='lyrics'"],
 'src/Service/LyricsTimelineResultService.php'=>['TYPE_LYRIC','line_break_after'],
 'templates/song/lyricslab.html.twig'=>['data-lyrics-source','Analyser les paroles','data-lyricslab','data-stem-mixer'],
 'public/assets/js/lyricslab-r36.js'=>['ezscore:audio-timeupdate','lyrics-word','data-lyrics-source'],
 'analysis/lyrics_timeline_analysis.py'=>['word_timestamps=True','CUDA required for LyricsLab','provided-text-whisper-anchor'],
 'worker_app/ezscore_analysis_worker.pyw'=>['_run_lyrics_job','kind") == "lyrics"'],
 'migrations/Version20260928030000.php'=>['lyrics_source_text'],
];
foreach($checks as $rel=>$tokens){
 $p=$root.DIRECTORY_SEPARATOR.str_replace('/',DIRECTORY_SEPARATOR,$rel);
 if(!is_file($p))throw new RuntimeException("Fichier absent: $rel");
 $s=(string)file_get_contents($p);
 foreach($tokens as $t)if(!str_contains($s,$t))throw new RuntimeException("$rel token absent: $t");
}
echo "R36_0_CONTRACT_OK\n";
