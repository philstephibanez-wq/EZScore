<?php
declare(strict_types=1);
$root=$argv[1]??dirname(__DIR__,2);

$analysis=(string)file_get_contents($root.'/analysis/chord_timeline_analysis.py');
if(!str_contains($analysis,'return i//bpm,i%bpm')){
    throw new RuntimeException('Mesure 1 encore partielle / phase appliquée à l’indexation');
}

$twig=(string)file_get_contents($root.'/templates/song/chordslab.html.twig');
if(str_contains($twig,'data-chord-reset-dialog')){
    throw new RuntimeException('Ancienne popup reset encore présente dans le DOM');
}
if(!str_contains($twig,'data-ez-confirm="Réinitialiser les accords ?')){
    throw new RuntimeException('Confirmation EZScore ciblée du reset absente');
}
if(!str_contains($twig,'20260928r35_10')){
    throw new RuntimeException('Cache bust R35.10 absent');
}

$js=(string)file_get_contents($root.'/public/assets/js/chordslab-r33-2.js');
if(str_contains($js,'resetDialog') || str_contains($js,'resetConfirm')){
    throw new RuntimeException('Ancienne mécanique de popup reset encore active');
}

echo "R35_10_CONTRACT_OK\n";
