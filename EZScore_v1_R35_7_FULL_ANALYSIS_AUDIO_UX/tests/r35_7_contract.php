<?php
declare(strict_types=1);
$root=$argv[1]??dirname(__DIR__,2);
$checks=[
'templates/base.html.twig'=>['data-ez-confirm-modal','ez-modal.js','ez-modal.css'],
'templates/song/edit.html.twig'=>['data-ez-confirm'],
'templates/song/chordslab.html.twig'=>['name="filter_noise"','Filtrer applaudissements / foule'],
'src/Controller/SongLabController.php'=>["getBoolean('filter_noise')"],
'src/Service/SongChordJobService.php'=>['bool $filterNoise = false',"'filter_noise' => $filterNoise"],
'worker_app/ezscore_analysis_worker.pyw'=>['--filter-noise','request.get("filter_noise")'],
'analysis/chord_timeline_analysis.py'=>['suppress_crowd_noise','extend_beats_to_zero','labels.append(".")','guitar_accompaniment_from_full_harmony','--filter-noise'],
'public/assets/js/ez-modal.js'=>['data-ez-confirm','requestSubmit'],
'public/assets/js/audio/ezscore-audio-engine.js'=>["media.preload = 'auto'",'warmUp(options = {})','_ensureTrackReady(track)'],
];
foreach($checks as $rel=>$tokens){$p=$root.DIRECTORY_SEPARATOR.str_replace('/',DIRECTORY_SEPARATOR,$rel);if(!is_file($p))throw new RuntimeException("Fichier absent: $rel");$s=(string)file_get_contents($p);foreach($tokens as $t)if(!str_contains($s,$t))throw new RuntimeException("$rel token absent: $t");}
$off=[];foreach([$root.'/templates',$root.'/public/assets/js'] as $base){if(!is_dir($base))continue;$it=new RecursiveIteratorIterator(new RecursiveDirectoryIterator($base,FilesystemIterator::SKIP_DOTS));foreach($it as $f){if(!$f->isFile()||!in_array(strtolower($f->getExtension()),['twig','js'],true))continue;$s=(string)file_get_contents($f->getPathname());if(preg_match('/(?<![A-Za-z0-9_])(confirm|alert)\s*\(/',$s))$off[]=$f->getPathname();}}
if($off)throw new RuntimeException('Popup navigateur restante: '.implode(', ',$off));
echo "R35_7_CONTRACT_OK\n";
