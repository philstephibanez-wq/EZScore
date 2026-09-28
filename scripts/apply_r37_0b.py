#!/usr/bin/env python3
from pathlib import Path
import sys

def die(msg):
    raise SystemExit("R37.0b ABORT: " + msg)

root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
path = root / "src" / "Controller" / "SongLabController.php"
if not path.is_file():
    die("src/Controller/SongLabController.php absent")

s = path.read_text(encoding="utf-8-sig")

s = s.replace("$jobs->queue($song,$user);", "$jobs->queue($song,$user,'align');", 1)

route_token = "name: 'app_song_lyricslab_extract'"
if route_token not in s:
    marker = "#[Route('/lyrics/status', name: 'app_song_lyricslab_status', methods: ['GET'])]"
    if marker not in s:
        die("ancre /lyrics/status introuvable")

    extract = r"""
#[Route('/lyrics/extract', name: 'app_song_lyricslab_extract', methods: ['POST'])]
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

"""
    s = s.replace(marker, extract + marker, 1)

old = "return $this->json(['job_id'=>$job->getId(),'status'=>$job->getStatus()->value,'progress'=>$job->getProgress(),'error'=>$job->getErrorCode()]);"
new = "return $this->json(['job_id'=>$job->getId(),'status'=>$job->getStatus()->value,'progress'=>$job->getProgress(),'error'=>$job->getErrorCode(),'mode'=>(string)($job->getRequestData()['mode']??'align')]);"
if old in s:
    s = s.replace(old, new, 1)

path.write_text(s, encoding="utf-8", newline="\n")

check = path.read_text(encoding="utf-8")
for token in [
    "app_song_lyricslab_extract",
    "$jobs->queue($song, $user, 'extract');",
]:
    if token not in check:
        die("token absent après patch: " + token)

print("R37_0B_APPLIED_OK")
