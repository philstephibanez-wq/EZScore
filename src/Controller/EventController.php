<?php
declare(strict_types=1);

namespace App\Controller;

use App\Domain\Event\Event;
use App\Domain\Event\EventParticipant;
use App\Domain\Event\EventParticipantStatus;
use App\Domain\Event\EventStatus;
use App\Domain\Event\LiveRun;
use App\Domain\Group\GroupMember;
use App\Domain\Group\UserGroup;
use App\Domain\Playlist\Playlist;
use App\Domain\Playlist\PlaylistGroup;
use App\Domain\Playlist\PlaylistInvitation;
use App\Domain\Playlist\PlaylistInvitationStatus;
use App\Domain\Playlist\PlaylistItem;
use App\Domain\User\User;
use App\Security\Acl\AclPrivilege;
use App\Service\EventMailer;
use App\Service\ListPagination;
use Doctrine\ORM\EntityManagerInterface;
use Symfony\Bundle\FrameworkBundle\Controller\AbstractController;
use Symfony\Component\HttpFoundation\JsonResponse;
use Symfony\Component\HttpFoundation\Request;
use Symfony\Component\HttpFoundation\Response;
use Symfony\Component\Routing\Attribute\Route;

#[Route('/events')]
final class EventController extends AbstractController
{
    #[Route('', name: 'app_events', methods: ['GET', 'POST'])]
    public function index(
        Request $request,
        EntityManagerInterface $em,
        ListPagination $pagination,
    ): Response {
        $user = $this->requireUser();

        if ($request->isMethod('POST')) {
            if (!$this->isCsrfTokenValid('event_create', (string) $request->request->get('_token'))) {
                throw $this->createAccessDeniedException();
            }

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

                ->setLocation((string) $request->request->get('location'))
                ->setGroup($group)
                ->setPlaylist($playlist)
                ->setStatus(EventStatus::Draft);

            $em->persist($event);
            $em->flush();

            $em->persist(new EventParticipant($event, $user, EventParticipantStatus::Accepted));
            $em->flush();

            $this->addFlash('success', 'event.created');
            return $this->redirectToRoute('app_event_show', [
                '_locale' => $request->getLocale(),
                'id' => $event->getId(),
            ]);
        }

        $query = $pagination->query($request);
        $letter = $pagination->letter($request);
        $status = (string) $request->query->get('status', '');

        $period = (string) $request->query->get('period', 'all');

        $qb = $em->getRepository(Event::class)->createQueryBuilder('e')
            ->leftJoin('e.createdBy', 'creator')
            ->leftJoin('e.group', 'eg')
            ->leftJoin('e.playlist', 'ep')
            ->leftJoin(EventParticipant::class, 'myParticipation', 'WITH', 'myParticipation.event = e AND myParticipation.user = :currentUser')
            ->leftJoin(GroupMember::class, 'myGroup', 'WITH', 'myGroup.group = eg AND myGroup.user = :currentUser')
            ->setParameter('currentUser', $user)
            ->distinct()
            ->orderBy('e.startsAt', 'ASC');

        if (!$this->isGranted('ROLE_ADMIN')) {
            $qb->andWhere('(e.createdBy = :currentUser OR ((e.status <> :draftStatus) AND (myParticipation.id IS NOT NULL OR myGroup.id IS NOT NULL)))')
                ->setParameter('draftStatus', EventStatus::Draft);
        }

        if ($query !== '') {
            $qb->andWhere(
                "(LOWER(e.title) LIKE :q
                  OR LOWER(COALESCE(e.description, '')) LIKE :q
                  OR LOWER(COALESCE(creator.displayName, '')) LIKE :q
                  OR LOWER(COALESCE(eg.name, '')) LIKE :q
                  OR LOWER(COALESCE(ep.name, '')) LIKE :q)"
            )->setParameter('q', '%'.mb_strtolower($query).'%');
        }

        if ($letter !== null) {
            $qb->andWhere('UPPER(SUBSTRING(e.title, 1, 1)) = :letter')
                ->setParameter('letter', $letter);
        }

        if (in_array($status, array_map(static fn(EventStatus $case): string => $case->value, EventStatus::cases()), true)) {
            $qb->andWhere('e.status = :status')->setParameter('status', $status);
        } else {
            $status = '';
        }



        $now = new \DateTimeImmutable();
        if ($period === 'past') {
            $qb->andWhere('e.startsAt < :now')->setParameter('now', $now)->orderBy('e.startsAt', 'DESC');
        } elseif ($period === 'all') {
        } else {
            $period = 'upcoming';
            $qb->andWhere('e.startsAt >= :now')->setParameter('now', $now);
        }

        $pager = $pagination->paginate($qb, $request, 'e', 'page', 12);

        $myInvitationCount = $em->getRepository(EventParticipant::class)->count([
            'user' => $user,
            'status' => EventParticipantStatus::Invited,
        ]);

        $myInvitations = $em->getRepository(EventParticipant::class)->createQueryBuilder('inv')
            ->join('inv.event', 'invEvent')
            ->addSelect('invEvent')
            ->andWhere('inv.user = :user')
            ->andWhere('inv.status = :status')
            ->setParameter('user', $user)
            ->setParameter('status', EventParticipantStatus::Invited)
            ->orderBy('invEvent.startsAt', 'ASC')
            ->setMaxResults(8)
            ->getQuery()
            ->getResult();

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
            'my_invitations' => $myInvitations,
            'my_invitation_count' => $myInvitationCount,
            'pager' => $pager,
            'alphabet' => $pagination->alphabet(),
            'filters' => [
                'q' => $query,
                'letter' => $letter,
                'status' => $status,
                'period' => $period,
            ],
        ]);
    }

    #[Route('/{id}', name: 'app_event_show', requirements: ['id' => '\\d+'], methods: ['GET'])]
    public function show(
        Event $event,
        Request $request,
        EntityManagerInterface $em,
        ListPagination $pagination,
    ): Response {
        $this->denyAccessUnlessGranted(AclPrivilege::EVENT_VIEW, $event);
        $user = $this->requireUser();

        $participantQuery = $pagination->query($request, 'pq');
        $participantLetter = $pagination->letter($request, 'pletter');
        $participantStatus = (string) $request->query->get('pstatus', '');

        $participantQb = $em->getRepository(EventParticipant::class)->createQueryBuilder('participant')
            ->join('participant.user', 'participantUser')
            ->addSelect('participantUser')
            ->andWhere('participant.event = :event')
            ->setParameter('event', $event)
            ->orderBy('LOWER(participantUser.displayName)', 'ASC');

        if ($participantQuery !== '') {
            $participantQb->andWhere(
                '(LOWER(participantUser.displayName) LIKE :pq OR LOWER(participantUser.email) LIKE :pq)'
            )->setParameter('pq', '%'.mb_strtolower($participantQuery).'%');
        }

        if ($participantLetter !== null) {
            $participantQb->andWhere('UPPER(SUBSTRING(participantUser.displayName, 1, 1)) = :pletter')
                ->setParameter('pletter', $participantLetter);
        }

        if (in_array(
            $participantStatus,
            array_map(static fn(EventParticipantStatus $case): string => $case->value, EventParticipantStatus::cases()),
            true,
        )) {
            $participantQb->andWhere('participant.status = :participantStatus')
                ->setParameter('participantStatus', $participantStatus);
        } else {
            $participantStatus = '';
        }

        $participantPager = $pagination->paginate(
            $participantQb,
            $request,
            'participant',
            'ppage',
            50,
        );

        $myParticipation = $em->getRepository(EventParticipant::class)->findOneBy([
            'event' => $event,
            'user' => $user,
        ]);

        return $this->render('events/show.html.twig', [
            'event' => $event,
            'participants' => $participantPager['rows'],
            'participant_pager' => $participantPager,
            'participant_filters' => [
                'q' => $participantQuery,
                'letter' => $participantLetter,
                'status' => $participantStatus,
            ],
            'alphabet' => $pagination->alphabet(),
            'my_participation' => $myParticipation,
            'event_url' => $this->generateUrl(
                'app_event_show',
                ['_locale' => $request->getLocale(), 'id' => $event->getId()],
                0,
            ),
        ]);
    }

    #[Route('/{id}/session-playlist', name: 'app_event_session_playlist', requirements: ['id' => '\d+'], methods: ['GET'])]
    public function sessionPlaylist(
        Event $event,
        EntityManagerInterface $em,
    ): Response {
        $this->denyAccessUnlessGranted(AclPrivilege::EVENT_VIEW, $event);

        $playlist = $event->getPlaylist();
        if (!$playlist instanceof Playlist) {
            throw $this->createNotFoundException('Session playlist not assigned.');
        }

        $items = $em->getRepository(PlaylistItem::class)->findBy(
            ['playlist' => $playlist],
            ['position' => 'ASC', 'id' => 'ASC'],
        );

        $activeLiveRun = $em->getRepository(LiveRun::class)->findOneBy(
            ['event' => $event, 'status' => 'live'],
            ['startedAt' => 'DESC'],
        );

        return $this->render('events/session_playlist.html.twig', [
            'event' => $event,
            'session_playlist_items' => $items,
            'active_live_run' => $activeLiveRun,
        ]);
    }
    #[Route('/{id}/update', name: 'app_event_update', requirements: ['id' => '\\d+'], methods: ['POST'])]
    public function update(Event $event, Request $request, EntityManagerInterface $em): Response
    {
        $this->denyAccessUnlessGranted(AclPrivilege::EVENT_MANAGE, $event);

        if (!$this->isCsrfTokenValid('event_update_'.$event->getId(), (string) $request->request->get('_token'))) {
            throw $this->createAccessDeniedException();
        }

        $startsAt = $this->parseDateTime((string) $request->request->get('starts_at'));
        if ($startsAt === null) {
            $this->addFlash('error', 'event.validation.required');
            return $this->redirectToRoute('app_event_show', ['_locale' => $request->getLocale(), 'id' => $event->getId()]);
        }

        $event
            ->setTitle((string) $request->request->get('title'))
            ->setDescription((string) $request->request->get('description'))
            ->setStartsAt($startsAt)
            ->setEndsAt($this->parseDateTime((string) $request->request->get('ends_at')))
            ->setLocation((string) $request->request->get('location'))
            ->setStatus(EventStatus::tryFrom((string) $request->request->get('status')) ?? EventStatus::Scheduled);

        $em->flush();
        $this->addFlash('success', 'event.updated');

        return $this->redirectToRoute('app_event_show', ['_locale' => $request->getLocale(), 'id' => $event->getId()]);
    }

    #[Route('/{id}/group', name: 'app_event_set_group', requirements: ['id' => '\\d+'], methods: ['POST'])]
    public function setGroup(
        Event $event,
        Request $request,
        EntityManagerInterface $em,
    ): JsonResponse {
        $this->denyAccessUnlessGranted(AclPrivilege::EVENT_MANAGE, $event);
        $this->validateAjaxCsrf('event_group_'.$event->getId(), $request);

        $ids = $this->ids($request);
        $group = isset($ids[0]) ? $em->getRepository(UserGroup::class)->find($ids[0]) : null;

        if (!$group instanceof UserGroup || !$this->isGranted(AclPrivilege::GROUP_EDIT, $group)) {
            return $this->json(['ok' => false, 'message' => 'invalid_group'], 422);
        }

        $event->setGroup($group);

        if ($event->getPlaylist() !== null
            && !($em->getRepository(PlaylistGroup::class)->findOneBy([
                'playlist' => $event->getPlaylist(),
                'group' => $group,
            ]) instanceof PlaylistGroup)
            && $this->isGranted(AclPrivilege::PLAYLIST_EDIT, $event->getPlaylist())
            && $this->isGranted(AclPrivilege::GROUP_MANAGE_PLAYLISTS, $group)) {
            $em->persist(new PlaylistGroup($event->getPlaylist(), $group, $this->requireUser()));
        }

        $em->flush();
        return $this->json(['ok' => true, 'changed' => 1]);
    }

    #[Route('/{id}/playlist', name: 'app_event_set_playlist', requirements: ['id' => '\\d+'], methods: ['POST'])]
    public function setPlaylist(Event $event, Request $request, EntityManagerInterface $em): JsonResponse
    {
        $this->denyAccessUnlessGranted(AclPrivilege::EVENT_MANAGE, $event);
        $this->validateAjaxCsrf('event_playlist_'.$event->getId(), $request);

        $ids = $this->ids($request);
        $playlist = isset($ids[0]) ? $em->getRepository(Playlist::class)->find($ids[0]) : null;

        if (!$playlist instanceof Playlist || !$this->isGranted(AclPrivilege::PLAYLIST_EDIT, $playlist)) {
            return $this->json(['ok' => false, 'message' => 'invalid_playlist'], 422);
        }

        $event->setPlaylist($playlist);

        if ($event->getGroup() !== null
            && !($em->getRepository(PlaylistGroup::class)->findOneBy([
                'playlist' => $playlist,
                'group' => $event->getGroup(),
            ]) instanceof PlaylistGroup)
            && $this->isGranted(AclPrivilege::GROUP_MANAGE_PLAYLISTS, $event->getGroup())) {
            $em->persist(new PlaylistGroup($playlist, $event->getGroup(), $this->requireUser()));
        }

        $em->flush();
        return $this->json(['ok' => true, 'changed' => 1]);
    }

    #[Route('/{id}/participants/bulk-add', name: 'app_event_participants_bulk_add', requirements: ['id' => '\\d+'], methods: ['POST'])]
    public function addParticipants(
        Event $event,
        Request $request,
        EntityManagerInterface $em,
    ): JsonResponse {
        $this->denyAccessUnlessGranted(AclPrivilege::EVENT_INVITE, $event);
        $this->validateAjaxCsrf('event_participants_'.$event->getId(), $request);

        if ($event->getStatus() !== EventStatus::Validated) {
            return $this->json(['ok' => false, 'message' => 'session_not_validated'], 409);
        }

        $changed = 0;
        foreach ($this->ids($request) as $id) {
            $user = $em->getRepository(User::class)->find($id);
            if (!$user instanceof User || !$user->isActive()) continue;
            if (!$this->eligibleParticipant($event, $user, $em)) continue;

            if ($em->getRepository(EventParticipant::class)->findOneBy(['event' => $event, 'user' => $user]) instanceof EventParticipant) {
                continue;
            }

            $participant = new EventParticipant($event, $user);
            $em->persist($participant);
            $em->flush();

            if ($mailer->sendInvitation($event, $user)) {
                $participant->markEmailNotified();
                $em->flush();
            }

            ++$changed;
        }

        return $this->json(['ok' => true, 'changed' => $changed]);
    }

    #[Route('/{id}/participants/bulk-remove', name: 'app_event_participants_bulk_remove', requirements: ['id' => '\\d+'], methods: ['POST'])]
    public function removeParticipants(Event $event, Request $request, EntityManagerInterface $em): JsonResponse
    {
        $this->denyAccessUnlessGranted(AclPrivilege::EVENT_INVITE, $event);
        $this->validateAjaxCsrf('event_participants_'.$event->getId(), $request);

        if ($event->getStatus() !== EventStatus::Validated) {
            return $this->json(['ok' => false, 'message' => 'session_not_validated'], 409);
        }

        $changed = 0;
        foreach ($this->ids($request) as $id) {
            $user = $em->getRepository(User::class)->find($id);
            if (!$user instanceof User || $user->getId() === $event->getCreatedBy()->getId()) continue;

            $participant = $em->getRepository(EventParticipant::class)->findOneBy(['event' => $event, 'user' => $user]);
            if (!$participant instanceof EventParticipant) continue;

            $em->remove($participant);
            ++$changed;
        }

        $em->flush();
        return $this->json(['ok' => true, 'changed' => $changed]);
    }

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
    #[Route('/{id}/rsvp', name: 'app_event_rsvp', requirements: ['id' => '\\d+'], methods: ['POST'])]
    public function rsvp(Event $event, Request $request, EntityManagerInterface $em): Response
    {
        $this->denyAccessUnlessGranted(AclPrivilege::EVENT_VIEW, $event);
        $user = $this->requireUser();

        if (!$this->isCsrfTokenValid('event_rsvp_'.$event->getId(), (string) $request->request->get('_token'))) {
            throw $this->createAccessDeniedException();
        }

        $participant = $em->getRepository(EventParticipant::class)->findOneBy(['event' => $event, 'user' => $user]);
        if (!$participant instanceof EventParticipant) {
            throw $this->createAccessDeniedException();
        }

        $status = EventParticipantStatus::tryFrom((string) $request->request->get('status'));
        if ($status === null) {
            throw $this->createAccessDeniedException();
        }

        $participant->respond($status);
        $em->flush();

        return $this->redirectToRoute('app_event_show', ['_locale' => $request->getLocale(), 'id' => $event->getId()]);
    }

    #[Route('/{id}/delete', name: 'app_event_delete', requirements: ['id' => '\\d+'], methods: ['POST'])]
    public function delete(Event $event, Request $request, EntityManagerInterface $em): Response
    {
        $this->denyAccessUnlessGranted(AclPrivilege::EVENT_MANAGE, $event);

        if (!$this->isCsrfTokenValid('event_delete_'.$event->getId(), (string) $request->request->get('_token'))) {
            throw $this->createAccessDeniedException();
        }

        $em->remove($event);
        $em->flush();

        $this->addFlash('success', 'event.deleted');
        return $this->redirectToRoute('app_events', ['_locale' => $request->getLocale()]);
    }

    private function eligibleParticipant(Event $event, User $user, EntityManagerInterface $em): bool
    {
        if ($event->getGroup() !== null) {
            return $em->getRepository(GroupMember::class)->findOneBy([
                'group' => $event->getGroup(),
                'user' => $user,
            ]) instanceof GroupMember;
        }

        $playlist = $event->getPlaylist();
        if ($playlist === null) return true;
        if ($playlist->isPublic() || $playlist->getOwnerUser()->getId() === $user->getId()) return true;

        if ($em->getRepository(PlaylistInvitation::class)->findOneBy([
            'playlist' => $playlist,
            'invitedUser' => $user,
            'status' => PlaylistInvitationStatus::Accepted,
        ]) instanceof PlaylistInvitation) return true;

        foreach ($em->getRepository(PlaylistGroup::class)->findBy(['playlist' => $playlist]) as $link) {
            if ($em->getRepository(GroupMember::class)->findOneBy([
                'group' => $link->getGroup(),
                'user' => $user,
            ]) instanceof GroupMember) return true;
        }

        return false;
    }

    private function parseDateTime(string $value): ?\DateTimeImmutable
    {
        $value = trim($value);
        if ($value === '') return null;

        try {
            return new \DateTimeImmutable($value);
        } catch (\Throwable) {
            return null;
        }
    }

    /** @return list<int> */
    private function ids(Request $request): array
    {
        return array_values(array_unique(array_filter(
            array_map('intval', $request->request->all('ids')),
            static fn(int $id): bool => $id > 0,
        )));
    }

    private function validateAjaxCsrf(string $tokenId, Request $request): void
    {
        if (!$this->isCsrfTokenValid($tokenId, (string) $request->request->get('_token'))) {
            throw $this->createAccessDeniedException();
        }
    }

    private function requireUser(): User
    {
        $user = $this->getUser();
        if (!$user instanceof User) throw $this->createAccessDeniedException();
        return $user;
    }
}

