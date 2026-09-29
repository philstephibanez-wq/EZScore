<?php
declare(strict_types=1);

$root=$argv[1]??'H:\\EZScore_v1';
function bad(string $m):never{fwrite(STDERR,$m.PHP_EOL);exit(1);}

$song=@file_get_contents($root.'/src/Domain/Song/Song.php');
$svc=@file_get_contents($root.'/src/Service/LyricsSourceHistoryService.php');
$ctl=@file_get_contents($root.'/src/Controller/LyricsHistoryController.php');
$mig=@file_get_contents($root.'/migrations/Version20260929080000.php');

if($song===false||$svc===false||$ctl===false||$mig===false)bad('Missing R38.16l2 files');

foreach(['lyrics_current_revision_id','getLyricsCurrentRevisionId()','setLyricsCurrentRevisionId(?int $revisionId)'] as $n)
    if(strpos($song,$n)===false)bad('Song missing '.$n);

$a=strpos($svc,'public function restore(');
$b=strpos($svc,'public function delete(',$a);
$r=substr($svc,$a,$b-$a);

foreach(['$song->setLyricsSourceText($target->getContent());','$song->setLyricsCurrentRevisionId($target->getId());','return $target;'] as $n)
    if(strpos($r,$n)===false)bad('Restore missing '.$n);

foreach(['saveVersion(','archiveCurrentIfChanged(','new LyricsSourceRevision('] as $n)
    if(strpos($r,$n)!==false)bad('Restore still creates duplicate: '.$n);

if(strpos($svc,'$song->getLyricsCurrentRevisionId() === $revision->getId()')===false)bad('Delete protection wrong');
if(strpos($ctl,'$currentRevisionId = $song->getLyricsCurrentRevisionId();')===false)bad('Controller current id wrong');
if(strpos($mig,'lyrics_current_revision_id')===false)bad('Migration missing');

echo "R38_16L2_RESTORE_EXACT_REVISION_CONTRACT_OK".PHP_EOL;
