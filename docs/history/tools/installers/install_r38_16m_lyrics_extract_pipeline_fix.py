#!/usr/bin/env python3
from __future__ import annotations
import re, sys
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else r"H:\EZScore_v1").resolve()
JOB = ROOT/"src/Service/SongLyricsJobService.php"
LAB = ROOT/"src/Controller/SongLabController.php"
DESKTOP = ROOT/"src/Controller/AnalysisDesktopController.php"
JS = ROOT/"public/assets/js/lyricslab-r37.js"

def main() -> int:
    for p in (JOB, LAB, DESKTOP, JS):
        if not p.is_file():
            raise RuntimeError(f"Missing prerequisite: {p}")

    job = JOB.read_text(encoding="utf-8")
    lab = LAB.read_text(encoding="utf-8")
    desktop = DESKTOP.read_text(encoding="utf-8")
    js = JS.read_text(encoding="utf-8")

    # 1. Never silently reuse an active lyrics job of the wrong mode.
    old = """        if ($active = $this->findActive($song)) {
            return $active;
        }
"""
    new = """        if ($active = $this->findActive($song)) {
            $activeMode = (string) ($active->getRequestData()['mode'] ?? 'align');
            if ($activeMode === $mode) {
                return $active;
            }

            throw new \\DomainException('lyrics_job_mode_conflict:'.$activeMode);
        }
"""
    if old in job:
        job = job.replace(old, new, 1)
    elif "lyrics_job_mode_conflict:" not in job:
        raise RuntimeError("SongLyricsJobService active-job anchor not found")

    # 2. Extract must not create an automatic history revision.
    # Remove history service argument if still present.
    lab = re.sub(
        r",\n\s*\\\\App\\\\Service\\\\LyricsSourceHistoryService \$lyricsHistory,\n",
        ",\n",
        lab,
        count=1,
    )

    # Remove auto archive block.
    lab = re.sub(
        r"""\n\s*\$lyricsHistory->archiveCurrentIfChanged\(
\s*\$song,
\s*\$user,
\s*'manual',
\s*'Sauvegarde automatique avant extraction Whisper\.',
\s*\);
""",
        "\n",
        lab,
        count=1,
    )
    if "Sauvegarde automatique avant extraction Whisper." in lab:
        raise RuntimeError("Automatic history save before extract remains")

    # 3. Explicitly report mode conflicts in both Analyze and Extract.
    analyze_old = """    $jobs->queue($song,$user,'align');
    return $this->redirectToRoute('app_song_lyricslab',['_locale'=>$request->getLocale(),'id'=>$song->getId()]);
"""
    analyze_new = """    try {
        $jobs->queue($song, $user, 'align');
    } catch (\\DomainException $error) {
        if (str_starts_with($error->getMessage(), 'lyrics_job_mode_conflict:')) {
            $activeMode = substr($error->getMessage(), strlen('lyrics_job_mode_conflict:'));
            $this->addFlash('error', sprintf(
                'Une tâche paroles est déjà en cours (%s). Attendez sa fin avant de lancer une autre opération.',
                $activeMode,
            ));
            return $this->redirectToRoute('app_song_lyricslab', ['_locale'=>$request->getLocale(),'id'=>$song->getId()]);
        }
        throw $error;
    }
    return $this->redirectToRoute('app_song_lyricslab',['_locale'=>$request->getLocale(),'id'=>$song->getId()]);
"""
    if analyze_old in lab:
        lab = lab.replace(analyze_old, analyze_new, 1)
    elif "queue($song, $user, 'align')" not in lab:
        raise RuntimeError("Analyze queue anchor not found")

    extract_old = """    $jobs->queue($song, $user, 'extract');

    return $this->redirectToRoute('app_song_lyricslab', [
"""
    extract_new = """    try {
        $jobs->queue($song, $user, 'extract');
    } catch (\\DomainException $error) {
        if (str_starts_with($error->getMessage(), 'lyrics_job_mode_conflict:')) {
            $activeMode = substr($error->getMessage(), strlen('lyrics_job_mode_conflict:'));
            $this->addFlash('error', sprintf(
                'Une tâche paroles est déjà en cours (%s). Attendez sa fin avant de lancer l’extraction.',
                $activeMode,
            ));
            return $this->redirectToRoute('app_song_lyricslab', [
                '_locale' => $request->getLocale(),
                'id' => $song->getId(),
            ]);
        }
        throw $error;
    }

    return $this->redirectToRoute('app_song_lyricslab', [
"""
    if extract_old in lab:
        lab = lab.replace(extract_old, extract_new, 1)
    elif "queue($song, $user, 'extract')" not in lab:
        raise RuntimeError("Extract queue anchor not found")

    # 4. Status exposes what actually ran and whether source text was persisted.
    old_status = """    return $this->json(['job_id'=>$job->getId(),'status'=>$job->getStatus()->value,'progress'=>$job->getProgress(),'error'=>$job->getErrorCode(),'mode'=>(string)($job->getRequestData()['mode']??'align')]);
"""
    new_status = """    $result = $job->getResultData() ?? [];
    return $this->json([
        'job_id' => $job->getId(),
        'status' => $job->getStatus()->value,
        'progress' => $job->getProgress(),
        'error' => $job->getErrorCode(),
        'mode' => (string) ($job->getRequestData()['mode'] ?? 'align'),
        'source_characters' => mb_strlen(trim((string) $song->getLyricsSourceText())),
        'result_characters' => (int) ($result['characters'] ?? 0),
        'recognized_words' => (int) ($result['recognized_words'] ?? 0),
    ]);
"""
    if old_status in lab:
        lab = lab.replace(old_status, new_status, 1)
    elif "'source_characters'" not in lab:
        raise RuntimeError("Lyrics status anchor not found")

    # 5. A successful extract changes the source but does NOT save a history version.
    # Clear exact current-revision pointer if the R38.16L field exists.
    desktop_old = """                    $job->getSong()->setLyricsSourceText($text);
                    $this->em->flush();

                    $summary = [
"""
    desktop_new = """                    $job->getSong()->setLyricsSourceText($text);
                    if (method_exists($job->getSong(), 'setLyricsCurrentRevisionId')) {
                        $job->getSong()->setLyricsCurrentRevisionId(null);
                    }
                    $this->em->flush();

                    if (trim((string) $job->getSong()->getLyricsSourceText()) !== $text) {
                        throw new \\RuntimeException('lyrics_extract_persist_failed');
                    }

                    $summary = [
"""
    if desktop_old in desktop:
        desktop = desktop.replace(desktop_old, desktop_new, 1)
    elif "lyrics_extract_persist_failed" not in desktop:
        raise RuntimeError("Desktop extract persist anchor not found")

    # 6. Browser must not report a successful extract if backend says zero source chars.
    old_js = """if(j.status==='completed'){if(!completedReloaded){completedReloaded=true;setTimeout(()=>location.reload(),500)}return}"""
    new_js = """if(j.status==='completed'){
  if((j.mode||'align')==='extract' && Number(j.source_characters||0)<=0){
    if(state) state.textContent='Extraction terminée mais aucune parole n’a été persistée.';
    if(bar) bar.style.width='100%';
    return;
  }
  if(!completedReloaded){completedReloaded=true;setTimeout(()=>location.reload(),500)}
  return
}"""
    if old_js in js:
        js = js.replace(old_js, new_js, 1)
    elif "aucune parole n’a été persistée" not in js:
        # tolerate whitespace/minified variation
        pat = re.compile(r"if\(j\.status==='completed'\)\{if\(!completedReloaded\)\{completedReloaded=true;setTimeout\(\(\)=>location\.reload\(\),500\)\}return\}")
        js, n = pat.subn(lambda _m: new_js, js, count=1)
        if n != 1:
            raise RuntimeError("Lyrics completed JS anchor not found")

    # Write only after all anchors validated.
    JOB.write_text(job, encoding="utf-8", newline="\n")
    LAB.write_text(lab, encoding="utf-8", newline="\n")
    DESKTOP.write_text(desktop, encoding="utf-8", newline="\n")
    JS.write_text(js, encoding="utf-8", newline="\n")

    print("R38_16M_LYRICS_EXTRACT_PIPELINE_FIX_INSTALL_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
