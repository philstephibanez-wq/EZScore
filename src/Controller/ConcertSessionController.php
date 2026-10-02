<?php

declare(strict_types=1);

namespace App\Controller;

use App\Domain\User\User;
use App\Service\ConcertSessionStore;
use Symfony\Bundle\FrameworkBundle\Controller\AbstractController;
use Symfony\Component\HttpFoundation\JsonResponse;
use Symfony\Component\HttpFoundation\Request;
use Symfony\Component\HttpFoundation\Response;
use Symfony\Component\Routing\Attribute\Route;
use Symfony\Component\Routing\Generator\UrlGeneratorInterface;
use Symfony\Component\Security\Csrf\CsrfTokenManagerInterface;

final class ConcertSessionController extends AbstractController
{
    #[Route('/concert/control', name: 'app_concert_control', methods: ['GET'])]
    public function control(CsrfTokenManagerInterface $csrf): Response
    {
        $this->denyAccessUnlessGranted('ROLE_USER');

        return $this->render('concert/control.html.twig', [
            'csrf_token_value' => $csrf->getToken('concert_session')->getValue(),
        ]);
    }

    #[Route('/api/concert/session', name: 'app_concert_session_create', methods: ['POST'])]
    public function create(Request $request, ConcertSessionStore $store, UrlGeneratorInterface $urls): JsonResponse
    {
        $this->denyAccessUnlessGranted('ROLE_USER');
        if (!$this->isCsrfTokenValid('concert_session', (string) $request->headers->get('X-CSRF-Token'))) {
            return $this->json(['error' => 'INVALID_CSRF'], 403);
        }

        $user = $this->getUser();
        if (!$user instanceof User || $user->getId() === null) {
            return $this->json(['error' => 'INVALID_USER'], 403);
        }

        $created = $store->create($user);
        $sessionId = (string) $created['session']['id'];
        $inviteToken = (string) $created['invite_token'];
        $followUrl = $urls->generate(
            'app_concert_follow',
            ['sessionId' => $sessionId, 'invite' => $inviteToken],
            UrlGeneratorInterface::ABSOLUTE_URL,
        );

        return $this->json([
            'session' => $created['session'],
            'master_key' => $created['master_key'],
            'invite_token' => $inviteToken,
            'follow_url' => $followUrl,
        ], 201);
    }

    #[Route('/api/concert/session/{sessionId}/state', name: 'app_concert_session_update', methods: ['POST'])]
    public function updateState(string $sessionId, Request $request, ConcertSessionStore $store): JsonResponse
    {
        $this->denyAccessUnlessGranted('ROLE_USER');
        if (!$this->isCsrfTokenValid('concert_session', (string) $request->headers->get('X-CSRF-Token'))) {
            return $this->json(['error' => 'INVALID_CSRF'], 403);
        }

        $user = $this->getUser();
        if (!$user instanceof User || $user->getId() === null) {
            return $this->json(['error' => 'INVALID_USER'], 403);
        }

        try {
            $session = $store->updateState(
                $sessionId,
                (int) $user->getId(),
                (string) $request->headers->get('X-Concert-Master-Key'),
                $this->payload($request),
            );
        } catch (\RuntimeException $exception) {
            return $this->storeError($exception);
        }

        return $this->json(['session' => $session]);
    }

    #[Route('/api/concert/session/{sessionId}/master-state', name: 'app_concert_master_state', methods: ['GET'])]
    public function masterState(string $sessionId, Request $request, ConcertSessionStore $store): JsonResponse
    {
        $this->denyAccessUnlessGranted('ROLE_USER');

        $user = $this->getUser();
        if (!$user instanceof User || $user->getId() === null) {
            return $this->json(['error' => 'INVALID_USER'], 403);
        }

        try {
            $session = $store->publicStateForMaster(
                $sessionId,
                (int) $user->getId(),
                (string) $request->headers->get('X-Concert-Master-Key'),
            );
        } catch (\RuntimeException $exception) {
            return $this->storeError($exception);
        }

        if ($session === null) {
            return $this->json(['error' => 'SESSION_NOT_FOUND'], 404);
        }

        return $this->json(['session' => $session]);
    }

    #[Route('/concert/session/{sessionId}', name: 'app_concert_follow', methods: ['GET'])]
    public function follow(string $sessionId, Request $request, ConcertSessionStore $store): Response
    {
        $inviteToken = (string) $request->query->get('invite', '');
        if (!$store->canJoin($sessionId, $inviteToken)) {
            return new Response('Session EZScore invalide ou expirée.', 404);
        }

        return $this->render('concert/follow.html.twig', [
            'session_id' => $sessionId,
            'invite_token' => $inviteToken,
        ]);
    }

    #[Route('/api/concert/session/{sessionId}/join', name: 'app_concert_session_join', methods: ['POST'])]
    public function join(string $sessionId, Request $request, ConcertSessionStore $store): JsonResponse
    {
        $payload = $this->payload($request);

        try {
            $joined = $store->join(
                $sessionId,
                (string) ($payload['invite_token'] ?? ''),
                (string) ($payload['name'] ?? 'Follower'),
                (string) ($payload['device_type'] ?? 'browser'),
            );
        } catch (\RuntimeException $exception) {
            return $this->storeError($exception);
        }

        return $this->json($joined, 201);
    }

    #[Route('/api/concert/session/{sessionId}/client-state', name: 'app_concert_client_state', methods: ['GET'])]
    public function clientState(string $sessionId, Request $request, ConcertSessionStore $store): JsonResponse
    {
        try {
            $session = $store->stateForClient(
                $sessionId,
                (string) $request->headers->get('X-Concert-Client-Id'),
                (string) $request->headers->get('X-Concert-Client-Key'),
            );
        } catch (\RuntimeException $exception) {
            return $this->storeError($exception);
        }

        return $this->json(['session' => $session], 200, ['Cache-Control' => 'no-store']);
    }

    #[Route('/api/concert/session/{sessionId}/heartbeat', name: 'app_concert_client_heartbeat', methods: ['POST'])]
    public function heartbeat(string $sessionId, Request $request, ConcertSessionStore $store): JsonResponse
    {
        try {
            $session = $store->heartbeat(
                $sessionId,
                (string) $request->headers->get('X-Concert-Client-Id'),
                (string) $request->headers->get('X-Concert-Client-Key'),
            );
        } catch (\RuntimeException $exception) {
            return $this->storeError($exception);
        }

        return $this->json(['session' => $session]);
    }

    private function payload(Request $request): array
    {
        try {
            $payload = $request->toArray();
        } catch (\Throwable) {
            return [];
        }

        return is_array($payload) ? $payload : [];
    }

    private function storeError(\RuntimeException $exception): JsonResponse
    {
        $code = $exception->getMessage();

        return match ($code) {
            'SESSION_NOT_FOUND' => $this->json(['error' => $code], 404),
            'SESSION_FULL' => $this->json(['error' => $code], 409),
            'INVALID_INVITE',
            'INVALID_CLIENT',
            'INVALID_CLIENT_KEY',
            'NOT_MASTER',
            'INVALID_MASTER_KEY' => $this->json(['error' => $code], 403),
            default => $this->json(['error' => 'SESSION_ERROR'], 500),
        };
    }
}
