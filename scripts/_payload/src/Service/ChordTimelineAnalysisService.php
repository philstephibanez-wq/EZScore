<?php

declare(strict_types=1);

namespace App\Service;

use App\Domain\Song\Song;
use Symfony\Component\DependencyInjection\Attribute\Autowire;

final class ChordTimelineAnalysisService
{
    public function __construct(
        private readonly SongStemStorage $storage,
        #[Autowire('%kernel.project_dir%')]
        private readonly string $projectDir,
    ) {}

    /** @return array<string,mixed> */
    public function analyze(Song $song): array
    {
        $script=$this->projectDir.DIRECTORY_SEPARATOR.'analysis'.DIRECTORY_SEPARATOR.'chord_timeline_analysis.py';
        $audio=$this->storage->sourcePath($song);
        if (!is_file($script)) throw new \RuntimeException('Chord analysis script is missing.');
        if (!is_file($audio)) throw new \RuntimeException('Song source audio is missing.');

        $command=[
            $this->pythonExecutable(),$script,
            '--audio',$audio,
            '--level',$song->getChordAnalysisLevel(),
            '--time-signature',$song->getTimeSignature(),
        ];

        foreach (['bass','guitar','piano','other'] as $name) {
            $path=$this->storage->stemPath($song,$name);
            if (is_string($path) && is_file($path)) {
                $command[]='--stem';
                $command[]=$path;
            }
        }

        $drums=$this->storage->stemPath($song,'drums');
        if (is_string($drums) && is_file($drums)) {
            $command[]='--drums';
            $command[]=$drums;
        }

        $process=proc_open($command,[0=>['pipe','r'],1=>['pipe','w'],2=>['pipe','w']],$pipes,$this->projectDir);
        if (!is_resource($process)) throw new \RuntimeException('Unable to start chord analysis.');
        fclose($pipes[0]);
        $stdout=stream_get_contents($pipes[1]); fclose($pipes[1]);
        $stderr=stream_get_contents($pipes[2]); fclose($pipes[2]);
        $exit=proc_close($process);
        $payload=json_decode(trim((string)$stdout),true);
        if ($exit!==0 || !is_array($payload) || ($payload['ok']??false)!==true) {
            $error=is_array($payload)?trim((string)($payload['error']??'')):'';
            $detail=$error!==''?$error:trim((string)$stderr);
            throw new \RuntimeException($detail!==''?$detail:'Chord analysis failed.');
        }
        return $payload;
    }

    private function pythonExecutable(): string
    {
        $windows=$this->projectDir.DIRECTORY_SEPARATOR.'.venv-py313'.DIRECTORY_SEPARATOR.'Scripts'.DIRECTORY_SEPARATOR.'python.exe';
        if (is_file($windows)) return $windows;
        $unix=$this->projectDir.DIRECTORY_SEPARATOR.'.venv-py313'.DIRECTORY_SEPARATOR.'bin'.DIRECTORY_SEPARATOR.'python';
        return is_file($unix)?$unix:'python';
    }
}
