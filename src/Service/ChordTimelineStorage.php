<?php
declare(strict_types=1);
namespace App\Service;

use App\Domain\Song\Song;
use Symfony\Component\DependencyInjection\Attribute\Autowire;

final class ChordTimelineStorage
{
    public function __construct(
        private readonly SongStemStorage $stems,
        #[Autowire('%kernel.project_dir%')] private readonly string $projectDir,
    ) {}

    public function storageRoot(Song $song): string
    {
        $hash=(string)$song->getAudioSha256();
        if (!preg_match('/^[a-f0-9]{64}$/',$hash)) throw new \RuntimeException('Song has no valid audio hash.');
        $path=$this->projectDir.DIRECTORY_SEPARATOR.'var'.DIRECTORY_SEPARATOR.'storage'.DIRECTORY_SEPARATOR.'chords'.DIRECTORY_SEPARATOR.'song-'.(int)$song->getId().DIRECTORY_SEPARATOR.$hash;
        if (!is_dir($path) && !@mkdir($path,0775,true) && !is_dir($path)) throw new \RuntimeException('Unable to create ChordsLab storage.');
        return $path;
    }

    public function progressPath(Song $song): string { return $this->storageRoot($song).DIRECTORY_SEPARATOR.'progress.json'; }
    public function resultPath(Song $song): string { return $this->storageRoot($song).DIRECTORY_SEPARATOR.'result.json'; }
    public function sourcePath(Song $song): string { return $this->stems->sourcePath($song); }

    public function deleteForSong(Song $song): void
    {
        $dir=$this->projectDir.DIRECTORY_SEPARATOR.'var'.DIRECTORY_SEPARATOR.'storage'.DIRECTORY_SEPARATOR.'chords'.DIRECTORY_SEPARATOR.'song-'.(int)$song->getId();
        if (!is_dir($dir)) return;
        $it=new \RecursiveIteratorIterator(new \RecursiveDirectoryIterator($dir, \FilesystemIterator::SKIP_DOTS), \RecursiveIteratorIterator::CHILD_FIRST);
        foreach ($it as $item) { if ($item->isDir()) @rmdir($item->getPathname()); else @unlink($item->getPathname()); }
        @rmdir($dir);
    }

    public function readResult(Song $song): array
    {
        $path=$this->resultPath($song);
        if (!is_file($path)) throw new \RuntimeException('Chord analysis result is missing.');
        $payload=json_decode((string)file_get_contents($path),true);
        if (!is_array($payload) || ($payload['ok']??false)!==true) throw new \RuntimeException('Chord analysis result is invalid.');
        return $payload;
    }
}
