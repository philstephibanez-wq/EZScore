#!/usr/bin/env python3
from pathlib import Path
import subprocess
import sys

def die(message: str) -> None:
    raise SystemExit("R36.1 ABORT: " + message)

def read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")

def write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="\n")

def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        die("ancre absente: " + label)
    return text.replace(old, new, 1)

root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()

required = [
    "src/Controller/SongLabController.php",
    "src/Controller/AnalysisDesktopController.php",
    "src/Service/SongLyricsJobService.php",
    "worker_app/ezscore_analysis_worker.pyw",
    "templates/song/lyricslab.html.twig",
    "analysis/lyrics_timeline_analysis.py",
]
for rel in required:
    if not (root / rel).is_file():
        die("fichier absent: " + rel)

# 1) SongLabController
p = root / "src/Controller/SongLabController.php"
s = read(p)

s = s.replace(
    "$jobs->queue($song,$user);",
    "$jobs->queue($song,$user,'align');",
    1,
)

if "app_song_lyricslab_extract" not in s:
    anchor = "    #[Route('/lyrics/status', name: 'app_song_lyricslab_status', methods: ['GET'])]\n"
    method = r'''    #[Route('/lyrics/extract', name: 'app_song_lyricslab_extract', methods: ['POST'])]
    public function extractLyrics(
        Song $song,
        Request $request,
        \App\Service\SongLyricsJobService $jobs,
    ): Response {
        $user = $this->requireEditor($song);

        if (!$this->isCsrfTokenValid(
            'song_lyricslab_extract_'.$song->getId(),
            (string) $request->request->get('_token'),
        )) {
            throw $this->createAccessDeniedException();
        }

        $jobs->queue($song, $user, 'extract');

        return $this->redirectToRoute('app_song_lyricslab', [
            '_locale' => $request->getLocale(),
            'id' => $song->getId(),
        ]);
    }

'''
    s = replace_once(s, anchor, method + anchor, "LyricsLab extract route")

old_status = "return $this->json(['job_id'=>$job->getId(),'status'=>$job->getStatus()->value,'progress'=>$job->getProgress(),'error'=>$job->getErrorCode()]);"
new_status = "return $this->json(['job_id'=>$job->getId(),'status'=>$job->getStatus()->value,'progress'=>$job->getProgress(),'error'=>$job->getErrorCode(),'mode'=>(string)($job->getRequestData()['mode']??'align')]);"
if old_status in s:
    s = s.replace(old_status, new_status, 1)

if "use App\\Domain\\Analysis\\AnalysisJobRepository;" not in s:
    s = s.replace(
        "namespace App\\Controller;\n\n",
        "namespace App\\Controller;\n\nuse App\\Domain\\Analysis\\AnalysisJobRepository;\n",
        1,
    )

old_sig = "public function analysis(Song $song, SongWorkflowState $workflow, SongCollaboratorRepository $collaborators): Response"
new_sig = "public function analysis(Song $song, SongWorkflowState $workflow, SongCollaboratorRepository $collaborators, AnalysisJobRepository $analysisJobs): Response"
if old_sig in s:
    s = s.replace(old_sig, new_sig, 1)

old_render = "return $this->render('song/analysis_dashboard.html.twig', ['song'=>$song,'workflow'=>$workflow->forSong($song),'collaborators'=>$collaborators->findForSong($song)]);"
new_render = r'''$jobs=$analysisJobs->createQueryBuilder('job')
            ->andWhere('job.song=:song')
            ->setParameter('song',$song)
            ->orderBy('job.createdAt','DESC')
            ->addOrderBy('job.id','DESC')
            ->setMaxResults(12)
            ->getQuery()
            ->getResult();

        return $this->render('song/analysis_dashboard.html.twig', [
            'song'=>$song,
            'workflow'=>$workflow->forSong($song),
            'collaborators'=>$collaborators->findForSong($song),
            'analysis_jobs'=>$jobs,
        ]);'''
if old_render in s:
    s = s.replace(old_render, new_render, 1)

write(p, s)

# 2) AnalysisDesktopController
p = root / "src/Controller/AnalysisDesktopController.php"
s = read(p)

needle = r'''                $result=$this->lyricsStorage->readResult($job->getSong());
                $summary=$this->lyricsResults->apply($job->getSong(),$result);
                $this->lyricsJobs->complete($job,$summary);
'''
replacement = r'''                $result=$this->lyricsStorage->readResult($job->getSong());
                $mode=(string)($result['mode']??$job->getRequestData()['mode']??'align');

                if ($mode === 'extract') {
                    $text=trim((string)($result['text']??''));
                    if ($text === '') {
                        throw new \RuntimeException('Lyrics extraction returned an empty text.');
                    }

                    $job->getSong()->setLyricsSourceText($text);
                    $this->em->flush();

                    $summary=[
                        'mode'=>'extract',
                        'characters'=>mb_strlen($text),
                        'recognized_words'=>(int)($result['recognized_words']??0),
                        'languages'=>$result['languages']??[],
                        'model'=>$result['model']??null,
                    ];
                } else {
                    $summary=$this->lyricsResults->apply($job->getSong(),$result);
                    $summary['mode']='align';
                    $summary['languages']=$result['languages']??[];
                    $summary['model']=$result['model']??null;
                }

                $this->lyricsJobs->complete($job,$summary);
'''
if needle in s:
    s = s.replace(needle, replacement, 1)
elif "Lyrics extraction returned an empty text." not in s:
    die("branche completion LyricsLab introuvable")

write(p, s)

# 3) Worker
p = root / "worker_app/ezscore_analysis_worker.pyw"
s = read(p)

if 'if job.get("kind") == "lyrics":' not in s:
    anchor = '        if job.get("kind") == "chords":\n            self._run_chord_job(job)\n            return\n\n'
    dispatch = anchor + '        if job.get("kind") == "lyrics":\n            self._run_lyrics_job(job)\n            return\n\n'
    s = replace_once(s, anchor, dispatch, "worker lyrics dispatch")

# Remove earlier broken class-body implementation if present.
start = s.find("    def _run_lyrics_job(self, job: dict) -> None:")
if start != -1:
    end = s.find("    @staticmethod\n    def _read_progress", start)
    if end != -1:
        s = s[:start] + s[end:]

marker = "# R36.1 LYRICS WORKER BINDING"
if marker not in s:
    main_pos = s.find('\nif __name__ == "__main__":')
    if main_pos == -1:
        main_pos = s.find("\nif __name__ == '__main__':")
    if main_pos == -1:
        die("point d'entrée Worker introuvable")

    binding = r'''
# R36.1 LYRICS WORKER BINDING
def _ezscore_r36_1_run_lyrics_job(self, job: dict) -> None:
    assert self.api is not None
    assert self.engine_python is not None

    job_id = int(job["job_id"])
    song = job.get("song") or {}
    paths = job.get("paths") or {}
    request = job.get("request") or {}
    mode = str(request.get("mode") or "align")

    self.current_job = {
        "job_id": job_id,
        "song_id": job.get("song_id"),
        "kind": "lyrics",
        "title": song.get("title"),
        "artist": song.get("artist"),
        "progress": 1,
        "stage": "queued",
    }
    self.app.events.put(("job", self.current_job.copy()))
    self.log(
        f"Job paroles #{job_id} pris ({mode}): "
        f"{song.get('artist')} — {song.get('title')}"
    )

    audio_path = paths.get("lead_vocals")
    if not audio_path or not Path(str(audio_path)).is_file():
        audio_path = paths["source"]

    command = [
        self.engine_python,
        str(self.root / "analysis" / "lyrics_timeline_analysis.py"),
        "--audio", str(audio_path),
        "--output", str(paths["result_file"]),
        "--progress-file", str(paths["progress_file"]),
        "--mode", mode,
    ]

    if mode == "align":
        lyrics_file = paths.get("lyrics_file")
        if not lyrics_file:
            raise RuntimeError("lyrics_file_missing")
        command.extend(["--lyrics-file", str(lyrics_file)])

    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"

    self.log("Commande LYRICS lancée.")

    progress_path = Path(str(paths["progress_file"]))
    result_path = Path(str(paths["result_file"]))
    progress_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        progress_path.unlink(missing_ok=True)
        result_path.unlink(missing_ok=True)
    except Exception:
        pass

    proc = subprocess.Popen(
        command,
        cwd=str(self.root),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
        creationflags=WINDOWS_NO_WINDOW if os.name == "nt" else 0,
    )
    self.current_process = proc

    output_queue: queue.Queue[str | None] = queue.Queue()

    def _reader() -> None:
        if proc.stdout is None:
            output_queue.put(None)
            return
        try:
            for line in proc.stdout:
                output_queue.put(line.rstrip())
        finally:
            output_queue.put(None)

    threading.Thread(target=_reader, daemon=True).start()

    last_progress = -1
    last_db_update = 0.0
    last_job_heartbeat = 0.0

    while proc.poll() is None:
        if self.stop_event.is_set():
            proc.terminate()
            break

        while True:
            try:
                line = output_queue.get_nowait()
            except queue.Empty:
                break
            if line:
                self.log("[LYRICS] " + line)

        current = self._read_progress(progress_path)
        if current:
            pct = int(current.get("percent", 0))
            self.current_job["progress"] = pct
            self.current_job["stage"] = current.get("stage")
            self.current_job["message"] = current.get("message")
            self.app.events.put(("progress", current))

            now = time.monotonic()
            if pct != last_progress and now - last_db_update >= 0.5:
                try:
                    self.api.post(
                        f"/internal/analysis/desktop/jobs/{job_id}/progress",
                        {"progress": pct},
                        timeout=10,
                    )
                except Exception as exc:
                    self.log(f"Progression paroles non publiée: {exc}")
                last_progress = pct
                last_db_update = now

        now = time.monotonic()
        if now - last_job_heartbeat >= HEARTBEAT_SECONDS:
            try:
                self._send_heartbeat("busy")
            except Exception as exc:
                self.log(f"Heartbeat paroles impossible: {exc}")
            last_job_heartbeat = now

        time.sleep(0.25)

    return_code = proc.wait()
    self.current_process = None

    if return_code == 0 and result_path.is_file():
        try:
            self.api.post(
                f"/internal/analysis/desktop/jobs/{job_id}/complete",
                {},
                timeout=30,
            )
            self.log(f"Job paroles #{job_id} terminé.")
            self.app.events.put((
                "progress",
                {"percent": 100, "stage": "complete", "message": "Paroles terminées"},
            ))
        except Exception as exc:
            self.log(f"Échec validation paroles #{job_id}: {exc}")
            try:
                self.api.post(
                    f"/internal/analysis/desktop/jobs/{job_id}/fail",
                    {"error": str(exc)[:400]},
                )
            except Exception:
                pass
    else:
        error = f"lyrics_python_exit_{return_code}"
        self.log(f"Job paroles #{job_id} en échec: {error}")
        try:
            self.api.post(
                f"/internal/analysis/desktop/jobs/{job_id}/fail",
                {"error": error},
            )
        except Exception:
            pass

    self.current_job = None
    self.app.events.put(("job", None))


WorkerEngine._run_lyrics_job = _ezscore_r36_1_run_lyrics_job

if not hasattr(WorkerEngine, "_run_lyrics_job"):
    raise RuntimeError("R36.1 lyrics worker binding failed")

'''
    s = s[:main_pos] + "\n" + binding + s[main_pos:]

s = s.replace("R35.4 · STEMS + CHORDS", "R36.1 · STEMS + CHORDS + LYRICS")
write(p, s)

# 4) Analysis dashboard history
dashboard = root / "templates/song/analysis_dashboard.html.twig"
if dashboard.is_file():
    d = read(dashboard)
    if "Historique des analyses" not in d:
        marker = '<section class="panel analysis-summary clean-analysis-summary">'
        block = r'''
<section class="panel analysis-jobs-panel">
    <div class="eyebrow">Traitements</div>
    <h2>Historique des analyses</h2>
    {% if analysis_jobs is defined and analysis_jobs %}
        <div class="analysis-jobs-table">
        {% for job in analysis_jobs %}
            <div class="analysis-job-row">
                <strong>#{{ job.id }}</strong>
                <span>{{ job.kind == 'lyrics' ? 'Paroles' : (job.kind == 'chords' ? 'Accords' : (job.kind == 'stems' ? 'Stems' : job.kind)) }}</span>
                <span>{{ job.status.value }}</span>
                <span>{{ job.progress }}%</span>
                {% if job.kind == 'lyrics' %}
                    <small>{{ job.requestData.mode|default('align') == 'extract' ? 'Extraction du texte' : 'Ancrage sur la timeline' }}</small>
                {% endif %}
            </div>
        {% endfor %}
        </div>
    {% else %}
        <p class="page-note">Aucun traitement enregistré.</p>
    {% endif %}
</section>
'''
        if marker in d:
            d = d.replace(marker, block + "\n" + marker, 1)
        write(dashboard, d)

# 5) Remove obsolete R36.0a assets only when untracked.
for rel in [
    "public/assets/css/lyricslab-r36-0a.css",
    "public/assets/js/lyricslab-r36-0a.js",
]:
    target = root / rel
    if not target.exists():
        continue
    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch", rel],
        cwd=root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ).returncode == 0
    if not tracked:
        target.unlink()

# Hard checks.
worker = read(root / "worker_app/ezscore_analysis_worker.pyw")
if "WorkerEngine._run_lyrics_job = _ezscore_r36_1_run_lyrics_job" not in worker:
    die("binding WorkerEngine absent")
if 'hasattr(WorkerEngine, "_run_lyrics_job")' not in worker:
    die("runtime check WorkerEngine absent")

controller = read(root / "src/Controller/SongLabController.php")
for token in [
    "app_song_lyricslab_extract",
    "$jobs->queue($song,$user,'align')",
    "'mode'=>(string)($job->getRequestData()['mode']??'align')",
]:
    if token not in controller:
        die("controller token absent: " + token)

desktop = read(root / "src/Controller/AnalysisDesktopController.php")
if "Lyrics extraction returned an empty text." not in desktop:
    die("completion extraction absente")

print("R36_1_APPLIED_OK")
