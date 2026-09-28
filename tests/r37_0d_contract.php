<?php
declare(strict_types=1);

$root=$argv[1]??dirname(__DIR__,2);
$path=$root.'/worker_app/ezscore_analysis_worker.pyw';
if(!is_file($path)) throw new RuntimeException('Worker absent');
$s=(string)file_get_contents($path);

$tokens=[
    'self._run_chord_job(job)',
    'def _read_progress(',
    'if job.get("kind") == "lyrics":',
    'from lyrics_worker_r37 import run_lyrics_job',
    'run_lyrics_job(self, job)',
];

foreach($tokens as $token){
    if(!str_contains($s,$token)){
        throw new RuntimeException("Token absent: ".$token);
    }
}

echo "R37_0D_CONTRACT_OK\n";
