<?php
declare(strict_types=1);

$root=$argv[1]??dirname(__DIR__,2);

$a=(string)file_get_contents($root.'/analysis/lyrics_timeline_analysis.py');
$j=(string)file_get_contents($root.'/public/assets/js/lyricslab-r37.js');
$t=(string)file_get_contents($root.'/templates/song/lyricslab.html.twig');

foreach([
    'Declarative sections: no whitelist and no implicit sections.',
    'def _first_acoustic_anchor(',
    'best_consecutive >= 2',
    'Align only from the first real acoustic phrase onward.',
    'if sim < 0.82 or conf < 0.30:',
] as $token){
    if(!str_contains($a,$token)){
        throw new RuntimeException('analysis token absent: '.$token);
    }
}

foreach([
    'function declaredSections(text)',
    "m=/^\\[([^\\[\\]\\r\\n]{1,120})\\]$/",
    "m=/^([^\\r\\n:]{1,120}):$/",
    'function buildSections()',
    'section.start=0',
    'nextBeatAtOrAfter(previousEnd)',
    'function renderSectionNav()',
] as $token){
    if(!str_contains($j,$token)){
        throw new RuntimeException('section token absent: '.$token);
    }
}

// Hard regression guards.
if(str_contains($a, "if normalise_section_type(candidate)!='section'")){
    throw new RuntimeException('section whitelist still active');
}
if(str_contains($j, "title=panel?.querySelector('.chordslab-prompter-head h2'),sections=[]")){
    throw new RuntimeException('sections still sourced only from lyric events');
}

// Do not regress progress again.
foreach([
    'data-lyrics-progress',
    'data-lyrics-progress-text',
    'data-lyrics-progress-percent',
] as $token){
    if(!str_contains($t,$token)){
        throw new RuntimeException('progress markup absent: '.$token);
    }
}
if(!str_contains($j,'function pollLyricsProgress()')){
    throw new RuntimeException('progress polling absent from current R38.3 baseline');
}

if(!str_contains($t,'lyricslab-r37.js?v=20260928r38_4')){
    throw new RuntimeException('R38.4 cachebuster absent');
}

echo "R38_4_CONTRACT_OK\n";
