from __future__ import annotations

import json
import os
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path

WINDOWS_NO_WINDOW=getattr(subprocess,"CREATE_NO_WINDOW",0)

def _read_progress(path: Path) -> dict | None:
    try:
        if not path.is_file():
            return None
        data=json.loads(path.read_text(encoding="utf-8",errors="replace"))
        return data if isinstance(data,dict) else None
    except Exception:
        return None

def _discover_lyrics_python(engine, force: bool = False) -> str:
    # R38.13a: cache validated Lyrics Python for the whole Worker lifetime.
    # Do not re-import torch/whisper/CUDA before every lyrics job.
    cached = getattr(engine, "_lyrics_python_cache", None)
    if not force and isinstance(cached, dict):
        cached_python = str(cached.get("python") or "")
        if cached_python and Path(cached_python).is_file():
            engine.log(
                f"Python Lyrics (cache): {cached_python}"
                + (f" · {cached.get('gpu')}" if cached.get("gpu") else "")
            )
            return cached_python
        engine._lyrics_python_cache = None
    env={}
    try:
        env=engine.root.joinpath(".env.local").read_text(encoding="utf-8",errors="replace")
    except Exception:
        env=""

    configured=os.environ.get("EZSCORE_LYRICS_PYTHON")
    if not configured:
        for raw in str(env).splitlines():
            if raw.strip().startswith("EZSCORE_LYRICS_PYTHON="):
                configured=raw.split("=",1)[1].strip().strip('"').strip("'")
                break

    candidates=[]
    for candidate in [
        configured,
        getattr(engine,"engine_python",None),
        r"H:\EZScore\.venv-py313\Scripts\python.exe",
        str(engine.root/".venv-py313"/"Scripts"/"python.exe"),
        sys.executable,
        "python",
    ]:
        if candidate and candidate not in candidates:
            candidates.append(candidate)

    probe=(
        "import json,torch,whisper,sys;"
        "print(json.dumps({'python':sys.executable,'cuda':bool(torch.cuda.is_available()),"
        "'gpu':torch.cuda.get_device_name(0) if torch.cuda.is_available() else None}))"
    )

    failures=[]
    for candidate in candidates:
        try:
            p=subprocess.run(
                [candidate,"-c",probe],
                stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                text=True,encoding="utf-8",errors="replace",
                timeout=60,check=False,
                creationflags=WINDOWS_NO_WINDOW if os.name=="nt" else 0,
            )
            if p.returncode!=0:
                failures.append(f"{candidate}: {p.stderr.strip()[-240:]}")
                continue
            data=json.loads(p.stdout.strip().splitlines()[-1])
            if not data.get("cuda"):
                failures.append(f"{candidate}: CUDA indisponible")
                continue
            resolved_python = str(data["python"])
            engine._lyrics_python_cache = {
                "python": resolved_python,
                "gpu": data.get("gpu"),
                "validated_at": time.time(),
            }
            engine.log(f"Python Lyrics: {resolved_python} · {data.get('gpu')}")
            return resolved_python
        except Exception as exc:
            failures.append(f"{candidate}: {exc}")

    raise RuntimeError("Aucun Python Lyrics compatible Whisper+CUDA. "+ " | ".join(failures[-4:]))

def run_lyrics_job(engine,job:dict)->None:
    api=engine.api
    if api is None:
        raise RuntimeError("worker_api_missing")

    python=_discover_lyrics_python(engine)

    job_id=int(job["job_id"])
    song=job.get("song") or {}
    paths=job.get("paths") or {}
    request=job.get("request") or {}
    mode=str(request.get("mode") or "align").strip().lower()
    if mode not in {"extract","align"}:
        mode="align"

    engine.current_job={
        "job_id":job_id,
        "song_id":job.get("song_id"),
        "kind":"lyrics",
        "title":song.get("title"),
        "artist":song.get("artist"),
        "progress":1,
        "stage":"queued",
    }
    engine.app.events.put(("job",engine.current_job.copy()))
    engine.log(f"Job paroles #{job_id} pris ({mode}): {song.get('artist')} — {song.get('title')}")

    # R38.3: extraction may use the isolated lead vocal, but alignment must use
    # the original source so timestamps share the exact playback clock.
    if mode=="align":
        audio=paths.get("source")
        audio_kind="source"
    else:
        audio=paths.get("lead_vocals")
        audio_kind="lead_vocals"
        if not audio or not Path(str(audio)).is_file():
            audio=paths.get("source")
            audio_kind="source"
    if not audio or not Path(str(audio)).is_file():
        raise RuntimeError("lyrics_audio_source_missing")
    engine.log(f"Audio Lyrics ({mode}): {audio_kind} -> {audio}")

    result_file=paths.get("result_file")
    progress_file=paths.get("progress_file")
    if not result_file or not progress_file:
        raise RuntimeError("lyrics_job_paths_missing")

    command=[
        python,
        str(engine.root/"analysis"/"lyrics_timeline_analysis.py"),
        "--audio",str(audio),
        "--output",str(result_file),
        "--progress-file",str(progress_file),
        "--mode",mode,
    ]

    if mode=="align":
        vocal_audio=paths.get("lead_vocals")
        if vocal_audio and Path(str(vocal_audio)).is_file():
            command += ["--vocal-audio",str(vocal_audio)]
            engine.log(f"Détection onset vocal: lead_vocals -> {vocal_audio}")

    if mode=="align":
        lyrics_file=paths.get("lyrics_file")
        if not lyrics_file or not Path(str(lyrics_file)).is_file():
            raise RuntimeError("lyrics_file_missing")
        command += ["--lyrics-file",str(lyrics_file)]

    env=os.environ.copy()
    env["PYTHONUTF8"]="1"
    env["PYTHONIOENCODING"]="utf-8"

    progress_path=Path(str(progress_file))
    result_path=Path(str(result_file))
    progress_path.parent.mkdir(parents=True,exist_ok=True)
    result_path.parent.mkdir(parents=True,exist_ok=True)
    progress_path.unlink(missing_ok=True)
    result_path.unlink(missing_ok=True)

    engine.log("Commande LYRICS lancée.")
    try:
        proc=subprocess.Popen(
            command,cwd=str(engine.root),env=env,
            stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
            text=True,encoding="utf-8",errors="replace",bufsize=1,
            creationflags=WINDOWS_NO_WINDOW if os.name=="nt" else 0,
        )
    except (FileNotFoundError, OSError) as exc:
        # Invalidate only when the interpreter itself can no longer be launched.
        engine.log(f"Python Lyrics cache invalidé au lancement: {exc}")
        engine._lyrics_python_cache = None
        python = _discover_lyrics_python(engine, force=True)
        command[0] = python
        proc=subprocess.Popen(
            command,cwd=str(engine.root),env=env,
            stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
            text=True,encoding="utf-8",errors="replace",bufsize=1,
            creationflags=WINDOWS_NO_WINDOW if os.name=="nt" else 0,
        )
    engine.current_process=proc

    outq:queue.Queue[str|None]=queue.Queue()
    def reader():
        if proc.stdout is None:
            outq.put(None);return
        try:
            for line in proc.stdout:
                outq.put(line.rstrip())
        finally:
            outq.put(None)
    threading.Thread(target=reader,daemon=True).start()

    lyrics_output_tail=[]
    last_progress=-1
    last_db_update=0.0
    last_heartbeat=0.0

    try:
        while proc.poll() is None:
            if engine.stop_event.is_set():
                proc.terminate()
                break

            while True:
                try:
                    line=outq.get_nowait()
                except queue.Empty:
                    break
                if line:
                    lyrics_output_tail.append(line)
                    lyrics_output_tail=lyrics_output_tail[-12:]
                    engine.log("[LYRICS] "+line)

            current=_read_progress(progress_path)
            if current:
                pct=int(current.get("percent",0))
                engine.current_job["progress"]=pct
                engine.current_job["stage"]=current.get("stage")
                engine.current_job["message"]=current.get("message")
                engine.app.events.put(("progress",current))

                now=time.monotonic()
                if pct!=last_progress and now-last_db_update>=0.5:
                    try:
                        api.post(
                            f"/internal/analysis/desktop/jobs/{job_id}/progress",
                            {"progress":pct},
                            timeout=10,
                        )
                    except Exception as exc:
                        engine.log(f"Progression paroles non publiée: {exc}")
                    last_progress=pct
                    last_db_update=now

            now=time.monotonic()
            if now-last_heartbeat>=2.0:
                try:
                    engine._send_heartbeat("busy")
                except Exception as exc:
                    engine.log(f"Heartbeat paroles impossible: {exc}")
                last_heartbeat=now

            time.sleep(0.25)

        rc=proc.wait()

        while True:
            try:
                line=outq.get_nowait()
            except queue.Empty:
                break
            if line:
                lyrics_output_tail.append(line)
                lyrics_output_tail=lyrics_output_tail[-12:]
                engine.log("[LYRICS] "+line)
    finally:
        engine.current_process=None

    if rc==0 and result_path.is_file():
        try:
            api.post(f"/internal/analysis/desktop/jobs/{job_id}/complete",{},timeout=30)
            engine.log(f"Job paroles #{job_id} terminé.")
            engine.app.events.put(("progress",{"percent":100,"stage":"complete","message":"Paroles terminées"}))
        except Exception as exc:
            engine.log(f"Validation finale paroles #{job_id} impossible: {exc}")
            try:
                api.post(f"/internal/analysis/desktop/jobs/{job_id}/fail",{"error":str(exc)[:400]},timeout=10)
            except Exception:
                pass
    else:
        tail=" | ".join(lyrics_output_tail[-6:]).strip()
        error=(f"lyrics_python_exit_{rc}: {tail}" if tail else f"lyrics_python_exit_{rc}")[:400]
        engine.log(f"Job paroles #{job_id} en échec: {error}")
        try:
            api.post(f"/internal/analysis/desktop/jobs/{job_id}/fail",{"error":error},timeout=10)
        except Exception:
            pass

    engine.current_job=None
    engine.app.events.put(("job",None))
