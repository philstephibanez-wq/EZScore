#!/usr/bin/env python3
from pathlib import Path
import re, sys

def die(msg):
    raise SystemExit("R35.4a ABORT: " + msg)

def rd(p):
    return p.read_text(encoding="utf-8-sig")

def wr(p, s):
    p.write_text(s, encoding="utf-8", newline="\n")

root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()

required = [
    "src/Controller/ContactController.php",
    "src/Controller/SongCollaborationController.php",
    "src/Domain/Analysis/AnalysisJob.php",
    "src/Controller/AnalysisDesktopController.php",
    "templates/base.html.twig",
    "templates/song/analysis_dashboard.html.twig",
    "config/routes.yaml",
    "worker_app/ezscore_analysis_worker.pyw",
]
for rel in required:
    if not (root/rel).is_file():
        die(f"fichier absent: {rel}")

# 1) Register missing localized routes.
p = root/"config/routes.yaml"
s = rd(p)
if "localized_song_collaboration:" not in s:
    anchor = """localized_song_labs:
    resource: ../src/Controller/SongLabController.php
    type: attribute
    prefix:
        fr: /fr
        en: /en

"""
    block = anchor + """localized_song_collaboration:
    resource: ../src/Controller/SongCollaborationController.php
    type: attribute
    prefix:
        fr: /fr
        en: /en

localized_contact:
    resource: ../src/Controller/ContactController.php
    type: attribute
    prefix:
        fr: /fr
        en: /en

"""
    if anchor not in s:
        die("ancre routes localized_song_labs absente")
    s = s.replace(anchor, block, 1)
wr(p, s)

# 2) Global header contact link, authenticated users only.
p = root/"templates/base.html.twig"
s = rd(p)
if "app_contact_admin" not in s:
    anchor = """        <div class="ez-topbar-right">
            {{ ui.language_select() }}
"""
    repl = """        <div class="ez-topbar-right">
            {{ ui.language_select() }}
            <a class="ez-contact-admin-link" href="{{ path('app_contact_admin', {'_locale': app.request.locale}) }}" title="Contacter l’administrateur" aria-label="Contacter l’administrateur">✉ <span>Contacter l’admin</span></a>
"""
    if anchor not in s:
        die("ancre header ez-topbar-right absente")
    s = s.replace(anchor, repl, 1)
wr(p, s)

# 3) Remove song-dashboard contact link: global header owns it now.
p = root/"templates/song/analysis_dashboard.html.twig"
s = rd(p)
s = re.sub(
    r'\s*·\s*<a href="\{\{\s*path\(\'app_contact_admin\'.*?</a>',
    '',
    s,
    count=1,
    flags=re.S
)
wr(p, s)

# 4) Real lease heartbeat: active worker must refresh AnalysisJob.updatedAt even when progress is unchanged.
p = root/"src/Domain/Analysis/AnalysisJob.php"
s = rd(p)
if "public function touchLease()" not in s:
    anchor = """    public function requeue(): self
    {
"""
    method = """    public function touchLease(): self
    {
        $this->updatedAt = new \\DateTimeImmutable();
        return $this;
    }

"""
    if anchor not in s:
        die("R35.4 requeue absent dans AnalysisJob.php")
    s = s.replace(anchor, method + anchor, 1)
wr(p, s)

p = root/"src/Controller/AnalysisDesktopController.php"
s = rd(p)
if "touchLease()" not in s:
    anchor = """        $state = $this->state->updateHeartbeat($payload);
        $workerId = trim((string) ($payload['worker_id'] ?? ''));

        return $this->json([
"""
    repl = """        $state = $this->state->updateHeartbeat($payload);
        $workerId = trim((string) ($payload['worker_id'] ?? ''));

        $currentJob = $payload['current_job'] ?? null;
        $currentJobId = is_array($currentJob) ? (int) ($currentJob['job_id'] ?? 0) : 0;
        if ($currentJobId > 0) {
            $activeJob = $this->jobs->find($currentJobId);
            if ($activeJob instanceof AnalysisJob && $activeJob->getStatus() === AnalysisJobStatus::Running) {
                $activeJob->touchLease();
                $this->em->flush();
            }
        }

        return $this->json([
"""
    # replace heartbeat occurrence only: there are hello and heartbeat blocks.
    pos = s.find("#[Route('/heartbeat'")
    if pos < 0:
        die("route heartbeat absente")
    before, after = s[:pos], s[pos:]
    if anchor not in after:
        die("ancre heartbeat payload absente")
    after = after.replace(anchor, repl, 1)
    s = before + after
wr(p, s)

# 5) Worker queue UI: if the local worker owns a job, show it as EN COURS even during the next queue refresh.
p = root/"worker_app/ezscore_analysis_worker.pyw"
s = rd(p)
old = """        for job in jobs if isinstance(jobs, list) else []:
            status = str(job.get("status") or "")
            state = "EN COURS" if status == "running" else "À FAIRE"
"""
new = """        for job in jobs if isinstance(jobs, list) else []:
            status = str(job.get("status") or "")
            current_id = int((self.engine.current_job or {}).get("job_id") or 0)
            job_id = int(job.get("job_id") or 0)
            locally_running = current_id > 0 and current_id == job_id
            state = "EN COURS" if status == "running" or locally_running else "À FAIRE"
"""
if old in s:
    s = s.replace(old, new, 1)

old2 = """            progress = f"{int(job.get('progress') or 0)} %" if status == "running" else "—"
"""
new2 = """            progress_value = int(job.get("progress") or 0)
            if locally_running and self.engine.current_job:
                progress_value = int(self.engine.current_job.get("progress") or progress_value)
            progress = f"{progress_value} %" if status == "running" or locally_running else "—"
"""
if old2 in s:
    s = s.replace(old2, new2, 1)
wr(p, s)

# 6) CSS for header contact link, minimal and compatible with current header.
p = root/"public/assets/css/r35-4a-contact-header.css"
wr(p, """.ez-contact-admin-link{display:inline-flex;align-items:center;gap:.45rem;min-height:44px;padding:0 .85rem;border:1px solid rgba(255,255,255,.24);border-radius:12px;color:inherit;text-decoration:none;white-space:nowrap}.ez-contact-admin-link:hover{background:rgba(255,255,255,.08)}@media(max-width:900px){.ez-contact-admin-link span{display:none}}""")

p = root/"templates/base.html.twig"
s = rd(p)
if "/assets/css/r35-4a-contact-header.css" not in s:
    anchor = """    <link rel="stylesheet" href="/assets/css/r21-admin.css?v=20260925r21">
"""
    repl = anchor + """    <link rel="stylesheet" href="/assets/css/r35-4a-contact-header.css?v=20260927r35_4a">
"""
    if anchor not in s:
        die("ancre CSS base absente")
    s = s.replace(anchor, repl, 1)
wr(p, s)

# 7) README marker.
p = root/"readme.md"
s = rd(p)
if "R35.4a HOTFIX" not in s:
    s += """

## R35.4a HOTFIX
- routes Contact/Collaborateurs enregistrées ;
- contact admin déplacé dans l’entête globale authentifiée ;
- lease des jobs réellement rafraîchi par heartbeat Worker ;
- queue desktop cohérente avec le job local réellement en cours.
"""
wr(p, s)

print("R35_4A_APPLIED_OK")
