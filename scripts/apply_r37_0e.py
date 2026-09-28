#!/usr/bin/env python3
from pathlib import Path
import sys

def die(msg):
    raise SystemExit("R37.0e ABORT: " + msg)

root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
path = root / "src" / "Controller" / "AnalysisDesktopController.php"
if not path.is_file():
    die("src/Controller/AnalysisDesktopController.php absent")

s = path.read_text(encoding="utf-8-sig")

if "ezscore.lyrics.extract.r37" not in s:
    old = r"""
        if ($job->getKind() === SongLyricsJobService::KIND) {
            try {
                $result=$this->lyricsStorage->readResult($job->getSong());
                $summary=$this->lyricsResults->apply($job->getSong(),$result);
                $this->lyricsJobs->complete($job,$summary);
            } catch (\Throwable $error) {
                $this->lyricsJobs->fail($job,$error->getMessage());
                return $this->json(['error'=>$error->getMessage()],Response::HTTP_CONFLICT);
            }
            return $this->json(['job_id'=>$job->getId(),'status'=>'completed','progress'=>100]);
        }
"""

    new = r"""
        if ($job->getKind() === SongLyricsJobService::KIND) {
            try {
                $result = $this->lyricsStorage->readResult($job->getSong());
                $mode = (string) ($job->getRequestData()['mode'] ?? ($result['mode'] ?? 'align'));

                if ($mode === 'extract') {
                    $text = trim((string) ($result['text'] ?? ''));
                    if ($text === '') {
                        throw new \RuntimeException('lyrics_extract_empty');
                    }

                    $job->getSong()->setLyricsSourceText($text);
                    $this->em->flush();

                    $summary = [
                        'schema_version' => 'ezscore.lyrics.extract.r37',
                        'mode' => 'extract',
                        'characters' => mb_strlen($text),
                        'recognized_words' => (int) ($result['recognized_words'] ?? 0),
                        'languages' => $result['languages'] ?? [],
                        'model' => $result['model'] ?? null,
                    ];
                } else {
                    $summary = $this->lyricsResults->apply($job->getSong(), $result);
                    $summary['mode'] = 'align';
                    $summary['languages'] = $result['languages'] ?? [];
                    $summary['model'] = $result['model'] ?? null;
                }

                $this->lyricsJobs->complete($job, $summary);
            } catch (\Throwable $error) {
                $this->lyricsJobs->fail($job, $error->getMessage());
                return $this->json(['error' => $error->getMessage()], Response::HTTP_CONFLICT);
            }

            return $this->json([
                'job_id' => $job->getId(),
                'status' => 'completed',
                'progress' => 100,
                'mode' => $mode,
            ]);
        }
"""

    if old not in s:
        die("bloc completion Lyrics attendu introuvable")
    s = s.replace(old, new, 1)

path.write_text(s, encoding="utf-8", newline="\n")

check = path.read_text(encoding="utf-8")
for token in [
    "ezscore.lyrics.extract.r37",
    "setLyricsSourceText($text)",
    "$mode === 'extract'",
    "$this->lyricsResults->apply($job->getSong(), $result)",
]:
    if token not in check:
        die("token absent après patch: " + token)

print("R37_0E_APPLIED_OK")
