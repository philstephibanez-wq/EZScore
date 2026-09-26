#!/usr/bin/env python3
from __future__ import annotations
from datetime import datetime
from pathlib import Path
import re, shutil

ROOT=Path(__file__).resolve().parents[1]
PAYLOAD=ROOT/"scripts"/"_payload"
BACKUP=ROOT/"var"/"backup"/("r33-2-async-progress-"+datetime.now().strftime("%Y%m%d-%H%M%S"))

def backup(path):
    path=Path(path)
    if not path.exists(): return
    dst=BACKUP/path.relative_to(ROOT)
    dst.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(path,dst)

def save(path,text,label):
    path=Path(path); old=path.read_text(encoding="utf-8")
    if old==text:
        print(f"[OK] {label}: already applied"); return
    backup(path); path.write_text(text,encoding="utf-8",newline="\n"); print(f"[OK] {label}")

def install(rel):
    src=PAYLOAD/rel; dst=ROOT/rel; content=src.read_text(encoding="utf-8")
    if dst.exists() and dst.read_text(encoding="utf-8")==content:
        print(f"[OK] {rel}: already applied"); return
    backup(dst); dst.parent.mkdir(parents=True,exist_ok=True)
    dst.write_text(content,encoding="utf-8",newline="\n"); print(f"[OK] {rel}")

def snip(name): return (PAYLOAD/"snippets"/name).read_text(encoding="utf-8")

def patch_timeline_repo():
    path=ROOT/"src/Domain/Song/SongTimelineEventRepository.php"; text=path.read_text(encoding="utf-8")
    if "deleteMusicalAnalysisForSong" in text:
        print("[OK] timeline reset method already present"); return
    anchor="    /** @return list<SongTimelineEvent> */\n    public function findChordEvents(Song $song): array\n"
    method=(
        "    public function deleteMusicalAnalysisForSong(Song $song): void\n"
        "    {\n"
        "        $this->createQueryBuilder('e')->delete()\n"
        "            ->andWhere('e.song = :song')->andWhere('e.eventType IN (:types)')\n"
        "            ->setParameter('song', $song)\n"
        "            ->setParameter('types', [SongTimelineEvent::TYPE_BEAT, SongTimelineEvent::TYPE_CHORD])\n"
        "            ->getQuery()->execute();\n"
        "    }\n\n"
    )
    if anchor not in text: raise RuntimeError("timeline repository anchor not found")
    save(path,text.replace(anchor,method+anchor,1),"timeline reset method")

def patch_songlab():
    path=ROOT/"src/Controller/SongLabController.php"; text=path.read_text(encoding="utf-8")
    if "use App\\Service\\SongChordJobService;" not in text:
        anchor="use App\\Service\\SongStemPlaybackStorage;\n"
        if anchor not in text: raise RuntimeError("SongLab import anchor not found")
        text=text.replace(anchor,"use App\\Service\\SongChordJobService;\n"+anchor,1)
    if "app_song_chordslab_status" not in text:
        pattern=re.compile(r"    #\[Route\('/chords/analyze'.*?(?=    #\[Route\('/chords/settings')",re.S)
        text,n=pattern.subn(snip("songlab_analyze_method.txt"),text,count=1)
        if n!=1: raise RuntimeError("SongLab analyze method block not found")
    save(path,text,"async chord queue + status")

def patch_desktop_controller():
    path=ROOT/"src/Controller/AnalysisDesktopController.php"; text=path.read_text(encoding="utf-8")
    if "use App\\Service\\SongChordJobService;" not in text:
        anchor="use App\\Service\\SongStemJobService;\n"
        if anchor not in text: raise RuntimeError("desktop import anchor not found")
        text=text.replace(anchor,
            "use App\\Service\\ChordTimelineResultService;\n"
            "use App\\Service\\ChordTimelineStorage;\n"
            "use App\\Service\\SongChordJobService;\n"+anchor,1)
    if "private readonly SongChordJobService $chordJobs" not in text:
        anchor="        private readonly SongStemJobService $stemJobs,\n"
        repl=("        private readonly SongChordJobService $chordJobs,\n"
              "        private readonly ChordTimelineStorage $chordStorage,\n"
              "        private readonly ChordTimelineResultService $chordResults,\n"+anchor)
        if anchor not in text: raise RuntimeError("desktop constructor anchor not found")
        text=text.replace(anchor,repl,1)

    text=text.replace("$job = $this->stemJobs->claimNext();","$job = $this->chordJobs->claimNext() ?? $this->stemJobs->claimNext();",1)

    text=text.replace(
        "        if ($job->getKind() !== SongStemJobService::KIND) {\n"
        "            return $this->json(['error' => 'Unsupported job kind.'], Response::HTTP_CONFLICT);\n"
        "        }\n\n"
        "        return $this->json($this->jobContext($job));",
        "        if (!in_array($job->getKind(), [SongStemJobService::KIND, SongChordJobService::KIND], true)) {\n"
        "            return $this->json(['error' => 'Unsupported job kind.'], Response::HTTP_CONFLICT);\n"
        "        }\n\n"
        "        return $this->json($this->jobContext($job));",
        1
    )

    if "if ($job->getKind() === SongChordJobService::KIND)" not in text:
        marker="    #[Route('/jobs/{id}/complete', name: 'internal_analysis_desktop_job_complete'"
        start=text.find(marker)
        if start<0: raise RuntimeError("desktop complete route not found")
        body_start=text.find("    public function complete",start)
        next_route=text.find("    #[Route('/jobs/{id}/fail'",body_start)
        if next_route<0: raise RuntimeError("desktop fail route not found")
        complete=text[body_start:next_route]
        needle="        $this->guard->assertAuthorized($request);\n\n"
        if needle not in complete: raise RuntimeError("complete auth anchor not found")
        inject=(
            needle+
            "        if ($job->getKind() === SongChordJobService::KIND) {\n"
            "            try {\n"
            "                $result = $this->chordStorage->readResult($job->getSong());\n"
            "                $summary = $this->chordResults->apply($job->getSong(), $result);\n"
            "                $this->chordJobs->complete($job, $summary);\n"
            "            } catch (\\Throwable $error) {\n"
            "                $this->chordJobs->fail($job, $error->getMessage());\n"
            "                return $this->json(['error' => $error->getMessage()], Response::HTTP_CONFLICT);\n"
            "            }\n"
            "            return $this->json(['job_id' => $job->getId(), 'status' => 'completed', 'progress' => 100]);\n"
            "        }\n\n"
        )
        complete=complete.replace(needle,inject,1)
        text=text[:body_start]+complete+text[next_route:]

    old_fail=(
        "        $payload = $request->toArray();\n"
        "        $error = trim((string) ($payload['error'] ?? 'desktop_worker_failed'));\n"
        "        $this->stemJobs->fail($job, $error);\n"
    )
    new_fail=(
        "        $payload = $request->toArray();\n"
        "        $error = trim((string) ($payload['error'] ?? 'desktop_worker_failed'));\n"
        "        if ($job->getKind() === SongChordJobService::KIND) {\n"
        "            $this->chordJobs->fail($job, $error);\n"
        "        } else {\n"
        "            $this->stemJobs->fail($job, $error);\n"
        "        }\n"
    )
    if old_fail in text: text=text.replace(old_fail,new_fail,1)

    if "'harmony_stems'" not in text:
        old_paths=(
            "            'paths' => [\n"
            "                'source' => $this->stemStorage->sourcePath($song),\n"
            "                'storage_root' => $this->stemStorage->storageRoot($song),\n"
            "                'progress_file' => $this->stemStorage->progressPath($song),\n"
            "                'log_file' => $this->stemStorage->logPath($song),\n"
            "            ],"
        )
        new_paths=(
            "            'paths' => $job->getKind() === SongChordJobService::KIND\n"
            "                ? [\n"
            "                    'source' => $this->chordStorage->sourcePath($song),\n"
            "                    'progress_file' => $this->chordStorage->progressPath($song),\n"
            "                    'result_file' => $this->chordStorage->resultPath($song),\n"
            "                    'harmony_stems' => array_values(array_filter([\n"
            "                        $this->stemStorage->stemPath($song, 'bass'),\n"
            "                        $this->stemStorage->stemPath($song, 'guitar'),\n"
            "                        $this->stemStorage->stemPath($song, 'piano'),\n"
            "                        $this->stemStorage->stemPath($song, 'other'),\n"
            "                    ])),\n"
            "                    'drums' => $this->stemStorage->stemPath($song, 'drums'),\n"
            "                ]\n"
            "                : [\n"
            "                    'source' => $this->stemStorage->sourcePath($song),\n"
            "                    'storage_root' => $this->stemStorage->storageRoot($song),\n"
            "                    'progress_file' => $this->stemStorage->progressPath($song),\n"
            "                    'log_file' => $this->stemStorage->logPath($song),\n"
            "                ],"
        )
        if old_paths not in text: raise RuntimeError("desktop paths anchor not found")
        text=text.replace(old_paths,new_paths,1)

    save(path,text,"desktop API chord jobs")

def patch_worker():
    path=ROOT/"worker_app/ezscore_analysis_worker.pyw"; text=path.read_text(encoding="utf-8")
    text=text.replace('APP_VERSION = "R27.2"','APP_VERSION = "R33.2"',1)
    text=text.replace('text=f"{APP_VERSION} · STEMS ONLY"','text=f"{APP_VERSION} · STEMS + CHORDS"',1)
    if "self._run_chord_job(job)" not in text:
        guard=(
            '        if job.get("kind") != "stems":\n'
            '            self.log(f"Job #{job.get(\'job_id\')} ignoré: kind={job.get(\'kind\')}")\n'
            '            self.api.post(f"/internal/analysis/desktop/jobs/{job[\'job_id\']}/fail", {"error": "unsupported_job_kind"})\n'
            '            return\n'
        )
        if guard not in text: raise RuntimeError("worker kind guard anchor not found")
        text=text.replace(guard,'        if job.get("kind") == "chords":\n            self._run_chord_job(job)\n            return\n\n'+guard,1)
    if "def _run_chord_job(self, job: dict)" not in text:
        anchor="    @staticmethod\n    def _read_progress(path: Path) -> dict | None:\n"
        if anchor not in text: raise RuntimeError("worker progress anchor not found")
        text=text.replace(anchor,snip("worker_method.txt")+anchor,1)
    save(path,text,"Desktop Worker CHORDS support")

def patch_template():
    path=ROOT/"templates/song/chordslab.html.twig"; text=path.read_text(encoding="utf-8")

    if "data-chord-analysis-progress" not in text:
        pos=text.find("{% if chord_events %}",text.find("chordslab-prompter-actions"))
        if pos<0: raise RuntimeError("prompter actions anchor not found")
        text=text[:pos]+snip("progress.html")+"\n    "+text[pos:]

    # Native confirm -> custom modal marker.
    text=re.sub(r'\s+onsubmit="return confirm\([^;]+;"','',text,count=1)
    if "data-chord-reset-form" not in text:
        needle="action=\"{{ path('app_song_chordslab_reset', {'_locale': app.request.locale, id: song.id}) }}\""
        if needle not in text: raise RuntimeError("reset form anchor not found")
        text=text.replace(needle,needle+" data-chord-reset-form",1)

    if "data-chord-reset-dialog" not in text:
        anchor="{% endif %}\n{% endblock %}"
        if anchor not in text: raise RuntimeError("template body end anchor not found")
        text=text.replace(anchor,"{% endif %}\n"+snip("dialog.html")+"\n{% endblock %}",1)

    if "data-chordslab-quick-volume" not in text:
        anchor="        <button type=\"button\" data-mixer-stop>{{ 'stems.mixer.stop'|trans({}, 'stems') }}</button>\n"
        if anchor not in text: raise RuntimeError("transport stop anchor not found")
        text=text.replace(anchor,anchor+snip("volume.html"),1)

    if "data-analysis-level-help" not in text:
        idx=text.find('name="chord_analysis_level"')
        if idx<0: raise RuntimeError("analysis level select not found")
        close=text.find("</label>",idx)
        if close<0: raise RuntimeError("analysis level label close not found")
        text=text[:close+8]+"\n        <small data-analysis-level-help></small>"+text[close+8:]

    if "chordslab-r33-2.js" not in text:
        anchor='<script src="/assets/js/chordslab-r33-1.js?v=20260926r33_1"></script>\n'
        if anchor not in text: anchor='<script src="/assets/js/chordslab.js?v=20260926r33"></script>\n'
        if anchor not in text: raise RuntimeError("script anchor not found")
        text=text.replace(anchor,anchor+'<script src="/assets/js/chordslab-r33-2.js?v=20260926r33_2"></script>\n',1)

    text=text.replace('/assets/css/chordslab.css?v=20260926r33_1','/assets/css/chordslab.css?v=20260926r33_2')
    save(path,text,"ChordsLab progress/modal/volume UI")

def patch_chordslab_js():
    path=ROOT/"public/assets/js/chordslab.js"; text=path.read_text(encoding="utf-8")
    if "const canonicalSignature=signature;" not in text:
        old=(
            "function buildProjection(){\n"
            " const sig=parseSignature(signature), measures=[]; let measure=null;\n"
            " beats.forEach((beat,seq)=>{\n"
            "  const measureIndex=Math.floor(seq/sig.num), beatIndex=seq%sig.num;"
        )
        new=(
            "const canonicalSignature=signature;\n"
            "function buildProjection(){\n"
            " const sig=parseSignature(signature), measures=[]; let measure=null;\n"
            " const useCanonical=signature===canonicalSignature;\n"
            " beats.forEach((beat,seq)=>{\n"
            "  const measureIndex=useCanonical&&Number.isInteger(beat.measure_index)?beat.measure_index:Math.floor(seq/sig.num);\n"
            "  const beatIndex=useCanonical&&Number.isInteger(beat.beat_index)?beat.beat_index:seq%sig.num;"
        )
        if old not in text: raise RuntimeError("buildProjection anchor not found")
        text=text.replace(old,new,1)
    save(path,text,"canonical beat/downbeat projection")

def patch_css():
    path=ROOT/"public/assets/css/chordslab.css"; text=path.read_text(encoding="utf-8")
    if "R33.2 async analysis" in text:
        print("[OK] R33.2 CSS already applied"); return
    save(path,text.rstrip()+"\n"+snip("css_add.txt"),"R33.2 CSS")

def patch_docs():
    for rel,sname,marker in [
        ("docs/CAHIER_DES_CHARGES.md","cdc_add.txt","## 41. ChordsLab — analyse asynchrone et progression"),
        ("recette.md","recette_add.txt","## 32. Recette R33.2 — job accords / progression / UX"),
    ]:
        path=ROOT/rel
        if not path.is_file(): continue
        text=path.read_text(encoding="utf-8")
        if marker in text:
            print(f"[OK] {rel} already updated"); continue
        save(path,text.rstrip()+"\n"+snip(sname),rel)

def main():
    for rel in [
        "analysis/chord_timeline_analysis.py",
        "src/Service/SongChordJobService.php",
        "src/Service/ChordTimelineStorage.php",
        "src/Service/ChordTimelineResultService.php",
        "public/assets/js/chordslab-r33-2.js",
    ]: install(rel)
    patch_timeline_repo()
    patch_songlab()
    patch_desktop_controller()
    patch_worker()
    patch_template()
    patch_chordslab_js()
    patch_css()
    patch_docs()
    print(f"[OK] Backup: {BACKUP}")
    print("[OK] R33.2 async/progress/UX applied.")

if __name__=="__main__":
    main()
