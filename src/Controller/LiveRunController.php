<?php
declare(strict_types=1);

namespace App\Controller;

use App\Domain\Event\Event;
use App\Domain\Event\LiveRun;
use App\Domain\Group\GroupMember;
use App\Domain\User\User;
use Doctrine\ORM\EntityManagerInterface;
use Symfony\Bundle\FrameworkBundle\Controller\AbstractController;
use Symfony\Component\HttpFoundation\JsonResponse;
use Symfony\Component\HttpFoundation\Request;
use Symfony\Component\HttpFoundation\Response;
use Symfony\Component\Routing\Attribute\Route;

#[Route('/live')]
final class LiveRunController extends AbstractController
{
    #[Route('/events/{id}/test/start', name: 'app_live_test_start', requirements: ['id' => '\d+'], methods: ['POST'])]
    public function startTest(Event $event, Request $request, EntityManagerInterface $em): Response
    {
        $user = $this->requireUser();
        $this->assertOwner($event, $user);

        if (!$this->isCsrfTokenValid('live_test_start_'.$event->getId(), (string) $request->request->get('_token'))) {
            throw $this->createAccessDeniedException();
        }

        $active = $em->getRepository(LiveRun::class)->findOneBy([
            'event' => $event,
            'status' => 'live',
        ]);

        if (!$active instanceof LiveRun) {
            $active = new LiveRun($event, $user, true);
            $em->persist($active);
            $em->flush();
            $this->addFlash('success', 'event.live.test_started');
        }

        return $this->redirectToRoute('app_event_show', [
            '_locale' => $request->getLocale(),
            'id' => $event->getId(),
        ]);
    }

    #[Route('/events/{id}/test/stop', name: 'app_live_test_stop', requirements: ['id' => '\d+'], methods: ['POST'])]
    public function stopTest(Event $event, Request $request, EntityManagerInterface $em): Response
    {
        $user = $this->requireUser();
        $this->assertOwner($event, $user);

        if (!$this->isCsrfTokenValid('live_test_stop_'.$event->getId(), (string) $request->request->get('_token'))) {
            throw $this->createAccessDeniedException();
        }

        $active = $em->getRepository(LiveRun::class)->findOneBy([
            'event' => $event,
            'status' => 'live',
        ]);

        if ($active instanceof LiveRun) {
            $active->end();
            $em->flush();
            $this->addFlash('success', 'event.live.test_stopped');
        }

        return $this->redirectToRoute('app_event_show', [
            '_locale' => $request->getLocale(),
            'id' => $event->getId(),
        ]);
    }

    #[Route('/display-home', name: 'app_live_display_home', methods: ['GET'])]
    public function displayHome(): Response
    {
        $user = $this->requireUser();
        if (!in_array('ROLE_DISPLAY', $user->getRoles(), true)) {
            throw $this->createAccessDeniedException();
        }

        return $this->render('live/display_home.html.twig');
    }

    #[Route('/open', name: 'app_live_open', methods: ['GET'])]
    public function open(EntityManagerInterface $em): JsonResponse
    {
        $user = $this->requireUser();

        if (!in_array('ROLE_DISPLAY', $user->getRoles(), true)) {
            return $this->json(['active' => false]);
        }

        $liveRuns = $em->getRepository(LiveRun::class)->findBy(
            ['status' => 'live'],
            ['startedAt' => 'DESC'],
        );

        foreach ($liveRuns as $liveRun) {
            if (!$liveRun instanceof LiveRun) {
                continue;
            }

            $event = $liveRun->getEvent();
            $group = $event->getGroup();
            if ($group === null) {
                continue;
            }

            $membership = $em->getRepository(GroupMember::class)->findOneBy([
                'group' => $group,
                'user' => $user,
            ]);

            if (!$membership instanceof GroupMember) {
                continue;
            }

            return $this->json([
                'active' => true,
                'test' => $liveRun->isTestMode(),
                'id' => $liveRun->getId(),
                'title' => $event->getTitle(),
                'conductor' => $liveRun->getConductor()->getDisplayName(),
                'join_url' => $this->generateUrl('app_live_display', ['id' => $liveRun->getId()]),
            ]);
        }

        return $this->json(['active' => false]);
    }

    #[Route('/{id}/display', name: 'app_live_display', requirements: ['id' => '\d+'], methods: ['GET'])]
    public function display(LiveRun $liveRun, EntityManagerInterface $em): Response
    {
        $user = $this->requireUser();

        if (!in_array('ROLE_DISPLAY', $user->getRoles(), true) || !$liveRun->isLive()) {
            throw $this->createAccessDeniedException();
        }

        $group = $liveRun->getEvent()->getGroup();
        if ($group === null) {
            throw $this->createAccessDeniedException();
        }

        $membership = $em->getRepository(GroupMember::class)->findOneBy([
            'group' => $group,
            'user' => $user,
        ]);

        if (!$membership instanceof GroupMember) {
            throw $this->createAccessDeniedException();
        }

        return $this->render('live/display.html.twig', [
            'live_run' => $liveRun,
            'event' => $liveRun->getEvent(),
        ]);
    }

    private function requireUser(): User
    {
        $user = $this->getUser();
        if (!$user instanceof User) {
            throw $this->createAccessDeniedException();
        }

        return $user;
    }

    private function assertOwner(Event $event, User $user): void
    {
        if ($event->getCreatedBy()->getId() !== $user->getId()) {
            throw $this->createAccessDeniedException();
        }
    }
}
