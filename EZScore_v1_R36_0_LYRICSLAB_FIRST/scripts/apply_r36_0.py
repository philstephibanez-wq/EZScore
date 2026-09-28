#!/usr/bin/env python3
from pathlib import Path
import shutil,sys,re

def die(msg):
    raise SystemExit("R36.0 ABORT: "+msg)

def rd(p):
    return p.read_text(encoding="utf-8-sig")

def wr(p,s):
    p.write_text(s,encoding="utf-8",newline="\n")

def rep(s,a,b,label):
    if a not in s:
        die("ancre absente: "+label)
    return s.replace(a,b,1)

root=Path(sys.argv[1] if len(sys.argv)>1 else ".").resolve()
bundle=Path(__file__).resolve().parents[1]/"payload"

for rel in [
    "src/Domain/Song/Song.php",
    "src/Controller/SongLabController.php",
    "src/Controller/AnalysisDesktopController.php",
    "worker_app/ezscore_analysis_worker.pyw",
]:
    if not (root/rel).is_file():
        die("fichier absent: "+rel)

for rel in [
    "src/Service/LyricsTimelineStorage.php",
    "src/Service/SongLyricsJobService.php",
    "src/Service/LyricsTimelineResultService.php",
    "templates/song/lyricslab.html.twig",
    "public/assets/js/lyricslab-r36.js",
    "public/assets/css/lyricslab-r36.css",
    "analysis/lyrics_timeline_analysis.py",
    "migrations/Version20260928030000.php",
]:
    src=bundle/rel
    dst=root/rel
    dst.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(src,dst)

# Song: persist editable source lyrics.
p=root/"src/Domain/Song/Song.php"
s=rd(p)
if "private ?string $lyricsSourceText" not in s:
    anchor="    #[ORM\\Column(length: 1000, nullable: true)]\n    private ?string $comment = null;\n"
    insert=anchor+"\n    #[ORM\\Column(name: 'lyrics_source_text', type: 'text', nullable: true)]\n    private ?string $lyricsSourceText = null;\n"
    s=rep(s,anchor,insert,"Song lyrics field")
if "getLyricsSourceText()" not in s:
    anchor="    public function getComment(): ?string { return $this->comment; }\n"
    insert="    public function getLyricsSourceText(): ?string { return $this->lyricsSourceText; }\n    public function setLyricsSourceText(?string $value): self\n    {\n        $this->lyricsSourceText = $value === null ? null : str_replace([\"\\r\\n\",\"\\r\"],\"\\n\",$value);\n        return $this->touch();\n    }\n\n"+anchor
    s=rep(s,anchor,insert,"Song lyrics methods")
wr(p,s)

# SongLabController: replace placeholder LyricsLab block.
p=root/"src/Controller/SongLabController.php"
s=rd(p)
start=s.find("    #[Route('/lyrics', name: 'app_song_lyricslab'")
end=s.find("    #[Route('/publication'",start)
if start<0 or end<0:
    die("route LyricsLab placeholder introuvable")
block=rd(bundle/"patches/songlab_lyrics_block.txt")
s=s[:start]+block+s[end:]
wr(p,s)

# AnalysisDesktopController: register lyrics job/storage/result services.
p=root/"src/Controller/AnalysisDesktopController.php"
s=rd(p)
if "use App\\Service\\SongLyricsJobService;" not in s:
    s=s.replace(
        "use App\\Service\\SongStemJobService;",
        "use App\\Service\\SongStemJobService;\nuse App\\Service\\SongLyricsJobService;\nuse App\\Service\\LyricsTimelineStorage;\nuse App\\Service\\LyricsTimelineResultService;",
        1
    )

if "private readonly SongLyricsJobService $lyricsJobs" not in s:
    anchor="        private readonly SongStemStorage $stemStorage,\n        private readonly EntityManagerInterface $em,\n"
    insert="        private readonly SongStemStorage $stemStorage,\n        private readonly SongLyricsJobService $lyricsJobs,\n        private readonly LyricsTimelineStorage $lyricsStorage,\n        private readonly LyricsTimelineResultService $lyricsResults,\n        private readonly EntityManagerInterface $em,\n"
    s=rep(s,anchor,insert,"desktop lyrics constructor")

s=s.replace(
    "$job = $this->chordJobs->claimNext() ?? $this->stemJobs->claimNext();",
    "$job = $this->chordJobs->claimNext() ?? $this->lyricsJobs->claimNext() ?? $this->stemJobs->claimNext();",
    1
)

s=s.replace(
    "if (!in_array($job->getKind(), [SongStemJobService::KIND, SongChordJobService::KIND], true))",
    "if (!in_array($job->getKind(), [SongStemJobService::KIND, SongChordJobService::KIND, SongLyricsJobService::KIND], true))",
    1
)

complete_pos=s.find("#[Route('/jobs/{id}/complete'")
fail_pos=s.find("#[Route('/jobs/{id}/fail'",complete_pos)
if complete_pos<0 or fail_pos<0:
    die("desktop complete/fail routes introuvables")
complete_slice=s[complete_pos:fail_pos]
if "SongLyricsJobService::KIND" not in complete_slice:
    anchor="        if ($job->getKind() === SongChordJobService::KIND) {\n"
    lyrics_complete=(
        "        if ($job->getKind() === SongLyricsJobService::KIND) {\n"
        "            try {\n"
        "                $result=$this->lyricsStorage->readResult($job->getSong());\n"
        "                $summary=$this->lyricsResults->apply($job->getSong(),$result);\n"
        "                $this->lyricsJobs->complete($job,$summary);\n"
        "            } catch (\\Throwable $error) {\n"
        "                $this->lyricsJobs->fail($job,$error->getMessage());\n"
        "                return $this->json(['error'=>$error->getMessage()],Response::HTTP_CONFLICT);\n"
        "            }\n"
        "            return $this->json(['job_id'=>$job->getId(),'status'=>'completed','progress'=>100]);\n"
        "        }\n\n"
    )
    s=rep(s,anchor,lyrics_complete+anchor,"desktop lyrics complete")

old_fail=(
    "        if ($job->getKind() === SongChordJobService::KIND) {\n"
    "            $this->chordJobs->fail($job, $error);\n"
    "        } else {\n"
    "            $this->stemJobs->fail($job, $error);\n"
    "        }\n"
)
new_fail=(
    "        if ($job->getKind() === SongChordJobService::KIND) {\n"
    "            $this->chordJobs->fail($job, $error);\n"
    "        } elseif ($job->getKind() === SongLyricsJobService::KIND) {\n"
    "            $this->lyricsJobs->fail($job, $error);\n"
    "        } else {\n"
    "            $this->stemJobs->fail($job, $error);\n"
    "        }\n"
)
if old_fail in s:
    s=s.replace(old_fail,new_fail,1)

# Add lyrics paths in jobContext without disturbing chord/stem paths.
ctx=s.find("private function jobContext")
if ctx<0:
    die("jobContext introuvable")
ctx_text=s[ctx:]
if "'lyrics_file' => $this->lyricsStorage->lyricsPath($song)" not in ctx_text:
    marker="                : [\n                    'source' => $this->stemStorage->sourcePath($song),\n"
    repl=(
        "                : ($job->getKind() === SongLyricsJobService::KIND\n"
        "                    ? [\n"
        "                        'source' => $this->lyricsStorage->sourcePath($song),\n"
        "                        'lead_vocals' => $this->stemStorage->stemPath($song, 'lead_vocals'),\n"
        "                        'lyrics_file' => $this->lyricsStorage->lyricsPath($song),\n"
        "                        'progress_file' => $this->lyricsStorage->progressPath($song),\n"
        "                        'result_file' => $this->lyricsStorage->resultPath($song),\n"
        "                    ]\n"
        "                    : [\n"
        "                    'source' => $this->stemStorage->sourcePath($song),\n"
    )
    s=rep(s,marker,repl,"desktop lyrics paths")
    tail="                    'log_file' => $this->stemStorage->logPath($song),\n                ],\n"
    if tail not in s:
        die("fin paths stems introuvable")
    s=s.replace(tail,"                    'log_file' => $this->stemStorage->logPath($song),\n                ]),\n",1)
wr(p,s)

# Desktop worker: dispatch and run lyrics jobs.
p=root/"worker_app/ezscore_analysis_worker.pyw"
s=rd(p)
if 'if job.get("kind") == "lyrics":' not in s:
    anchor='        if job.get("kind") == "chords":\n            self._run_chord_job(job)\n            return\n\n'
    insert=anchor+'        if job.get("kind") == "lyrics":\n            self._run_lyrics_job(job)\n            return\n\n'
    s=rep(s,anchor,insert,"worker lyrics dispatch")

if "def _run_lyrics_job" not in s:
    anchor="    @staticmethod\n    def _read_progress(path: Path) -> dict | None:\n"
    method=rd(bundle/"patches/worker_lyrics_method.txt")
    s=rep(s,anchor,method+anchor,"worker lyrics method")
wr(p,s)

print("R36_0_APPLIED_OK")
