from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys

BASE_COMMITS = {
    "535ac59dbbb4797d41779ca0c36ba102d81712c2",  # R34.6 TEMPO TYPOGRAPHY
    "09cdb62ee2fab2defe65c214e2e32f038b57234d",  # accidental R35.2 bundle commit; source base still R34.6
}


def abort(message: str) -> None:
    raise SystemExit("R35.2 ABORT: " + message)


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        abort(f"anchor {label!r}: attendu 1, trouvé {count}")
    return text.replace(old, new, 1)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="\n")


def assert_base(root: Path) -> None:
    try:
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    except Exception as exc:
        abort(f"git rev-parse impossible: {exc}")
    if head not in BASE_COMMITS:
        abort(f"HEAD={head}; R35.2 attend une base R34.6 connue: {sorted(BASE_COMMITS)}")


def install_meter(root: Path, bundle: Path) -> None:
    shutil.copy2(bundle / "analysis" / "meter_detection_r35_2.py",
                 root / "analysis" / "meter_detection_r35_2.py")


def patch_repository(root: Path) -> None:
    p = root / "src/Domain/Analysis/AnalysisJobRepository.php"
    s = read(p)
    anchor = "\n    public function findNextQueued(): ?AnalysisJob\n"
    addition = r'''
    /** @return list<AnalysisJob> */
    public function findDesktopQueue(int $limit = 100): array
    {
        return $this->createQueryBuilder('job')
            ->leftJoin('job.song', 'song')
            ->addSelect('song')
            ->andWhere('job.status IN (:statuses)')
            ->setParameter('statuses', [
                AnalysisJobStatus::Queued->value,
                AnalysisJobStatus::Running->value,
            ])
            ->orderBy('job.status', 'DESC')
            ->addOrderBy('job.createdAt', 'ASC')
            ->addOrderBy('job.id', 'ASC')
            ->setMaxResults(max(1, min(500, $limit)))
            ->getQuery()
            ->getResult();
    }
'''
    s = replace_once(s, anchor, addition + anchor, "AnalysisJobRepository.findDesktopQueue")
    write(p, s)


def patch_desktop_controller(root: Path) -> None:
    p = root / "src/Controller/AnalysisDesktopController.php"
    s = read(p)
    s = replace_once(
        s,
        "use App\\Domain\\Analysis\\AnalysisJobStatus;\n",
        "use App\\Domain\\Analysis\\AnalysisJobStatus;\nuse App\\Domain\\Analysis\\AnalysisJobRepository;\n",
        "AnalysisJobRepository import",
    )
    s = replace_once(
        s,
        "        private readonly AnalysisDesktopStateStore $state,\n",
        "        private readonly AnalysisDesktopStateStore $state,\n        private readonly AnalysisJobRepository $jobs,\n",
        "AnalysisJobRepository ctor",
    )
    anchor = "\n    #[Route('/jobs/claim', name: 'internal_analysis_desktop_job_claim', methods: ['POST'])]\n"
    method = r'''
    #[Route('/jobs/queue', name: 'internal_analysis_desktop_job_queue', methods: ['GET'])]
    public function queue(Request $request): JsonResponse
    {
        $this->guard->assertAuthorized($request);
        $rows = [];
        foreach ($this->jobs->findDesktopQueue() as $job) {
            $song = $job->getSong();
            $rows[] = [
                'job_id' => $job->getId(),
                'kind' => $job->getKind(),
                'status' => $job->getStatus()->value,
                'progress' => $job->getProgress(),
                'song_id' => $song->getId(),
                'title' => $song->getTitle(),
                'artist' => $song->getArtist(),
            ];
        }
        return $this->json([
            'schema_version' => AnalysisDesktopStateStore::SCHEMA_VERSION,
            'jobs' => $rows,
        ]);
    }
'''
    s = replace_once(s, anchor, method + anchor, "desktop queue endpoint")
    write(p, s)


def patch_worker(root: Path) -> None:
    p = root / "worker_app/ezscore_analysis_worker.pyw"
    s = read(p)
    s = replace_once(s, 'APP_VERSION = "R33.2"', 'APP_VERSION = "R35.2"', "worker version")
    s = replace_once(
        s,
        "        self.stop_event = threading.Event()\n        self.current_process: subprocess.Popen | None = None\n",
        "        self.stop_event = threading.Event()\n        self.thread: threading.Thread | None = None\n        self.current_process: subprocess.Popen | None = None\n",
        "worker thread",
    )
    s = replace_once(
        s,
'''    def start(self) -> None:
        if self.running:
            return
        self.stop_event.clear()
        self.running = True
        threading.Thread(target=self._loop, name="worker-loop", daemon=True).start()

    def request_stop(self) -> None:
        self.stop_event.set()
        self.running = False
''',
'''    def start(self) -> None:
        if self.running or (self.thread is not None and self.thread.is_alive()):
            return
        self.stop_event.clear()
        self.running = True
        self.thread = threading.Thread(target=self._loop, name="worker-loop", daemon=True)
        self.thread.start()

    def request_stop(self) -> None:
        self.stop_event.set()

    def stop_and_wait(self, timeout: float = 30.0) -> bool:
        if self.current_job is not None:
            return False
        self.request_stop()
        thread = self.thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=timeout)
        if thread is not None and thread.is_alive():
            return False
        self.thread = None
        self.running = False
        return True

    def restart(self) -> bool:
        if self.current_job is not None:
            return False
        if not self.stop_and_wait():
            return False
        self.start()
        return True
''',
        "worker lifecycle",
    )
    s = replace_once(
        s,
        "            last_heartbeat = 0.0\n            last_claim = 0.0\n",
        "            last_heartbeat = 0.0\n            last_claim = 0.0\n            last_queue_refresh = 0.0\n",
        "queue timer init",
    )
    s = replace_once(
        s,
'''                if not self.paused and self.current_job is None and now - last_claim >= CLAIM_SECONDS:
                    job = self.api.post("/internal/analysis/desktop/jobs/claim", {})
                    last_claim = now
                    if job:
                        self._run_job(job)

                time.sleep(0.15)
''',
'''                if now - last_queue_refresh >= 2.0:
                    try:
                        queue_state = self.api.get("/internal/analysis/desktop/jobs/queue", timeout=10)
                        self.app.events.put(("queue", (queue_state or {}).get("jobs", [])))
                    except Exception as exc:
                        self.log(f"Lecture file d'attente impossible: {exc}")
                    last_queue_refresh = now

                if not self.paused and self.current_job is None and now - last_claim >= CLAIM_SECONDS:
                    job = self.api.post("/internal/analysis/desktop/jobs/claim", {})
                    last_claim = now
                    if job:
                        self._run_job(job)

                time.sleep(0.15)
''',
        "queue polling",
    )
    s = replace_once(
        s,
'''        ttk.Button(buttons, text="Démarrer", command=self._start).pack(side="left", padx=4)
        ttk.Button(buttons, text="Pause / Reprendre", command=self._toggle_pause).pack(side="left", padx=4)
''',
'''        self.worker_button = ttk.Button(buttons, text="Démarrer Worker", command=self._worker_action)
        self.worker_button.pack(side="left", padx=4)
        self.server_start_button = ttk.Button(buttons, text="Démarrer serveur", command=self._start_server)
        self.server_start_button.pack(side="left", padx=4)
        self.server_stop_button = ttk.Button(buttons, text="Arrêter serveur", command=self._stop_server)
        self.server_stop_button.pack(side="left", padx=4)
        ttk.Button(buttons, text="Pause / Reprendre", command=self._toggle_pause).pack(side="left", padx=4)
''',
        "worker/server buttons",
    )
    # Insert persistent queue panel between current job and console.
    queue_anchor = '''        console_box = ttk.LabelFrame(self.root, text="Console temps réel", padding=8)
'''
    queue_panel = '''        queue_box = ttk.LabelFrame(self.root, text="Traitements en cours / à faire", padding=8)
        queue_box.pack(fill="x", padx=12, pady=(0, 10))
        columns = ("id", "etat", "type", "chanson", "progression")
        self.queue_tree = ttk.Treeview(queue_box, columns=columns, show="headings", height=6)
        headings = {"id": "#", "etat": "État", "type": "Traitement", "chanson": "Chanson", "progression": "Progression"}
        widths = {"id": 55, "etat": 95, "type": 95, "chanson": 560, "progression": 105}
        for name in columns:
            self.queue_tree.heading(name, text=headings[name])
            self.queue_tree.column(name, width=widths[name], anchor="w")
        queue_scroll = ttk.Scrollbar(queue_box, orient="vertical", command=self.queue_tree.yview)
        self.queue_tree.configure(yscrollcommand=queue_scroll.set)
        self.queue_tree.grid(row=0, column=0, sticky="nsew")
        queue_scroll.grid(row=0, column=1, sticky="ns")
        queue_box.columnconfigure(0, weight=1)

'''
    s = replace_once(s, queue_anchor, queue_panel + queue_anchor, "queue UI panel")
    s = replace_once(
        s,
'''    def _start(self):
        if self.engine.running:
            return
        self._append("Démarrage du worker desktop…")
        self.engine.start()

    def _toggle_pause(self):
''',
'''    def _refresh_worker_button(self):
        if self.engine.current_job is not None:
            self.worker_button.configure(text="Worker occupé", state="disabled")
        elif self.engine.running:
            self.worker_button.configure(text="Redémarrer Worker", state="normal")
        else:
            self.worker_button.configure(text="Démarrer Worker", state="normal")

    def _worker_action(self):
        if self.engine.current_job is not None:
            messagebox.showwarning("EZScore Analysis Worker", "Un traitement est actif. Redémarrage interdit.")
            return
        if self.engine.running:
            self._append("Redémarrage Worker : attente de la fin réelle de l'ancien thread…")
            if not self.engine.restart():
                messagebox.showerror("EZScore Analysis Worker", "L'ancien Worker ne s'est pas arrêté. Relance annulée.")
                return
        else:
            self._start()
        self._refresh_worker_button()

    def _start(self):
        if self.engine.running:
            return
        self._append("Démarrage du worker desktop…")
        self.engine.start()
        self._refresh_worker_button()

    def _start_server(self):
        alive, _ = local_server_alive()
        if alive:
            return
        script = project_root() / "scripts" / "start_ezscore_web.ps1"
        subprocess.Popen(
            ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(script), "-Port", "8501"],
            cwd=str(project_root()),
            creationflags=WINDOWS_NO_WINDOW if os.name == "nt" else 0,
        )
        self._append("Démarrage du serveur local demandé.")

    def _stop_server(self):
        pid = local_server_pid(project_root())
        if not pid:
            return
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", f"Stop-Process -Id {pid} -Force -ErrorAction SilentlyContinue"],
            cwd=str(project_root()),
            check=False,
            creationflags=WINDOWS_NO_WINDOW if os.name == "nt" else 0,
        )
        self._append("Arrêt du serveur local demandé.")

    def _ensure_server_then_start(self):
        alive, _ = local_server_alive()
        if not alive:
            self._start_server()
            for _ in range(40):
                alive, _ = local_server_alive()
                if alive:
                    break
                time.sleep(0.25)
        self._start()

    def _render_queue(self, jobs):
        for item in self.queue_tree.get_children():
            self.queue_tree.delete(item)
        for job in jobs if isinstance(jobs, list) else []:
            status = str(job.get("status") or "")
            state = "EN COURS" if status == "running" else "À FAIRE"
            kind = {"stems": "Stems", "chords": "Accords", "lyrics": "Paroles"}.get(str(job.get("kind") or ""), str(job.get("kind") or "—"))
            song = f"{job.get('artist') or ''} — {job.get('title') or ''}".strip(" —")
            progress = f"{int(job.get('progress') or 0)} %" if status == "running" else "—"
            self.queue_tree.insert("", "end", values=(job.get("job_id"), state, kind, song, progress))

    def _toggle_pause(self):
''',
        "worker actions and queue render",
    )
    s = replace_once(
        s,
'''            elif kind == "status":
                self.status_var.set(str(payload))
''',
'''            elif kind == "status":
                self.status_var.set(str(payload))
                self._refresh_worker_button()
''',
        "status button refresh",
    )
    s = replace_once(
        s,
'''            elif kind == "job":
                if payload:
''',
'''            elif kind == "queue":
                self._render_queue(payload)
            elif kind == "job":
                self._refresh_worker_button()
                if payload:
''',
        "queue event",
    )
    s = replace_once(
        s,
'''    def run(self):
        self.root.after(400, self._start)
        self.root.mainloop()
''',
'''    def run(self):
        self.root.after(250, self._ensure_server_then_start)
        self.root.mainloop()
''',
        "autostart server+worker",
    )
    write(p, s)


def patch_meter(root: Path) -> None:
    p = root / "analysis/chord_timeline_analysis.py"
    s = read(p)
    s = replace_once(s, "import librosa\n", "import librosa\nfrom meter_detection_r35_2 import detect_meter\n", "meter import")
    old = '''    signature=detect_signature(onset,beat_frames) if requested_signature=="auto" else requested_signature
    bpm=numerator(signature)
    phase,phase_conf=detect_downbeat_phase(onset,beat_frames,bpm)
'''
    new = '''    bass_y=None
    bass_path=next((p for p in harmonic if "bass" in Path(p).stem.lower()),None)
    if bass_path:
        bass_y,_=librosa.load(str(bass_path),sr=sr,mono=True)
        bass_y=librosa.util.normalize(bass_y)
    if requested_signature=="auto":
        metric=detect_meter(harmonic_y=yh,bass_y=bass_y,onset=onset,beat_frames=beat_frames,sr=sr,hop=hop)
        signature=metric.signature
        phase=metric.phase
        phase_conf=metric.confidence
        metric_scores=metric.scores
    else:
        signature=requested_signature
        bpm_manual=numerator(signature)
        phase,phase_conf=detect_downbeat_phase(onset,beat_frames,bpm_manual)
        metric_scores={signature:1.0}
    bpm=numerator(signature)
'''
    s = replace_once(s, old, new, "meter auto")
    s = replace_once(
        s,
        '''        "downbeat_confidence":round(float(phase_conf),4),
        "beats":beats,
''',
        '''        "downbeat_confidence":round(float(phase_conf),4),
        "meter_candidates":metric_scores,
        "beats":beats,
''',
        "meter diagnostics",
    )
    write(p, s)


def patch_reimport(root: Path) -> None:
    p = root / "src/Controller/SongImportController.php"
    s = read(p)
    s = replace_once(s,
        "use App\\Service\\SongImportStorage;\n",
        "use App\\Service\\SongImportStorage;\nuse App\\Service\\SongStemStorage;\nuse App\\Service\\ChordTimelineStorage;\nuse App\\Domain\\Song\\SongTimelineEventRepository;\n",
        "reimport imports")
    anchor = "\n    private function buildSong(Request $request, User $user, UserRepository $users): Song\n"
    method = r'''
    #[Route('/song/{id}/reimport', name: 'app_song_reimport', requirements: ['id' => '\d+'], methods: ['POST'])]
    public function reimport(
        Song $song,
        Request $request,
        SongImportStorage $storage,
        SongStemStorage $stems,
        ChordTimelineStorage $chords,
        SongTimelineEventRepository $timeline,
        EntityManagerInterface $em,
    ): Response {
        $user = $this->getUser();
        $canEdit = $user instanceof User && (
            $this->isGranted('ROLE_ADMIN')
            || ($this->isGranted('ROLE_EDITOR') && $song->getEditor()?->getId() === $user->getId())
        );
        if (!$canEdit) throw $this->createAccessDeniedException();
        if (!$this->isCsrfTokenValid('song_reimport_'.$song->getId(), (string) $request->request->get('_token'))) {
            throw $this->createAccessDeniedException();
        }
        $audio = $request->files->get('audio');
        if (!$audio instanceof UploadedFile || !$audio->isValid()) {
            $this->addFlash('error', 'Réimportation impossible : fichier audio invalide.');
            return $this->redirectToRoute('app_song_workspace', ['_locale'=>$request->getLocale(),'id'=>$song->getId()]);
        }
        $audioData = $storage->storeAudio($audio);
        $timeline->deleteAllForSong($song);
        $stems->deleteForSong($song);
        $chords->deleteForSong($song);
        $song->setImportedAudio($audioData['original_name'], $audioData['storage_path'], $audioData['mime_type'], $audioData['size'], $audioData['sha256']);
        $song->markImported();
        $em->flush();
        $this->addFlash('success', 'Audio réimporté ; analyses précédentes invalidées.');
        return $this->redirectToRoute('app_song_workspace', ['_locale'=>$request->getLocale(),'id'=>$song->getId()]);
    }
'''
    s = replace_once(s, anchor, method + anchor, "reimport route")
    write(p, s)

    p = root / "src/Domain/Song/SongTimelineEventRepository.php"
    s = read(p)
    anchor = "\n    public function deleteMusicalAnalysisForSong(Song $song): void\n"
    method = r'''
    public function deleteAllForSong(Song $song): void
    {
        $this->createQueryBuilder('e')->delete()->andWhere('e.song = :song')->setParameter('song', $song)->getQuery()->execute();
    }
'''
    s = replace_once(s, anchor, method + anchor, "delete timeline")
    write(p, s)

    p = root / "src/Service/ChordTimelineStorage.php"
    s = read(p)
    anchor = "\n    public function readResult(Song $song): array\n"
    method = r'''
    public function deleteForSong(Song $song): void
    {
        $dir=$this->projectDir.DIRECTORY_SEPARATOR.'var'.DIRECTORY_SEPARATOR.'storage'.DIRECTORY_SEPARATOR.'chords'.DIRECTORY_SEPARATOR.'song-'.(int)$song->getId();
        if (!is_dir($dir)) return;
        $it=new \RecursiveIteratorIterator(new \RecursiveDirectoryIterator($dir, \FilesystemIterator::SKIP_DOTS), \RecursiveIteratorIterator::CHILD_FIRST);
        foreach ($it as $item) { if ($item->isDir()) @rmdir($item->getPathname()); else @unlink($item->getPathname()); }
        @rmdir($dir);
    }
'''
    s = replace_once(s, anchor, method + anchor, "delete chords")
    write(p, s)

    p = root / "templates/song/workspace.html.twig"
    s = read(p)
    anchor = '''        <div class="song-workspace-actions">\n'''
    block = '''        <div class="song-workspace-actions">\n            {% if can_edit %}\n                <form method="post" enctype="multipart/form-data" action="{{ path('app_song_reimport', {'_locale': app.request.locale, id: song.id}) }}" onsubmit="return confirm('ATTENTION : la réimportation remplace l’audio source et invalide stems, accords, paroles, alignements et artefacts dérivés. Continuer ?');">\n                    <input type="hidden" name="_token" value="{{ csrf_token('song_reimport_' ~ song.id) }}">\n                    <input type="file" name="audio" accept=".mp3,.wav,.ogg,.m4a,.flac,audio/*" required>\n                    <button type="submit" class="danger-button">Réimporter</button>\n                </form>\n            {% endif %}\n'''
    s = replace_once(s, anchor, block, "reimport UI")
    write(p, s)


def patch_editor_labels(root: Path) -> None:
    p = root / "templates/catalog/index.html.twig"
    s = read(p)
    old = """                                <option value=\"0\">{{ 'catalog_admin.keep_editor'|trans({}, 'admin_catalog') }} — {{ song.editor.displayName }}</option>"""
    new = """                                <option value=\"0\">{{ song.editor.displayName }}</option>"""
    s = replace_once(s, old, new, "editor current label")
    old_none = """                                <option value=\"0\">{{ 'catalog_admin.keep_no_editor'|trans({}, 'admin_catalog') }}</option>"""
    new_none = """                                <option value=\"0\">—</option>"""
    s = replace_once(s, old_none, new_none, "editor none label")
    write(p, s)


def main() -> None:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    if not (root / "composer.json").is_file():
        abort(f"{root} n'est pas EZScore_v1")
    assert_base(root)
    bundle = Path(__file__).resolve().parents[1]
    install_meter(root, bundle)
    patch_repository(root)
    patch_desktop_controller(root)
    patch_worker(root)
    patch_meter(root)
    patch_reimport(root)
    patch_editor_labels(root)
    print("R35_2_APPLIED_OK")


if __name__ == "__main__":
    main()
