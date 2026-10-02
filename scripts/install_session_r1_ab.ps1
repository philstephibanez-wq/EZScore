param([string]$Root = (Get-Location).Path)
$ErrorActionPreference = 'Stop'

function ReadUtf8([string]$p) { [IO.File]::ReadAllText($p, [Text.UTF8Encoding]::new($false)) }
function WriteUtf8([string]$p,[string]$s) { [IO.File]::WriteAllText($p,$s,[Text.UTF8Encoding]::new($false)) }
function ReplaceExact([string]$s,[string]$old,[string]$new,[string]$label) {
    if (-not $s.Contains($old)) { throw "SESSION_R1_AB motif introuvable: $label" }
    $s.Replace($old,$new)
}

$event = Join-Path $Root 'src\Domain\Event\Event.php'
$status = Join-Path $Root 'src\Domain\Event\EventStatus.php'
$ctrl = Join-Path $Root 'src\Controller\EventController.php'
$voter = Join-Path $Root 'src\Security\Acl\EventVoter.php'
$index = Join-Path $Root 'templates\events\index.html.twig'
$show = Join-Path $Root 'templates\events\show.html.twig'
$fr = Join-Path $Root 'translations\event.fr.yaml'
$en = Join-Path $Root 'translations\event.en.yaml'

foreach($p in @($event,$status,$ctrl,$voter,$index,$show,$fr,$en)) {
    if(-not (Test-Path $p)){ throw "SESSION_R1_AB fichier absent: $p" }
}

# EventStatus
$s=ReadUtf8 $status
if(-not $s.Contains("case Validated = 'validated';")){
    $s=ReplaceExact $s "    case Draft = 'draft';`n    case Scheduled = 'scheduled';" "    case Draft = 'draft';`n    case Validated = 'validated';`n    case Scheduled = 'scheduled';" 'status validated'
    WriteUtf8 $status $s
}

# Event
$s=ReadUtf8 $event
$s=$s.Replace('private EventStatus $status = EventStatus::Scheduled;','private EventStatus $status = EventStatus::Draft;')
if(-not $s.Contains('private ?\DateTimeImmutable $validatedAt = null;')){
    $s=ReplaceExact $s @'
    #[ORM\Column]
    private \DateTimeImmutable $updatedAt;
'@ @'
    #[ORM\Column]
    private \DateTimeImmutable $updatedAt;

    #[ORM\Column(nullable: true)]
    private ?\DateTimeImmutable $validatedAt = null;
'@ 'validatedAt'
    $s=ReplaceExact $s @'
    public function getUpdatedAt(): \DateTimeImmutable { return $this->updatedAt; }

    private function touch(): self
'@ @'
    public function getUpdatedAt(): \DateTimeImmutable { return $this->updatedAt; }
    public function getValidatedAt(): ?\DateTimeImmutable { return $this->validatedAt; }

    public function validate(): self
    {
        if ($this->group === null || $this->playlist === null) {
            throw new \LogicException('A session requires exactly one group and one playlist.');
        }
        $this->status = EventStatus::Validated;
        $this->validatedAt = new \DateTimeImmutable();
        return $this->touch();
    }

    private function touch(): self
'@ 'validate method'
}
WriteUtf8 $event $s

# Voter: brouillon privé
$s=ReadUtf8 $voter
if(-not $s.Contains('EventStatus::Draft')){
    $s=ReplaceExact $s "use App\Domain\Event\EventParticipant;`n" "use App\Domain\Event\EventParticipant;`nuse App\Domain\Event\EventStatus;`n" 'voter import'
    $s=ReplaceExact $s @'
        $creator = $subject->getCreatedBy()->getId() === $user->getId();

        if ($attribute === AclPrivilege::EVENT_VIEW) {
'@ @'
        $creator = $subject->getCreatedBy()->getId() === $user->getId();

        if ($subject->getStatus() === EventStatus::Draft && !$creator) {
            return false;
        }

        if ($attribute === AclPrivilege::EVENT_VIEW) {
'@ 'draft private'
    WriteUtf8 $voter $s
}

# Controller: création exige 1 groupe + 1 playlist, draft.
$s=ReadUtf8 $ctrl
if(-not $s.Contains('required_group_playlist')){
$old=@'
            $title = trim((string) $request->request->get('title'));
            $startsAt = $this->parseDateTime((string) $request->request->get('starts_at'));

            if ($title === '' || $startsAt === null) {
                $this->addFlash('error', 'event.validation.required');
                return $this->redirectToRoute('app_events', ['_locale' => $request->getLocale()]);
            }

            $event = (new Event($user))
                ->setTitle($title)
                ->setDescription((string) $request->request->get('description'))
                ->setStartsAt($startsAt)
                ->setEndsAt($this->parseDateTime((string) $request->request->get('ends_at')))
                ->setMode(EventMode::tryFrom((string) $request->request->get('mode')) ?? EventMode::Onsite)
                ->setLocation((string) $request->request->get('location'))
                ->setRemoteUrl((string) $request->request->get('remote_url'))
                ->setStatus(EventStatus::Scheduled);
'@
$new=@'
            $title = trim((string) $request->request->get('title'));
            $startsAt = $this->parseDateTime((string) $request->request->get('starts_at'));
            $group = $em->getRepository(UserGroup::class)->find((int) $request->request->get('group_id'));
            $playlist = $em->getRepository(Playlist::class)->find((int) $request->request->get('playlist_id'));

            if ($title === '' || $startsAt === null
                || !$group instanceof UserGroup
                || !$playlist instanceof Playlist
                || !$this->isGranted(AclPrivilege::GROUP_EDIT, $group)
                || !$this->isGranted(AclPrivilege::PLAYLIST_EDIT, $playlist)) {
                $this->addFlash('error', 'event.validation.required_group_playlist');
                return $this->redirectToRoute('app_events', ['_locale' => $request->getLocale()]);
            }

            $event = (new Event($user))
                ->setTitle($title)
                ->setDescription((string) $request->request->get('description'))
                ->setStartsAt($startsAt)
                ->setEndsAt($this->parseDateTime((string) $request->request->get('ends_at')))
                ->setMode(EventMode::tryFrom((string) $request->request->get('mode')) ?? EventMode::Onsite)
                ->setLocation((string) $request->request->get('location'))
                ->setRemoteUrl((string) $request->request->get('remote_url'))
                ->setGroup($group)
                ->setPlaylist($playlist)
                ->setStatus(EventStatus::Draft);
'@
$s=ReplaceExact $s $old $new 'creation group playlist'
}

$s=$s.Replace("`$period = (string) `$request->query->get('period', 'upcoming');","`$period = (string) `$request->query->get('period', 'all');")
$s=$s.Replace("            `$qb->andWhere('(e.createdBy = :currentUser OR myParticipation.id IS NOT NULL OR myGroup.id IS NOT NULL)');",
"            `$qb->andWhere('(e.createdBy = :currentUser OR ((e.status <> :draftStatus) AND (myParticipation.id IS NOT NULL OR myGroup.id IS NOT NULL)))')`n                ->setParameter('draftStatus', EventStatus::Draft);")

if(-not $s.Contains("'creation_groups'")){
$old=@'
        return $this->render('events/index.html.twig', [
            'events' => $pager['rows'],
'@
$new=@'
        $creationGroups = array_values(array_filter(
            $em->getRepository(UserGroup::class)->findAll(),
            fn(UserGroup $group): bool => $this->isGranted(AclPrivilege::GROUP_EDIT, $group),
        ));
        $creationPlaylists = array_values(array_filter(
            $em->getRepository(Playlist::class)->findAll(),
            fn(Playlist $playlist): bool => $this->isGranted(AclPrivilege::PLAYLIST_EDIT, $playlist),
        ));

        return $this->render('events/index.html.twig', [
            'events' => $pager['rows'],
            'creation_groups' => $creationGroups,
            'creation_playlists' => $creationPlaylists,
'@
$s=ReplaceExact $s $old $new 'creation lists'
}

# setGroup ne crée plus de participants et n'envoie plus d'invitations.
$s=$s.Replace("        EventMailer `$mailer,`n","")
$rx='(?s)\n        \$newParticipants = \[\];.*?\n        return \$this->json\(\[''ok'' => true, ''changed'' => count\(\$newParticipants\)\]\);'
if([regex]::IsMatch($s,$rx)){
    $s=[regex]::Replace($s,$rx,"`n        `$em->flush();`n        return `$this->json(['ok' => true, 'changed' => 1]);",1)
}

# participants manuels seulement après validation
$needle=@'
        $this->denyAccessUnlessGranted(AclPrivilege::EVENT_INVITE, $event);
        $this->validateAjaxCsrf('event_participants_'.$event->getId(), $request);

        $changed = 0;
'@
if(-not $s.Contains('session_not_validated')){
$replacement=@'
        $this->denyAccessUnlessGranted(AclPrivilege::EVENT_INVITE, $event);
        $this->validateAjaxCsrf('event_participants_'.$event->getId(), $request);

        if ($event->getStatus() !== EventStatus::Validated) {
            return $this->json(['ok' => false, 'message' => 'session_not_validated'], 409);
        }

        $changed = 0;
'@
$s=ReplaceExact $s $needle $replacement 'participant gate'
}

# route validation
if(-not $s.Contains("name: 'app_event_validate'")){
$anchor="    #[Route('/{id}/rsvp', name: 'app_event_rsvp', requirements: ['id' => '\\d+'], methods: ['POST'])]"
$route=@'
    #[Route('/{id}/validate', name: 'app_event_validate', requirements: ['id' => '\d+'], methods: ['POST'])]
    public function validateSession(Event $event, Request $request, EntityManagerInterface $em, EventMailer $mailer): Response
    {
        $user = $this->requireUser();
        if ($event->getCreatedBy()->getId() !== $user->getId()) throw $this->createAccessDeniedException();
        if (!$this->isCsrfTokenValid('event_validate_'.$event->getId(), (string) $request->request->get('_token'))) {
            throw $this->createAccessDeniedException();
        }
        if ($event->getGroup() === null || $event->getPlaylist() === null) {
            $this->addFlash('error', 'event.validation.required_group_playlist');
            return $this->redirectToRoute('app_event_show', ['_locale' => $request->getLocale(), 'id' => $event->getId()]);
        }

        foreach ($em->getRepository(GroupMember::class)->findBy(['group' => $event->getGroup()]) as $membership) {
            $member = $membership->getUser();
            if (!$member->isActive()) continue;
            $participant = $em->getRepository(EventParticipant::class)->findOneBy(['event' => $event, 'user' => $member]);
            if (!$participant instanceof EventParticipant) {
                $participant = new EventParticipant(
                    $event,
                    $member,
                    $member->getId() === $event->getCreatedBy()->getId() ? EventParticipantStatus::Accepted : EventParticipantStatus::Invited,
                );
                $em->persist($participant);
            }
        }

        $event->validate();
        $em->flush();

        foreach ($em->getRepository(EventParticipant::class)->findBy(['event' => $event]) as $participant) {
            if ($participant->getUser()->getId() === $event->getCreatedBy()->getId()) continue;
            if ($participant->getEmailNotifiedAt() !== null) continue;
            if ($mailer->sendInvitation($event, $participant->getUser())) $participant->markEmailNotified();
        }
        $em->flush();

        $this->addFlash('success', 'event.validated');
        return $this->redirectToRoute('app_event_show', ['_locale' => $request->getLocale(), 'id' => $event->getId()]);
    }

'@
$s=ReplaceExact $s $anchor ($route+$anchor) 'validate route'
}
WriteUtf8 $ctrl $s

# Index form
$s=ReadUtf8 $index
if(-not $s.Contains('name="group_id"')){
$old="    <label>{{ 'event.fields.title'|trans({}, 'event') }}<input name=`"title`" required></label>"
$new=@'
    <label>{{ 'event.fields.title'|trans({}, 'event') }}<input name="title" required></label>
    <label>{{ 'event.fields.group'|trans({}, 'event') }}
      <select name="group_id" required><option value="">—</option>{% for group in creation_groups %}<option value="{{ group.id }}">{{ group.name }}</option>{% endfor %}</select>
    </label>
    <label>{{ 'event.fields.playlist'|trans({}, 'event') }}
      <select name="playlist_id" required><option value="">—</option>{% for playlist in creation_playlists %}<option value="{{ playlist.id }}">{{ playlist.name }}</option>{% endfor %}</select>
    </label>
'@
$s=ReplaceExact $s $old $new 'index selectors'
}
$s=$s.Replace("['draft','scheduled','cancelled','completed']","['draft','validated','scheduled','cancelled','completed']")
$s=$s.Replace("period: filters.period != 'upcoming' ? filters.period : null","period: filters.period != 'all' ? filters.period : null")
WriteUtf8 $index $s

# Show validation
$s=ReadUtf8 $show
$s=$s.Replace("['draft','scheduled','cancelled','completed']","['draft','validated','scheduled','cancelled','completed']")
if(-not $s.Contains('app_event_validate')){
$anchor="{% if is_granted('EVENT_MANAGE', event) %}`n<section class=`"panel`">"
$new=@'
{% if event.createdBy.id == app.user.id and event.status.value == 'draft' %}
<section class="panel">
  <h2>{{ 'event.validate_title'|trans({}, 'event') }}</h2>
  <p class="page-note">{{ 'event.validate_note'|trans({}, 'event') }}</p>
  <form method="post" action="{{ path('app_event_validate', {'_locale': app.request.locale, id: event.id}) }}">
    <input type="hidden" name="_token" value="{{ csrf_token('event_validate_' ~ event.id) }}">
    <button class="primary" type="submit">{{ 'event.validate_button'|trans({}, 'event') }}</button>
  </form>
</section>
{% endif %}

{% if is_granted('EVENT_MANAGE', event) %}
<section class="panel">
'@
$s=ReplaceExact $s $anchor $new 'show validation'
}
WriteUtf8 $show $s

# i18n
$s=ReadUtf8 $fr
$s=$s.Replace("    draft: Brouillon`n    scheduled: Planifié","    draft: Brouillon`n    validated: Validée`n    scheduled: Planifié")
if(-not $s.Contains('validate_button:')){
$s=$s.Replace("  save: Enregistrer`n","  save: Enregistrer`n  validate_title: Validation`n  validate_note: La validation rend la session officielle et envoie les invitations aux membres du groupe.`n  validate_button: Valider la session et envoyer les invitations`n  validated: Session validée. Invitations envoyées.`n")
}
$s=$s.Replace("    required: Le titre et la date de début sont obligatoires.","    required: Le titre et la date de début sont obligatoires.`n    required_group_playlist: Le titre, la date, un groupe et une playlist sont obligatoires.")
WriteUtf8 $fr $s

$s=ReadUtf8 $en
$s=$s.Replace("    draft: Draft`n    scheduled: Scheduled","    draft: Draft`n    validated: Validated`n    scheduled: Scheduled")
if(-not $s.Contains('validate_button:')){
$s=$s.Replace("  save: Save`n","  save: Save`n  validate_title: Validation`n  validate_note: Validation makes the session official and sends invitations to group members.`n  validate_button: Validate session and send invitations`n  validated: Session validated. Invitations sent.`n")
}
$s=$s.Replace("    required: Title and start date are required.","    required: Title and start date are required.`n    required_group_playlist: Title, date, one group and one playlist are required.")
WriteUtf8 $en $s

foreach($required in @(
    (Join-Path $Root 'migrations\Version20261002170000.php'),
    (Join-Path $Root 'tests\session_r1_ab_contract.php'),
    (Join-Path $Root 'docs\CONTRAT_SESSION_EZSCORE_R1.md')
)) {
    if(-not (Test-Path $required)) {
        throw "SESSION_R1_AB fichier de livraison absent: $required"
    }
}

Write-Host 'SESSION_R1_AB_INSTALL_OK'
