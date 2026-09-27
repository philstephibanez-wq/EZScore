#!/usr/bin/env python3
from pathlib import Path
import sys,re

def die(m): raise SystemExit('R35.5 ABORT: '+m)
def rd(p): return p.read_text(encoding='utf-8-sig')
def wr(p,s): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(s,encoding='utf-8',newline='\n')
root=Path(sys.argv[1] if len(sys.argv)>1 else '.').resolve()
for rel in ['src/Controller/ContactController.php','src/Controller/SongCollaborationController.php','src/Service/SongAccessPolicy.php','templates/base.html.twig','templates/song/analysis_dashboard.html.twig','templates/layout/song/_workflow_tabs.html.twig']:
    if not (root/rel).is_file(): die('fichier absent: '+rel)

# Base: Répertoire + CSS R35.5
p=root/'templates/base.html.twig'; s=rd(p)
s=s.replace("← {{ 'common.back'|trans({}, 'navigation') }}","← {{ 'nav.catalog'|trans }}")
if 'r35-5-ux.css' not in s:
    anchor='<link rel="stylesheet" href="/assets/css/r35-4a-contact-header.css?v=20260927r35_4a">'
    if anchor not in s: anchor='<link rel="stylesheet" href="/assets/css/r21-admin.css?v=20260925r21">'
    if anchor not in s: die('ancre CSS base absente')
    s=s.replace(anchor,anchor+'\n    <link rel="stylesheet" href="/assets/css/r35-5-ux.css?v=20260927r35_5">',1)
wr(p,s)

# Un seul onglet
wr(root/'templates/layout/song/_workflow_tabs.html.twig',"""{% set existing_song = song is defined and song and song.id %}
{% if existing_song %}
<nav class=\"workflow-tabs song-workflow-tabs dashboard-only-tab\" aria-label=\"Navigation chanson\">
<a class=\"workflow-tab {{ current|default('') == 'analysis' ? 'active' : '' }}\" href=\"{{ path('app_song_analysis_lab', {'_locale':app.request.locale,id:song.id}) }}\">Tableau de bord</a>
</nav>
{% endif %}
""")

# Dashboard nettoyé
wr(root/'templates/song/analysis_dashboard.html.twig',"""{% extends 'base.html.twig' %}
{% set wf = workflow %}
{% block title %}Tableau de bord - {{ song.title }} - EZScore_v1{% endblock %}
{% block stylesheets %}<link rel=\"stylesheet\" href=\"/assets/css/song-analysis-dashboard-r35-3.css?v=20260927r35_5\">{% endblock %}
{% block body %}
{% include 'layout/song/_workflow_tabs.html.twig' with {current:'analysis',song:song} %}
<header class=\"clean-dashboard-head\"><div class=\"eyebrow\">Tableau de bord de la chanson</div><h1>{{ song.title }}</h1><p class=\"page-note\">{{ song.artist }} · Suivi du workflow d’analyse et d’édition.</p></header>
<section class=\"analysis-dashboard-grid clean-dashboard-grid\">
{% set stages=[
{'label':'Import','route':null,'ready':wf.imported,'blocked':false},
{'label':'Stems','route':'app_song_stems','ready':wf.stems_ready,'blocked':not wf.can_stems},
{'label':'Accords','route':'app_song_chordslab','ready':wf.chords_ready,'blocked':not wf.can_chords},
{'label':'Paroles','route':'app_song_lyricslab','ready':wf.lyrics_ready,'blocked':not wf.can_lyrics},
{'label':'Publication','route':'app_song_publication_lab','ready':wf.published,'blocked':not wf.can_publish}
] %}
{% for stage in stages %}<article class=\"analysis-stage {{ stage.ready ? 'is-ready' : (stage.blocked ? 'is-blocked' : 'is-next') }}\"><div class=\"analysis-stage-status\">{{ stage.ready ? '✓' : (stage.blocked ? '•' : '→') }}</div><div><div class=\"eyebrow\">Étape {{ loop.index }}</div><h2>{{ stage.label }}</h2><p>{{ stage.ready ? 'Prêt' : (stage.blocked ? 'En attente de l’étape précédente' : 'À faire') }}</p>{% if stage.route and not stage.blocked %}<a href=\"{{ path(stage.route, {'_locale':app.request.locale,id:song.id}) }}\">Ouvrir</a>{% endif %}</div></article>{% endfor %}
</section>
<section class=\"panel analysis-summary clean-analysis-summary\"><div><span>État courant</span><strong>{{ wf.next == 'done' ? 'Terminé' : wf.next|upper }}</strong></div><div><span>Signature</span><strong>{{ song.timeSignature }}</strong></div><div><span>Capo</span><strong>{{ song.capo }}</strong></div><div><span>SHA audio</span><strong>{{ song.audioSha256 ? song.audioSha256|slice(0,16) ~ '…' : '—' }}</strong></div></section>
<section class=\"panel editorial-team-panel\"><div class=\"editorial-team-head\"><div><div class=\"eyebrow\">Équipe éditoriale</div><h2>Éditeurs de la chanson</h2></div><a class=\"primary\" href=\"{{ path('app_song_collaborators', {'_locale':app.request.locale,id:song.id}) }}\">Gérer les éditeurs</a></div><div class=\"editorial-owner\"><span>Propriétaire</span><strong>{{ song.editor ? song.editor.displayName : '—' }}</strong></div>{% if collaborators is defined and collaborators %}<div class=\"editorial-collaborators\"><span>Éditeurs délégués</span><div>{% for row in collaborators %}<span class=\"editor-chip\">{{ row.user.displayName }}</span>{% endfor %}</div></div>{% else %}<p class=\"page-note\">Aucun éditeur délégué.</p>{% endif %}</section>
{% endblock %}
""")

# Accès délégué helper
ACCESS='''    private function requireEditor(Song $song): User\n    {\n        $user=$this->getUser();\n        if(!$user instanceof User || !$this->songAccess->canEdit($song,$user,$this->isGranted('ROLE_ADMIN'))) throw $this->createAccessDeniedException();\n        return $user;\n    }'''
def patch_access(rel,cls):
    p=root/rel; s=rd(p)
    if 'use App\\Service\\SongAccessPolicy;' not in s:
        s=s.replace('use Doctrine\\ORM\\EntityManagerInterface;','use App\\Service\\SongAccessPolicy;\nuse Doctrine\\ORM\\EntityManagerInterface;',1)
    marker=f'final class {cls} extends AbstractController\n{{'
    if 'private readonly SongAccessPolicy $songAccess' not in s:
        if marker not in s: die('classe introuvable: '+cls)
        s=s.replace(marker,marker+'\n    public function __construct(private readonly SongAccessPolicy $songAccess) {}\n',1)
    pat=re.compile(r'    private function requireEditor\(Song \$song\): User\n    \{\n        \$user = \$this->getUser\(\);.*?        return \$user;\n    \}',re.S)
    s,n=pat.subn(ACCESS,s,count=1)
    if n==0 and '$this->songAccess->canEdit' not in s: die('requireEditor non patchable: '+rel)
    wr(p,s)

# SongLab : collaborateurs visibles + accès délégué
p=root/'src/Controller/SongLabController.php'; s=rd(p)
if 'SongCollaboratorRepository' not in s: s=s.replace('use App\\Domain\\Song\\SongTimelineEventRepository;','use App\\Domain\\Song\\SongTimelineEventRepository;\nuse App\\Domain\\Song\\SongCollaboratorRepository;',1)
if 'use App\\Service\\SongAccessPolicy;' not in s: s=s.replace('use App\\Service\\SongWorkflowState;','use App\\Service\\SongWorkflowState;\nuse App\\Service\\SongAccessPolicy;',1)
marker='final class SongLabController extends AbstractController\n{'
if 'private readonly SongAccessPolicy $songAccess' not in s: s=s.replace(marker,marker+'\n    public function __construct(private readonly SongAccessPolicy $songAccess) {}\n',1)
s=s.replace('public function analysis(Song $song, SongWorkflowState $workflow): Response','public function analysis(Song $song, SongWorkflowState $workflow, SongCollaboratorRepository $collaborators): Response',1)
s=s.replace("['song'=>$song,'workflow'=>$workflow->forSong($song)]","['song'=>$song,'workflow'=>$workflow->forSong($song),'collaborators'=>$collaborators->findForSong($song)]",1)
pat=re.compile(r'    private function requireEditor\(Song \$song\): User\n    \{\n        \$user = \$this->getUser\(\);.*?        return \$user;\n    \}',re.S)
s,n=pat.subn(ACCESS,s,count=1)
if n==0 and '$this->songAccess->canEdit' not in s: die('SongLab requireEditor non patchable')
wr(p,s)
patch_access('src/Controller/SongStemController.php','SongStemController')
patch_access('src/Controller/SongEditController.php','SongEditController')

# Propriétaire immuable dans édition
p=root/'src/Controller/SongEditController.php'; s=rd(p)
s=re.sub(r"\n                if \(\$this->isGranted\('ROLE_ADMIN'\)\) \{.*?\n                \}\n\n                \$requestedStatus","\n                // R35.5: propriétaire immuable après création.\n\n                $requestedStatus",s,count=1,flags=re.S)
wr(p,s)

# Répertoire : propriétaire explicite + gestion délégations
p=root/'templates/catalog/index.html.twig'; s=rd(p)
s=s.replace("{{ 'song.editor'|trans }} · {{ song.editor ? song.editor.displayName : ('catalog_admin.no_editor'|trans({}, 'admin_catalog')) }}","Propriétaire · {{ song.editor ? song.editor.displayName : '—' }}")
s=s.replace("{{ 'song.editor'|trans }} · {{ song.editor.displayName }}","Propriétaire · {{ song.editor.displayName }}")
s=re.sub(r'''                    <label>\n                        <span>\{\{ 'song.editor'\|trans \}\}</span>\n                        <select name="editor_id">.*?                        </select>\n                    </label>''','''                    <div class="admin-owner-readonly"><span>Propriétaire</span><strong>{{ song.editor ? song.editor.displayName : '—' }}</strong><a href="{{ path('app_song_collaborators', {'_locale':app.request.locale,id:song.id}) }}">Gérer les éditeurs</a></div>''',s,count=1,flags=re.S)
wr(p,s)

# Admin : ne réassigne plus le propriétaire
p=root/'src/Controller/CatalogController.php'; s=rd(p)
s=re.sub(r"        \$editorId = \(int\) \$request->request->get\('editor_id'\);.*?        if \(\$editor instanceof User\) \{\n            \$song->setEditor\(\$editor\);\n        \}\n","        // R35.5: propriétaire immuable; délégations via SongCollaborator.\n",s,count=1,flags=re.S)
wr(p,s)

# Mail : From + statut + pas de 500 transport
p=root/'src/Domain/Contact/ContactMessage.php'; s=rd(p)
s=s.replace("private string $status='sent'","private string $status='pending'")
if 'markSent()' not in s: s=s.replace(' public function __construct(',' public function markSent():self{$this->status=\'sent\';return $this;} public function markFailed():self{$this->status=\'failed\';return $this;}\n public function __construct(',1)
wr(p,s)
p=root/'src/Controller/ContactController.php'; s=rd(p)
s=s.replace('->to($adminEmail)->replyTo(','->from($adminEmail)->to($adminEmail)->replyTo(',1)
if '$em->persist(new ContactMessage' in s:
    s=s.replace('$em->persist(new ContactMessage($user,$song,$category,$subject,$body));$em->flush();$mail=','$record=new ContactMessage($user,$song,$category,$subject,$body);$em->persist($record);$em->flush();try{$mail=',1)
    s=s.replace("$mailer->send($mail);$this->addFlash('success','Message transmis à l’administrateur.');return $this->redirectToRoute('app_contact_admin',['_locale'=>$request->getLocale()]);","$mailer->send($mail);$record->markSent();$em->flush();$this->addFlash('success','Message transmis à l’administrateur.');return $this->redirectToRoute('app_contact_admin',['_locale'=>$request->getLocale()]);}catch(\\Throwable $e){$record->markFailed();$em->flush();$this->addFlash('error','Envoi impossible. Vérifiez MAILER_DSN puis réessayez.');}",1)
wr(p,s)

# Formulaire mail propre
wr(root/'templates/contact/admin.html.twig',"""{% extends 'base.html.twig' %}
{% block title %}Contacter l’administrateur - EZScore{% endblock %}
{% block body %}<section class=\"contact-admin-shell\"><div class=\"contact-admin-card\"><div class=\"eyebrow\">Assistance EZScore</div><h1>Contacter l’administrateur</h1><p class=\"page-note\">Le message est transmis par EZScore. L’adresse de l’administrateur reste privée.</p>{% if song %}<div class=\"contact-context\"><span>Chanson concernée</span><strong>{{ song.artist }} — {{ song.title }}</strong></div>{% endif %}<form method=\"post\" class=\"contact-admin-form\"><input type=\"hidden\" name=\"_token\" value=\"{{ csrf_token('contact_admin') }}\"><input type=\"hidden\" name=\"song_id\" value=\"{{ song ? song.id : 0 }}\"><label><span>Catégorie</span><select name=\"category\"><option>Bug</option><option>Question</option><option>Demande d’accès</option><option>Problème de chanson</option><option>Autre</option></select></label><label><span>Sujet</span><input name=\"subject\" maxlength=\"180\" required></label><label class=\"contact-message-field\"><span>Message</span><textarea name=\"message\" rows=\"9\" maxlength=\"10000\" required></textarea></label><div class=\"contact-actions\"><button class=\"primary\" type=\"submit\">Envoyer le message</button></div></form></div></section>{% endblock %}
""")

# Écran délégations clair
wr(root/'templates/song/collaborators.html.twig',"""{% extends 'base.html.twig' %}
{% block title %}Équipe éditoriale - {{ song.title }}{% endblock %}
{% block body %}<section class=\"editorial-management-shell\"><header class=\"editorial-management-head\"><div><div class=\"eyebrow\">Équipe éditoriale</div><h1>{{ song.artist }} — {{ song.title }}</h1></div><a href=\"{{ path('app_song_analysis_lab', {'_locale':app.request.locale,id:song.id}) }}\">Tableau de bord</a></header><div class=\"panel owner-card\"><span>Propriétaire</span><strong>{{ song.editor ? song.editor.displayName : '—' }}</strong><small>La propriété ne peut pas être transférée depuis cet écran.</small></div><section class=\"panel\"><div class=\"eyebrow\">Délégations</div><h2>Éditeurs délégués</h2><div class=\"delegated-editor-list\">{% for row in collaborators %}<div class=\"delegated-editor-row\"><strong>{{ row.user.displayName }}</strong>{% if can_manage %}<form method=\"post\" action=\"{{ path('app_song_collaborator_remove', {'_locale':app.request.locale,id:song.id,userId:row.user.id}) }}\"><input type=\"hidden\" name=\"_token\" value=\"{{ csrf_token('song_collaborators_' ~ song.id) }}\"><button class=\"danger-button\">Retirer</button></form>{% endif %}</div>{% else %}<p class=\"page-note\">Aucun éditeur délégué.</p>{% endfor %}</div>{% if can_manage %}<form class=\"delegate-add-form\" method=\"post\" action=\"{{ path('app_song_collaborator_add', {'_locale':app.request.locale,id:song.id}) }}\"><input type=\"hidden\" name=\"_token\" value=\"{{ csrf_token('song_collaborators_' ~ song.id) }}\"><label><span>Ajouter un éditeur</span><select name=\"user_id\" required>{% for editor in editors %}{% if not song.editor or editor.id != song.editor.id %}<option value=\"{{ editor.id }}\">{{ editor.displayName }}</option>{% endif %}{% endfor %}</select></label><button class=\"primary\">Ajouter à la chanson</button></form>{% else %}<p class=\"page-note\">Seul le propriétaire ou un administrateur peut modifier les délégations.</p>{% endif %}</section></section>{% endblock %}
""")

# CSS
wr(root/'public/assets/css/r35-5-ux.css',""".dashboard-only-tab{display:flex;max-width:260px;margin-bottom:18px}.dashboard-only-tab .workflow-tab{width:100%;justify-content:center}.clean-dashboard-head{margin-bottom:18px}.clean-dashboard-grid{margin:0 0 18px!important}.clean-analysis-summary{margin-top:0}.editorial-team-panel{margin-top:18px}.editorial-team-head{display:flex;align-items:center;justify-content:space-between;gap:20px}.editorial-owner,.editorial-collaborators{display:flex;align-items:center;gap:14px;margin-top:14px}.editorial-owner>span,.editorial-collaborators>span,.owner-card>span,.admin-owner-readonly span{opacity:.65;text-transform:uppercase;letter-spacing:.08em;font-size:.78rem}.editor-chip{display:inline-flex;padding:.4rem .65rem;border:1px solid rgba(255,255,255,.15);border-radius:999px;margin:.15rem}.contact-admin-shell{max-width:860px;margin:42px auto}.contact-admin-card{padding:28px;border:1px solid rgba(255,255,255,.14);border-radius:18px;background:rgba(255,255,255,.035)}.contact-admin-form{display:grid;grid-template-columns:1fr 1.5fr;gap:18px;margin-top:24px}.contact-admin-form label{display:grid;gap:8px}.contact-admin-form input,.contact-admin-form select,.contact-admin-form textarea{width:100%;box-sizing:border-box}.contact-message-field,.contact-actions{grid-column:1/-1}.contact-actions{display:flex;justify-content:flex-end}.contact-context{display:flex;gap:12px;padding:12px 14px;border-radius:10px;background:rgba(255,255,255,.05);margin-top:16px}.editorial-management-shell{max-width:980px;margin:0 auto}.editorial-management-head{display:flex;justify-content:space-between;align-items:end;gap:20px;margin-bottom:18px}.owner-card{display:grid;gap:6px}.delegated-editor-list{display:grid;gap:10px;margin:16px 0}.delegated-editor-row{display:flex;justify-content:space-between;align-items:center;gap:16px;padding:12px 14px;border:1px solid rgba(255,255,255,.1);border-radius:10px}.delegate-add-form{display:grid;grid-template-columns:1fr auto;gap:14px;align-items:end;margin-top:18px}.delegate-add-form label{display:grid;gap:8px}.admin-owner-readonly{display:grid;gap:4px;padding:.45rem .2rem}@media(max-width:800px){.contact-admin-form,.delegate-add-form{grid-template-columns:1fr}.contact-message-field,.contact-actions{grid-column:auto}.editorial-team-head,.editorial-management-head{align-items:flex-start;flex-direction:column}}""")

p=root/'readme.md'; s=rd(p)
if 'R35.5 UX + COLLAB + MAIL' not in s: s+='\n\n## R35.5 UX + COLLAB + MAIL\nDashboard simplifié, Répertoire, délégations visibles et fonctionnelles, propriétaire explicite, contact admin corrigé.\n'
wr(p,s)
print('R35_5_APPLIED_OK')
