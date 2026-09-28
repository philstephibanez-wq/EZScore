<?php
declare(strict_types=1);
$root=$argv[1]??dirname(__DIR__,2);
$stems=(string)file_get_contents($root.'/public/assets/js/stems-mixer.js');
$lyrics=(string)file_get_contents($root.'/public/assets/js/lyricslab-r37.js');
$worker=(string)file_get_contents($root.'/worker_app/lyrics_worker_r37.py');
$twig=(string)file_get_contents($root.'/templates/song/lyricslab.html.twig');
foreach(["quickVolume: q('[data-chordslab-quick-volume]')","els.quickVolume?.addEventListener('input'","syncQuickVolume()","root.addEventListener('ezscore:request-seek'"] as $token){if(!str_contains($stems,$token))throw new RuntimeException('stems token absent: '.$token);} 
if(str_contains($stems,"event) => {\\n        const time="))throw new RuntimeException('literal escaped newlines still present');
foreach(['diagramStorageKey=',"localStorage.setItem(diagramStorageKey",'renderAt(s.start,true)'] as $token){if(!str_contains($lyrics,$token))throw new RuntimeException('lyrics ui token absent: '.$token);} 
foreach(['if mode=="align":','audio=paths.get("source")','audio_kind="source"','Audio Lyrics ({mode})'] as $token){if(!str_contains($worker,$token))throw new RuntimeException('worker token absent: '.$token);} 
if(!str_contains($twig,'stems-mixer.js?v=20260928r38_3'))throw new RuntimeException('stems cachebuster absent');
if(!str_contains($twig,'lyricslab-r37.js?v=20260928r38_3'))throw new RuntimeException('lyrics cachebuster absent');
echo "R38_3_CONTRACT_OK\n";
