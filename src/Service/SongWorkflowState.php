<?php

declare(strict_types=1);
namespace App\Service;
use App\Domain\Song\Song;
use App\Domain\Song\SongStatus;
use App\Domain\Song\SongTimelineEvent;
use App\Domain\Song\SongTimelineEventRepository;
final class SongWorkflowState
{
    public function __construct(private readonly SongStemStorage $stems, private readonly SongTimelineEventRepository $timeline) {}
    public function forSong(Song $song): array
    {
        $imported=(bool)($song->getAudioStoragePath() && $song->getAudioSha256());
        $stemsReady=$imported && $this->stems->hasCompleteStems($song);
        $chordsReady=$stemsReady && count($this->timeline->findChordEvents($song))>0;
        $lyricsReady=$chordsReady && count($this->timeline->findForSongAndType($song,SongTimelineEvent::TYPE_LYRIC))>0;
        $published=$lyricsReady && $song->getStatus()===SongStatus::Published;
        return ['imported'=>$imported,'stems_ready'=>$stemsReady,'chords_ready'=>$chordsReady,'lyrics_ready'=>$lyricsReady,'published'=>$published,'can_stems'=>$imported,'can_chords'=>$stemsReady,'can_lyrics'=>$chordsReady,'can_publish'=>$lyricsReady,'next'=>!$imported?'import':(!$stemsReady?'stems':(!$chordsReady?'chords':(!$lyricsReady?'lyrics':(!$published?'publication':'done'))))];
    }
}
