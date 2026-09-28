<?php
declare(strict_types=1);
namespace App\Service;
use App\Domain\Song\Song;
use App\Domain\Song\SongTimelineEvent;
use App\Domain\Song\SongTimelineEventRepository;
use Doctrine\ORM\EntityManagerInterface;

final class LyricsTimelineResultService
{
    public function __construct(private readonly SongTimelineEventRepository $timeline,private readonly EntityManagerInterface $em){}
    public function apply(Song $song,array $result): array
    {
        foreach($this->timeline->findForSongAndType($song,SongTimelineEvent::TYPE_LYRIC) as $old)$this->em->remove($old);
        $this->em->flush();
        $beats=$this->timeline->findBeatEvents($song);
        $rows=array_map(static fn(SongTimelineEvent $b)=>['start'=>$b->getStartMs(),'measure'=>$b->getMeasureIndex(),'beat'=>$b->getBeatIndex()],$beats);
        $count=0;
        foreach(($result['words']??[]) as $word){
            if(!is_array($word))continue;
            $start=max(0,(int)($word['start_ms']??0));$end=max($start,(int)($word['end_ms']??$start));$text=trim((string)($word['text']??''));
            if($text==='')continue;
            $measure=null;$beat=null;
            foreach($rows as $row){if($row['start']>$start)break;$measure=$row['measure'];$beat=$row['beat'];}
            $event=(new SongTimelineEvent($song,SongTimelineEvent::TYPE_LYRIC,$start))->setEndMs($end)->setPosition($measure,$beat,null)->setOriginalValue($text)->setPayload([
                'line_break_after'=>(bool)($word['line_break_after']??false),
                'confidence'=>isset($word['confidence'])?(float)$word['confidence']:null,
                'analysis_version'=>(string)($result['version']??'r36.0'),
            ]);
            $this->em->persist($event);++$count;
        }
        $this->em->flush();
        return ['schema_version'=>'ezscore.lyrics.r36.0','words'=>$count,'language'=>$result['language']??'fr'];
    }
}
