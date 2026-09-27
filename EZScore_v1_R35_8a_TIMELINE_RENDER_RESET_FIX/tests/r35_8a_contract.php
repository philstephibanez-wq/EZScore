<?php
declare(strict_types=1);
$root=$argv[1]??dirname(__DIR__,2);
$analysis=(string)file_get_contents($root.'/analysis/chord_timeline_analysis.py');
if(substr_count($analysis,'extend_beats_to_zero(')<2) throw new RuntimeException('extend_beats_to_zero defini mais pas appele');
if(!str_contains($analysis,'beat_times,prepended_count=extend_beats_to_zero')) throw new RuntimeException('timeline t=0 non branchee');
$css=(string)file_get_contents($root.'/public/assets/css/chordslab.css');
foreach(['content:"["',"content:'['",'content:"]"',"content:']'"] as $bad){ if(str_contains($css,$bad)) throw new RuntimeException('crochet CSS encore injecte: '.$bad); }
if(!str_contains($css,'R35.8a framed cells: no square brackets')) throw new RuntimeException('override CSS absent');
$svc=(string)file_get_contents($root.'/src/Service/ChordTimelineResultService.php');
if(str_contains($svc,'$overrides')) throw new RuntimeException('reancrage des overrides encore actif');
if(!str_contains($svc,'fresh harmonic analysis is authoritative')) throw new RuntimeException('semantique reanalyse autoritative absente');
$twig=(string)file_get_contents($root.'/templates/song/chordslab.html.twig');
if(!str_contains($twig,'Les corrections manuelles de l’ancienne analyse seront supprimées')) throw new RuntimeException('texte reanalyse non corrige');
if(!str_contains($twig,'20260928r35_8a')) throw new RuntimeException('cache bust R35.8a absent');
echo "R35_8A_CONTRACT_OK\n";
