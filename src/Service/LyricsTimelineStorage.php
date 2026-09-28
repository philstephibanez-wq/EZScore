<?php
declare(strict_types=1);
namespace App\Service;
use App\Domain\Song\Song;
use Symfony\Component\DependencyInjection\Attribute\Autowire;

final class LyricsTimelineStorage
{
    public function __construct(
        private readonly SongStemStorage $stems,
        #[Autowire('%kernel.project_dir%')] private readonly string $projectDir,
    ) {}

    public function storageRoot(Song $song): string
    {
        $hash=(string)$song->getAudioSha256();
        if(!preg_match('/^[a-f0-9]{64}$/',$hash))throw new \RuntimeException('Song has no valid audio hash.');
        $path=$this->projectDir.DIRECTORY_SEPARATOR.'var'.DIRECTORY_SEPARATOR.'storage'.DIRECTORY_SEPARATOR.'lyrics'.DIRECTORY_SEPARATOR.'song-'.(int)$song->getId().DIRECTORY_SEPARATOR.$hash;
        if(!is_dir($path)&&!@mkdir($path,0775,true)&&!is_dir($path))throw new \RuntimeException('Unable to create LyricsLab storage.');
        return $path;
    }
    public function progressPath(Song $song): string{return $this->storageRoot($song).DIRECTORY_SEPARATOR.'progress.json';}
    public function resultPath(Song $song): string{return $this->storageRoot($song).DIRECTORY_SEPARATOR.'result.json';}
    public function lyricsPath(Song $song): string{return $this->storageRoot($song).DIRECTORY_SEPARATOR.'lyrics.txt';}
    public function sourcePath(Song $song): string{return $this->stems->sourcePath($song);}
    public function writeLyrics(Song $song,string $lyrics): string{$p=$this->lyricsPath($song);file_put_contents($p,$lyrics);return $p;}
    public function readResult(Song $song): array
    {
        $p=$this->resultPath($song);
        if(!is_file($p))throw new \RuntimeException('Lyrics analysis result is missing.');
        $data=json_decode((string)file_get_contents($p),true);
        if(!is_array($data)||($data['ok']??false)!==true)throw new \RuntimeException('Lyrics analysis result is invalid.');
        return $data;
    }
}
