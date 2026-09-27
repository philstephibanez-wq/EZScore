#!/usr/bin/env python3
from pathlib import Path
import subprocess,sys
BASE='fff8806c6e603e78779790d7c80019c45c54ff95'
def die(m): raise SystemExit('R35.4 ABORT: '+m)
def rd(p): return p.read_text(encoding='utf-8-sig')
def wr(p,s): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(s,encoding='utf-8',newline='\n')
def rep(s,a,b,label):
    if a not in s: die('ancre absente: '+label)
    return s.replace(a,b,1)
root=Path(sys.argv[1] if len(sys.argv)>1 else '.').resolve()
head=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()
if head!=BASE: die(f'HEAD={head}; attendu {BASE}')
bundle=Path(__file__).resolve().parents[1]
for rel in ['src/Domain/Song/SongCollaborator.php','src/Domain/Song/SongCollaboratorRepository.php','src/Service/SongAccessPolicy.php','src/Domain/Contact/ContactMessage.php','src/Domain/Contact/ContactMessageRepository.php','src/Controller/ContactController.php','src/Controller/SongCollaborationController.php','templates/contact/admin.html.twig','templates/song/collaborators.html.twig','migrations/Version20260927093000.php']:
    wr(root/rel,rd(bundle/rel))

p=root/'src/Domain/Analysis/AnalysisJob.php'; s=rd(p)
a="    public function cancel(): self\n    {\n        $this->status = AnalysisJobStatus::Cancelled;"
b="    public function requeue(): self\n    {\n        $this->status = AnalysisJobStatus::Queued;\n        $this->progress = 0;\n        $this->errorCode = null;\n        $this->updatedAt = new \\DateTimeImmutable();\n        return $this;\n    }\n\n    public function cancel(): self\n    {\n        $this->status = AnalysisJobStatus::Cancelled;"
s=rep(s,a,b,'AnalysisJob requeue'); wr(p,s)

p=root/'src/Domain/Analysis/AnalysisJobRepository.php'; s=rd(p)
a="    public function findNextQueued(): ?AnalysisJob\n    {"
b="    public function findStaleRunning(\\DateTimeImmutable $cutoff): array\n    {\n        return $this->createQueryBuilder('job')->andWhere('job.status = :status')->andWhere('job.updatedAt < :cutoff')->setParameter('status', AnalysisJobStatus::Running->value)->setParameter('cutoff',$cutoff)->orderBy('job.updatedAt','ASC')->getQuery()->getResult();\n    }\n\n    public function findNextQueued(): ?AnalysisJob\n    {"
s=rep(s,a,b,'stale repo'); wr(p,s)

p=root/'src/Controller/AnalysisDesktopController.php'; s=rd(p)
s=rep(s,"        $this->guard->assertAuthorized($request);\n        $rows = [];","        $this->guard->assertAuthorized($request);\n        $this->recoverStaleJobs();\n        $rows = [];",'queue recovery')
s=rep(s,"        $this->guard->assertAuthorized($request);\n\n        $job = $this->chordJobs->claimNext() ?? $this->stemJobs->claimNext();","        $this->guard->assertAuthorized($request);\n        $this->recoverStaleJobs();\n\n        $job = $this->chordJobs->claimNext() ?? $this->stemJobs->claimNext();",'claim recovery')
anchor="    /**\n     * @return array<string,mixed>\n     */\n    private function jobContext"
helper="    private function recoverStaleJobs(): int\n    {\n        $count=0; $cutoff=(new \\DateTimeImmutable())->modify('-120 seconds');\n        foreach($this->jobs->findStaleRunning($cutoff) as $job){$job->requeue();++$count;}\n        if($count>0)$this->em->flush();\n        return $count;\n    }\n\n"+anchor
s=rep(s,anchor,helper,'recovery helper'); wr(p,s)

p=root/'src/Security/Acl/SongVoter.php'; s=rd(p)
s=s.replace("use App\\Domain\\User\\User;","use App\\Domain\\User\\User;\nuse App\\Service\\SongAccessPolicy;",1)
s=rep(s,"        private readonly AccessDecisionManagerInterface $accessDecisionManager,\n    ) {","        private readonly AccessDecisionManagerInterface $accessDecisionManager,\n        private readonly SongAccessPolicy $songAccess,\n    ) {",'voter ctor')
old="        $ownsSong = $subject->getEditor() instanceof User\n            && $subject->getEditor()->getId() === $user->getId();"
s=rep(s,old,"        $ownsSong = $this->songAccess->canEdit($subject,$user,false);",'voter access'); wr(p,s)

p=root/'src/Domain/Song/SongRepository.php'; s=rd(p)
old="        $qb = $this->baseCatalogQuery()\n            ->andWhere('(s.status = :published OR s.editor = :editor)')"
new="        $qb = $this->baseCatalogQuery()\n            ->leftJoin('App\\\\Domain\\\\Song\\\\SongCollaborator','sc','WITH','sc.song = s AND sc.user = :editor')\n            ->andWhere('(s.status = :published OR s.editor = :editor OR sc.id IS NOT NULL)')"
s=rep(s,old,new,'catalog delegated')
anchor="    private function baseCatalogQuery(): QueryBuilder\n    {"
helpers="    public function findByAudioSha256(string $sha256): ?Song { return $this->findOneBy(['audioSha256'=>$sha256]); }\n    public function findLikelyDuplicate(string $title,string $artist): array { return $this->createQueryBuilder('s')->andWhere('LOWER(TRIM(s.title)) = :title')->andWhere('LOWER(TRIM(s.artist)) = :artist')->setParameter('title',mb_strtolower(trim($title)))->setParameter('artist',mb_strtolower(trim($artist)))->orderBy('s.id','ASC')->getQuery()->getResult(); }\n\n"+anchor
s=rep(s,anchor,helpers,'duplicate helpers'); wr(p,s)

p=root/'src/Controller/SongImportController.php'; s=rd(p)
s=s.replace("use App\\Service\\ChordTimelineStorage;","use App\\Service\\ChordTimelineStorage;\nuse App\\Service\\SongAccessPolicy;\nuse App\\Domain\\Song\\SongRepository;",1)
s=rep(s,"        SongImportStorage $storage,\n        EntityManagerInterface $em,","        SongImportStorage $storage,\n        SongRepository $songs,\n        EntityManagerInterface $em,",'import repo')
a="                $audioData = $storage->storeAudio($audio);"
b="                $sha256=hash_file('sha256',$audio->getPathname());\n                $exact=is_string($sha256)?$songs->findByAudioSha256($sha256):null;\n                $likely=$songs->findLikelyDuplicate($song->getTitle(),$song->getArtist());\n                if(($exact||$likely) && !$request->request->getBoolean('confirm_duplicate')){\n                    $duplicate=$exact ?? $likely[0];\n                    $this->addFlash('error',sprintf('Doublon probable : %s — %s (#%d). Rechargez le fichier et confirmez seulement s’il s’agit réellement d’une autre version.',$duplicate->getArtist(),$duplicate->getTitle(),$duplicate->getId()));\n                    return $this->render('song/import.html.twig',['editors'=>$editors,'current_editor'=>$user,'status_choices'=>[SongStatus::Imported,SongStatus::Editing,SongStatus::Published],'duplicate_song'=>$duplicate]);\n                }\n                $audioData = $storage->storeAudio($audio);"
s=rep(s,a,b,'duplicate gate')
old="        SongTimelineEventRepository $timeline,\n        EntityManagerInterface $em,\n    ): Response {\n        $user = $this->getUser();\n        $canEdit = $user instanceof User && (\n            $this->isGranted('ROLE_ADMIN')\n            || ($this->isGranted('ROLE_EDITOR') && $song->getEditor()?->getId() === $user->getId())\n        );\n        if (!$canEdit) throw $this->createAccessDeniedException();"
new="        SongTimelineEventRepository $timeline,\n        SongAccessPolicy $songAccess,\n        EntityManagerInterface $em,\n    ): Response {\n        $user = $this->getUser();\n        if(!$user instanceof User || !$songAccess->canEdit($song,$user,$this->isGranted('ROLE_ADMIN'))) throw $this->createAccessDeniedException();"
s=rep(s,old,new,'reimport delegated'); wr(p,s)

p=root/'templates/song/import.html.twig'; s=rd(p)
if 'duplicate_song' not in s:
    s=s.replace('<form','{% if duplicate_song is defined and duplicate_song %}<div class="flash flash-error"><strong>Doublon probable :</strong> {{ duplicate_song.artist }} — {{ duplicate_song.title }} (#{{ duplicate_song.id }}). Rechargez le fichier et confirmez seulement s’il s’agit d’une autre version.</div>{% endif %}\n<form',1)
    s=s.replace('</form>','{% if duplicate_song is defined and duplicate_song %}<label><input type="checkbox" name="confirm_duplicate" value="1" required> Je confirme qu’il s’agit d’une autre version/interprétation.</label>{% endif %}</form>',1)
wr(p,s)

p=root/'templates/song/analysis_dashboard.html.twig'; s=rd(p)
s=s.replace(">Répertoire</a></header>",">Éditeurs</a> · <a href=\"{{ path('app_contact_admin', {'_locale':app.request.locale,'song':song.id}) }}\">Contacter l’admin</a> · <a href=\"{{ path('app_catalog', {'_locale': app.request.locale}) }}\">Répertoire</a></div></header>",1) if ">Répertoire</a></header>" in s else s
# safer explicit insertion before current Répertoire link
if "app_song_collaborators" not in s:
    s=s.replace("<a href=\"{{ path('app_catalog', {'_locale': app.request.locale}) }}\">Répertoire</a>","<div><a href=\"{{ path('app_song_collaborators', {'_locale':app.request.locale,id:song.id}) }}\">Éditeurs</a> · <a href=\"{{ path('app_contact_admin', {'_locale':app.request.locale,'song':song.id}) }}\">Contacter l’admin</a> · <a href=\"{{ path('app_catalog', {'_locale': app.request.locale}) }}\">Répertoire</a></div>",1)
wr(p,s)

p=root/'.env'; s=rd(p)
if 'EZSCORE_ADMIN_CONTACT_EMAIL=' not in s: s+="\nEZSCORE_ADMIN_CONTACT_EMAIL=xpertdev@hotmail.com\n"
wr(p,s)

p=root/'worker_app/ezscore_analysis_worker.pyw'; s=rd(p); s=s.replace('APP_VERSION = "R35.2"','APP_VERSION = "R35.4"',1); wr(p,s)
p=root/'readme.md'; s=rd(p); s+="\n\n## R35.4 RECOVERY + COLLAB + CONTACT\nJobs orphelins >120s requeue; propriétaire inchangé; délégations owner/admin; doublons import; contact admin indirect.\n"; wr(p,s)
print('R35_4_APPLIED_OK')
