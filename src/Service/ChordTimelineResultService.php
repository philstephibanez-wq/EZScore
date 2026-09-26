<?php
declare(strict_types=1);
namespace App\Service;

use App\Domain\Song\Song;
use App\Domain\Song\SongTimelineEvent;
use App\Domain\Song\SongTimelineEventRepository;
use Doctrine\ORM\EntityManagerInterface;

final class ChordTimelineResultService
{
    public function __construct(
        private readonly SongTimelineEventRepository $timeline,
        private readonly EntityManagerInterface $em,
    ) {}

    public function apply(Song $song, array $result): array
    {
        $overrides=[];
        foreach ($this->timeline->findChordEvents($song) as $existing) {
            if ($existing->getOverrideValue()!==null) {
                $key=($existing->getMeasureIndex()??-1).':'.($existing->getBeatIndex()??-1);
                $overrides[$key]=$existing->getOverrideValue();
            }
        }

        $this->timeline->deleteMusicalAnalysisForSong($song);

        foreach (($result['beats']??[]) as $beat) {
            if (!is_array($beat)) continue;
            $event=(new SongTimelineEvent($song,SongTimelineEvent::TYPE_BEAT,max(0,(int)($beat['start_ms']??0))))
                ->setPosition(
                    isset($beat['measure_index'])?(int)$beat['measure_index']:null,
                    isset($beat['beat_index'])?(int)$beat['beat_index']:null,
                    isset($beat['subdivision_index'])?(int)$beat['subdivision_index']:null,
                );
            $this->em->persist($event);
        }

        foreach (($result['chords']??[]) as $chord) {
            if (!is_array($chord)) continue;
            $measure=isset($chord['measure_index'])?(int)$chord['measure_index']:null;
            $beat=isset($chord['beat_index'])?(int)$chord['beat_index']:null;
            $event=(new SongTimelineEvent($song,SongTimelineEvent::TYPE_CHORD,max(0,(int)($chord['start_ms']??0))))
                ->setPosition($measure,$beat,isset($chord['subdivision_index'])?(int)$chord['subdivision_index']:null)
                ->setOriginalValue(trim((string)($chord['chord']??'.')))
                ->setPayload([
                    'confidence'=>isset($chord['confidence'])?(float)$chord['confidence']:null,
                    'analysis_level'=>$song->getChordAnalysisLevel(),
                    'analysis_version'=>(string)($result['version']??'r33.2'),
                    'downbeat_phase'=>$result['downbeat_phase']??null,
                ]);
            $key=($measure??-1).':'.($beat??-1);
            if (isset($overrides[$key])) $event->setOverrideValue($overrides[$key]);
            $this->em->persist($event);
        }

        $key=trim((string)($result['key']??''));
        if ($key!=='') $song->setKeySignature($key);
        if ($song->getTimeSignature()==='auto') {
            $sig=trim((string)($result['time_signature']??''));
            if ($sig!=='') $song->setTimeSignature($sig);
        }
        $this->em->flush();

        return [
            'schema_version'=>'ezscore.chords.r33.2',
            'beats'=>count($result['beats']??[]),
            'chords'=>count($result['chords']??[]),
            'key'=>$result['key']??null,
            'time_signature'=>$result['time_signature']??null,
            'level'=>$result['level']??null,
            'downbeat_phase'=>$result['downbeat_phase']??0,
        ];
    }
}
