#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import subprocess, shutil, sys

BASE="d2a7dc22588044c81f67f8610f4b9820620e91c4"

def abort(msg): raise SystemExit("R35.1 ABORT: "+msg)
def one(s,old,new,label):
    if s.count(old)!=1: abort(f"anchor {label}: {s.count(old)} occurrence(s)")
    return s.replace(old,new,1)
def write(p,s): p.write_text(s,encoding="utf-8",newline="\n")

def patch_worker(root):
    p=root/'worker_app'/'ezscore_analysis_worker.pyw';s=p.read_text(encoding='utf-8-sig')
    s=one(s,'APP_VERSION = "R33.2"','APP_VERSION = "R35.1"','worker version')
    s=one(s,'        self.stop_event = threading.Event()\n        self.current_process: subprocess.Popen | None = None','        self.stop_event = threading.Event()\n        self.thread: threading.Thread | None = None\n        self.current_process: subprocess.Popen | None = None','thread field')
    old='''    def start(self) -> None:\n        if self.running:\n            return\n        self.stop_event.clear()\n        self.running = True\n        threading.Thread(target=self._loop, name="worker-loop", daemon=True).start()\n\n    def request_stop(self) -> None:\n        self.stop_event.set()\n        self.running = False\n'''
    new='''    def start(self) -> None:\n        if self.running or (self.thread is not None and self.thread.is_alive()):\n            return\n        self.stop_event.clear()\n        self.running = True\n        self.thread = threading.Thread(target=self._loop, name="worker-loop", daemon=True)\n        self.thread.start()\n\n    def request_stop(self) -> None:\n        self.stop_event.set()\n\n    def stop_and_wait(self, timeout: float = 30.0) -> bool:\n        if self.current_job is not None:\n            return False\n        self.request_stop()\n        thread = self.thread\n        if thread is not None and thread.is_alive():\n            thread.join(timeout=timeout)\n        if thread is not None and thread.is_alive():\n            return False\n        self.thread = None\n        self.running = False\n        return True\n\n    def restart(self) -> bool:\n        if self.current_job is not None:\n            return False\n        if not self.stop_and_wait():\n            return False\n        self.start()\n        return True\n'''
    s=one(s,old,new,'worker lifecycle')
    old='''        ttk.Button(buttons, text="Démarrer", command=self._start).pack(side="left", padx=4)\n        ttk.Button(buttons, text="Pause / Reprendre", command=self._toggle_pause).pack(side="left", padx=4)\n'''
    new='''        self.worker_button = ttk.Button(buttons, text="Démarrer Worker", command=self._worker_action)\n        self.worker_button.pack(side="left", padx=4)\n        ttk.Button(buttons, text="Démarrer serveur", command=self._start_server).pack(side="left", padx=4)\n        ttk.Button(buttons, text="Arrêter serveur", command=self._stop_server).pack(side="left", padx=4)\n        ttk.Button(buttons, text="Pause / Reprendre", command=self._toggle_pause).pack(side="left", padx=4)\n'''
    s=one(s,old,new,'buttons')
    old='''    def _start(self):\n        if self.engine.running:\n            return\n        self._append("Démarrage du worker desktop…")\n        self.engine.start()\n\n    def _toggle_pause(self):\n'''
    new='''    def _refresh_worker_button(self):\n        if self.engine.current_job is not None:\n            self.worker_button.configure(text="Worker occupé", state="disabled")\n        elif self.engine.running:\n            self.worker_button.configure(text="Redémarrer Worker", state="normal")\n        else:\n            self.worker_button.configure(text="Démarrer Worker", state="normal")\n\n    def _worker_action(self):\n        if self.engine.current_job is not None:\n            messagebox.showwarning("EZScore Analysis Worker", "Un job est actif. Le Worker ne peut pas être redémarré.")\n            return\n        if self.engine.running:\n            self._append("Attente de la fin réelle de l'ancien thread Worker…")\n            if not self.engine.restart():\n                messagebox.showerror("EZScore Analysis Worker", "L'ancien thread ne s'est pas arrêté proprement. Relance annulée.")\n                return\n        else:\n            self._start()\n        self._refresh_worker_button()\n\n    def _start(self):\n        if self.engine.running:\n            return\n        self._append("Démarrage du worker desktop…")\n        self.engine.start()\n        self._refresh_worker_button()\n\n    def _start_server(self):\n        alive, _ = local_server_alive()\n        if alive: return\n        script=project_root()/"scripts"/"start_ezscore_web.ps1"\n        subprocess.Popen(["powershell","-ExecutionPolicy","Bypass","-File",str(script),"-Port","8501"],cwd=str(project_root()),creationflags=WINDOWS_NO_WINDOW if os.name=="nt" else 0)\n        self._append("Démarrage du serveur local demandé.")\n\n    def _stop_server(self):\n        pid=local_server_pid(project_root())\n        if not pid: return\n        subprocess.run(["powershell","-NoProfile","-Command",f"Stop-Process -Id {pid} -Force -ErrorAction SilentlyContinue"],cwd=str(project_root()),check=False,creationflags=WINDOWS_NO_WINDOW if os.name=="nt" else 0)\n        self._append("Arrêt du serveur local demandé.")\n\n    def _ensure_server_then_start(self):\n        alive,_=local_server_alive()\n        if not alive:\n            self._start_server()\n            for _ in range(40):\n                alive,_=local_server_alive()\n                if alive: break\n                time.sleep(0.25)\n        self._start()\n\n    def _toggle_pause(self):\n'''
    s=one(s,old,new,'worker actions')
    s=one(s,'            elif kind == "status":\n                self.status_var.set(str(payload))','            elif kind == "status":\n                self.status_var.set(str(payload))\n                self._refresh_worker_button()','status refresh')
    s=one(s,'            elif kind == "job":\n                if payload:','            elif kind == "job":\n                self._refresh_worker_button()\n                if payload:','job refresh')
    s=one(s,'    def run(self):\n        self.root.after(400, self._start)\n        self.root.mainloop()','    def run(self):\n        self.root.after(250, self._ensure_server_then_start)\n        self.root.mainloop()','autostart')
    write(p,s)

def patch_meter(root,bundle):
    shutil.copy2(bundle/'analysis'/'meter_detection_r35_1.py',root/'analysis'/'meter_detection_r35_1.py')
    p=root/'analysis'/'chord_timeline_analysis.py';s=p.read_text(encoding='utf-8')
    s=one(s,'import librosa\n','import librosa\nfrom meter_detection_r35_1 import detect_meter\n','meter import')
    old='''    signature=detect_signature(onset,beat_frames) if requested_signature=="auto" else requested_signature\n    bpm=numerator(signature)\n    phase,phase_conf=detect_downbeat_phase(onset,beat_frames,bpm)\n'''
    new='''    bass_y=None\n    bass_path=next((p for p in harmonic if "bass" in Path(p).stem.lower()),None)\n    if bass_path:\n        bass_y,_=librosa.load(str(bass_path),sr=sr,mono=True);bass_y=librosa.util.normalize(bass_y)\n    if requested_signature=="auto":\n        metric=detect_meter(rhythm_y=yr,harmonic_y=yh,bass_y=bass_y,sr=sr,hop=hop,onset=onset,beat_frames=beat_frames)\n        signature=metric.signature;phase=metric.phase;phase_conf=metric.confidence\n        metric_scores=metric.scores;metric_sources=metric.sources\n    else:\n        signature=requested_signature\n        bpm_override=numerator(signature);phase,phase_conf=detect_downbeat_phase(onset,beat_frames,bpm_override)\n        metric_scores={signature:1.0};metric_sources={"rhythm":rhythm_source,"bass":"manual_signature","harmony":harmonic_source}\n    bpm=numerator(signature)\n'''
    s=one(s,old,new,'meter invocation')
    s=one(s,'        "downbeat_confidence":round(float(phase_conf),4),\n        "beats":beats,','        "downbeat_confidence":round(float(phase_conf),4),\n        "meter_candidates":metric_scores,\n        "meter_sources":metric_sources,\n        "beats":beats,','meter diagnostics')
    write(p,s)

def patch_storage(root):
    p=root/'src'/'Service'/'ChordTimelineStorage.php';s=p.read_text(encoding='utf-8')
    anchor='\n    public function readResult(Song $song): array\n'
    addition='''\n    public function deleteForSong(Song $song): void\n    {\n        $dir=$this->projectDir.DIRECTORY_SEPARATOR.'var'.DIRECTORY_SEPARATOR.'storage'.DIRECTORY_SEPARATOR.'chords'.DIRECTORY_SEPARATOR.'song-'.(int)$song->getId();\n        if (!is_dir($dir)) return;\n        $it=new \\RecursiveIteratorIterator(new \\RecursiveDirectoryIterator($dir,\\FilesystemIterator::SKIP_DOTS),\\RecursiveIteratorIterator::CHILD_FIRST);\n        foreach ($it as $item) { if ($item->isDir()) @rmdir($item->getPathname()); else @unlink($item->getPathname()); }\n        @rmdir($dir);\n    }\n'''
    s=one(s,anchor,addition+anchor,'chord delete');write(p,s)
    p=root/'src'/'Domain'/'Song'/'SongTimelineEventRepository.php';s=p.read_text(encoding='utf-8')
    anchor='\n    public function deleteMusicalAnalysisForSong(Song $song): void\n'
    addition='''\n    public function deleteAllForSong(Song $song): void\n    {\n        $this->createQueryBuilder('e')->delete()->andWhere('e.song = :song')->setParameter('song', $song)->getQuery()->execute();\n    }\n'''
    s=one(s,anchor,addition+anchor,'timeline delete all');write(p,s)

def patch_reimport(root):
    p=root/'src'/'Controller'/'SongImportController.php';s=p.read_text(encoding='utf-8')
    s=one(s,'use App\\Service\\SongImportStorage;\n','use App\\Service\\SongImportStorage;\nuse App\\Service\\SongStemStorage;\nuse App\\Service\\ChordTimelineStorage;\nuse App\\Domain\\Song\\SongTimelineEventRepository;\n','imports')
    anchor='\n    private function buildSong(Request $request, User $user, UserRepository $users): Song\n'
    method=r'''\n    #[Route('/song/{id}/reimport', name: 'app_song_reimport', requirements: ['id' => '\\d+'], methods: ['POST'])]\n    public function reimport(Song $song, Request $request, SongImportStorage $storage, SongStemStorage $stems, ChordTimelineStorage $chords, SongTimelineEventRepository $timeline, EntityManagerInterface $em): Response\n    {\n        $user=$this->getUser();\n        $canEdit=$user instanceof User && ($this->isGranted('ROLE_ADMIN') || ($this->isGranted('ROLE_EDITOR') && $song->getEditor()?->getId()===$user->getId()));\n        if (!$canEdit) throw $this->createAccessDeniedException();\n        if (!$this->isCsrfTokenValid('song_reimport_'.$song->getId(), (string)$request->request->get('_token'))) throw $this->createAccessDeniedException();\n        $audio=$request->files->get('audio');\n        if (!$audio instanceof UploadedFile || !$audio->isValid()) { $this->addFlash('error','Réimportation impossible : fichier audio invalide.'); return $this->redirectToRoute('app_song_workspace',['_locale'=>$request->getLocale(),'id'=>$song->getId()]); }\n        $audioData=$storage->storeAudio($audio);\n        $timeline->deleteAllForSong($song); $stems->deleteForSong($song); $chords->deleteForSong($song);\n        $song->setImportedAudio($audioData['original_name'],$audioData['storage_path'],$audioData['mime_type'],$audioData['size'],$audioData['sha256']);\n        $song->markImported(); $em->flush();\n        $this->addFlash('success','Audio réimporté ; analyses invalidées ; état revenu à Importée.');\n        return $this->redirectToRoute('app_song_workspace',['_locale'=>$request->getLocale(),'id'=>$song->getId()]);\n    }\n'''.replace('\\n','\n')
    s=one(s,anchor,method+anchor,'reimport route');write(p,s)
    p=root/'templates'/'song'/'workspace.html.twig';s=p.read_text(encoding='utf-8')
    anchor='''        <div class="song-workspace-actions">\n'''
    addition='''        <div class="song-workspace-actions">\n            {% if can_edit %}\n            <form method="post" enctype="multipart/form-data" action="{{ path('app_song_reimport', {'_locale': app.request.locale, id: song.id}) }}" onsubmit="return confirm('ATTENTION : la réimportation remplace l’audio source et SUPPRIME/INVALIDE stems, accords, paroles, alignements et artefacts dérivés. Les métadonnées éditoriales sont conservées. Continuer ?');">\n                <input type="hidden" name="_token" value="{{ csrf_token('song_reimport_' ~ song.id) }}">\n                <input type="file" name="audio" accept=".mp3,.wav,.ogg,.m4a,.flac,audio/*" required>\n                <button type="submit" class="danger-button">Réimporter</button>\n            </form>\n            {% endif %}\n'''
    s=one(s,anchor,addition,'reimport form');write(p,s)

def patch_catalog(root):
    p=root/'templates'/'catalog'/'index.html.twig';s=p.read_text(encoding='utf-8')
    marker='{% for song in songs %}\n'
    inject='''{% for song in songs %}\n        {# R35.1_ROLE_ACTIONS: Ouvrir = final publié; Démo = public/test; Éditer = workflow. #}\n        {% set r35_published = song.status.value == 'published' %}\n        {% set r35_admin = is_granted('ROLE_ADMIN') %}\n        {% set r35_editor = is_granted('ROLE_EDITOR') %}\n        {% set r35_anonymous = not app.user %}\n'''
    s=one(s,marker,inject,'catalog role contract')
    write(p,s)

def main():
    root=Path(sys.argv[1] if len(sys.argv)>1 else '.').resolve();bundle=Path(__file__).resolve().parents[1]
    if not (root/'composer.json').is_file():abort('composer.json introuvable')
    try: head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
    except Exception: head=None
    if head and head!=BASE:abort(f'HEAD={head}; attendu {BASE}')
    patch_worker(root);patch_meter(root,bundle);patch_storage(root);patch_reimport(root);patch_catalog(root)
    print('R35.1_APPLIED_OK')
if __name__=='__main__':main()
