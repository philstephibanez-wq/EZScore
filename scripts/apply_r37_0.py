#!/usr/bin/env python3
from pathlib import Path
import shutil
import sys

def die(message):
    raise SystemExit("R37.0 ABORT: "+message)

def rd(path):
    return path.read_text(encoding="utf-8-sig")

def wr(path,text):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(text,encoding="utf-8",newline="\n")

repo=Path(sys.argv[1] if len(sys.argv)>1 else ".").resolve()
bundle=Path(__file__).resolve().parents[1]

for rel in [
    "templates/song/components/_lab_song_card.html.twig",
    "templates/song/components/_timeline_stage.html.twig",
    "templates/song/components/_analysis_player.html.twig",
    "templates/song/lyricslab.html.twig",
    "public/assets/css/lyricslab-r37.css",
    "public/assets/js/lyricslab-r37.js",
    "worker_app/lyrics_worker_r37.py",
    "analysis/lyrics_timeline_analysis.py",
    "src/Service/SongLyricsJobService.php",
]:
    src=bundle/rel
    if not src.is_file():
        die("fichier bundle absent: "+rel)
    dst=repo/rel
    dst.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(src,dst)

p=repo/"templates/song/chordslab.html.twig"
if not p.is_file():
    die("templates/song/chordslab.html.twig absent")
s=rd(p)

song_card = '''<section class="panel chordslab-song-card">
    <div><span>{{ 'song.title'|trans }}</span><strong>{{ song.title }}</strong></div>
    <div><span>{{ 'song.artist'|trans }}</span><strong>{{ song.artist }}</strong></div>
    <div><span>{{ 'chordslab.key'|trans({}, 'chordslab') }}</span><strong>{{ song.keySignature ?: '—' }}</strong></div>
    <div><span>{{ 'song.time_signature'|trans }}</span><strong>{{ song.timeSignature }}</strong></div>
    <div><span>{{ 'song.capo'|trans }}</span><strong>{{ song.capo }}</strong></div>
</section>'''
song_include="{% include 'song/components/_lab_song_card.html.twig' with {song:song} %}"
if song_card in s:
    s=s.replace(song_card,song_include,1)
elif "_lab_song_card.html.twig" not in s:
    die("bloc song-card ChordsLab inattendu")

stage = '''        <div class="chordslab-stage">
            <div class="chord-diagram" data-chord-diagram hidden></div>
            <div class="chordslab-measures" data-chordslab-measures></div>
        </div>'''
stage_include = '''        {% include 'song/components/_timeline_stage.html.twig' with {
            mode: 'chords',
            show_diagram: true
        } %}'''
if stage in s:
    s=s.replace(stage,stage_include,1)
elif "_timeline_stage.html.twig" not in s:
    die("bloc timeline ChordsLab inattendu")

wr(p,s)

p=repo/"src/Controller/SongLabController.php"
if not p.is_file():
    die("src/Controller/SongLabController.php absent")
s=rd(p)

s=s.replace("$jobs->queue($song,$user);","$jobs->queue($song,$user,'align');",1)

if "app_song_lyricslab_extract" not in s:
    marker="#[Route('/lyrics/status', name: 'app_song_lyricslab_status', methods: ['GET'])]"
    if marker not in s:
        die("ancre lyrics/status introuvable")
    extract = r'''
#[Route('/lyrics/extract', name: 'app_song_lyricslab_extract', methods: ['POST'])]
public function extractLyrics(Song $song,Request $request,\App\Service\SongLyricsJobService $jobs): Response
{
    $user=$this->requireEditor($song);
    if(!$this->isCsrfTokenValid('song_lyricslab_extract_'.$song->getId(),(string)$request->request->get('_token')))throw $this->createAccessDeniedException();

    $jobs->queue($song,$user,'extract');

    return $this->redirectToRoute('app_song_lyricslab',[
        '_locale'=>$request->getLocale(),
        'id'=>$song->getId(),
    ]);
}

'''
    s=s.replace(marker,extract+marker,1)

old="return $this->json(['job_id'=>$job->getId(),'status'=>$job->getStatus()->value,'progress'=>$job->getProgress(),'error'=>$job->getErrorCode()]);"
new="return $this->json(['job_id'=>$job->getId(),'status'=>$job->getStatus()->value,'progress'=>$job->getProgress(),'error'=>$job->getErrorCode(),'mode'=>(string)($job->getRequestData()['mode']??'align')]);"
if old in s:
    s=s.replace(old,new,1)
elif "'mode'=>(string)($job->getRequestData()['mode']??'align')" not in s:
    die("retour lyrics status inattendu")

wr(p,s)

p=repo/"src/Controller/AnalysisDesktopController.php"
if not p.is_file():
    die("src/Controller/AnalysisDesktopController.php absent")
s=rd(p)

old = r'''        if ($job->getKind() === SongLyricsJobService::KIND) {
            try {
                $result=$this->lyricsStorage->readResult($job->getSong());
                $summary=$this->lyricsResults->apply($job->getSong(),$result);
                $this->lyricsJobs->complete($job,$summary);
            } catch (\Throwable $error) {
                $this->lyricsJobs->fail($job,$error->getMessage());
                return $this->json(['error'=>$error->getMessage()],Response::HTTP_CONFLICT);
            }
            return $this->json(['job_id'=>$job->getId(),'status'=>'completed','progress'=>100]);
        }'''
new = r'''        if ($job->getKind() === SongLyricsJobService::KIND) {
            try {
                $result=$this->lyricsStorage->readResult($job->getSong());
                $mode=(string)($job->getRequestData()['mode']??($result['mode']??'align'));

                if($mode==='extract'){
                    $text=trim((string)($result['text']??''));
                    if($text===''){
                        throw new \RuntimeException('lyrics_extract_empty');
                    }
                    $job->getSong()->setLyricsSourceText($text);
                    $this->em->flush();
                    $summary=[
                        'schema_version'=>'ezscore.lyrics.extract.r37',
                        'mode'=>'extract',
                        'characters'=>mb_strlen($text),
                        'recognized_words'=>(int)($result['recognized_words']??0),
                        'languages'=>$result['languages']??[],
                        'model'=>$result['model']??null,
                    ];
                }else{
                    $summary=$this->lyricsResults->apply($job->getSong(),$result);
                    $summary['mode']='align';
                    $summary['languages']=$result['languages']??[];
                    $summary['model']=$result['model']??null;
                }

                $this->lyricsJobs->complete($job,$summary);
            } catch (\Throwable $error) {
                $this->lyricsJobs->fail($job,$error->getMessage());
                return $this->json(['error'=>$error->getMessage()],Response::HTTP_CONFLICT);
            }
            return $this->json(['job_id'=>$job->getId(),'status'=>'completed','progress'=>100]);
        }'''
if old in s:
    s=s.replace(old,new,1)
elif "ezscore.lyrics.extract.r37" not in s:
    die("bloc complete Lyrics inattendu")

wr(p,s)

p=repo/"worker_app/ezscore_analysis_worker.pyw"
if not p.is_file():
    die("worker_app/ezscore_analysis_worker.pyw absent")
s=rd(p)

if "from lyrics_worker_r37 import run_lyrics_job" not in s:
    anchor = '''        if job.get("kind") == "chords":
            self._run_chord_job(job)
            return

'''
    if anchor not in s:
        die("dispatch CHORDS stable introuvable")
    insertion = anchor + '''        if job.get("kind") == "lyrics":
            from lyrics_worker_r37 import run_lyrics_job
            run_lyrics_job(self, job)
            return

'''
    s=s.replace(anchor,insertion,1)

if "def _read_progress(" not in s:
    die("protection stable: WorkerEngine._read_progress absent avant écriture")
if "self._run_chord_job(job)" not in s:
    die("protection stable: dispatch chords absent")

wr(p,s)

chord=rd(repo/"templates/song/chordslab.html.twig")
if "_lab_song_card.html.twig" not in chord or "_timeline_stage.html.twig" not in chord:
    die("mutualisation ChordsLab incomplète")

lyrics=rd(repo/"templates/song/lyricslab.html.twig")
for token in ["Extraire les paroles","_lab_song_card.html.twig","_timeline_stage.html.twig","_analysis_player.html.twig"]:
    if token not in lyrics:
        die("LyricsLab token absent: "+token)

worker=rd(repo/"worker_app/ezscore_analysis_worker.pyw")
for token in ["self._run_chord_job(job)","def _read_progress(","from lyrics_worker_r37 import run_lyrics_job","run_lyrics_job(self, job)"]:
    if token not in worker:
        die("Worker token absent: "+token)

desktop=rd(repo/"src/Controller/AnalysisDesktopController.php")
if "ezscore.lyrics.extract.r37" not in desktop:
    die("completion extraction non branchée")

controller=rd(repo/"src/Controller/SongLabController.php")
if "app_song_lyricslab_extract" not in controller or "$jobs->queue($song,$user,'align');" not in controller:
    die("routes LyricsLab incomplètes")

print("R37_0_APPLIED_OK")
