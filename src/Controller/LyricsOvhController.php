<?php
declare(strict_types=1);

namespace App\Controller;

use App\Domain\Song\Song;
use App\Domain\User\User;
use App\Service\LyricsOvhClient;
use App\Service\LyricsSourceHistoryService;
use App\Service\SongAccessPolicy;
use Symfony\Bundle\FrameworkBundle\Controller\AbstractController;
use Symfony\Component\HttpFoundation\JsonResponse;
use Symfony\Component\HttpFoundation\Request;
use Symfony\Component\HttpFoundation\Response;
use Symfony\Component\Routing\Attribute\Route;

#[Route('/song/{id}/lab/lyrics/ovh', requirements: ['id' => '\\d+'])]
final class LyricsOvhController extends AbstractController
{
    public function __construct(private readonly SongAccessPolicy $songAccess)
    {
    }


    #[Route('/autocomplete', name: 'app_song_lyrics_ovh_autocomplete', methods: ['POST'])]
    public function autocomplete(Song $song, Request $request, LyricsOvhClient $client): JsonResponse
    {
        $this->requireEditor($song);
        $payload = $request->toArray();

        if (!$this->isCsrfTokenValid(
            'song_lyrics_ovh_'.$song->getId(),
            (string) ($payload['_token'] ?? ''),
        )) {
            return $this->json(['error' => 'invalid_csrf'], Response::HTTP_FORBIDDEN);
        }

        $query = trim((string) ($payload['query'] ?? ''));
        if (mb_strlen($query) < 2 || mb_strlen($query) > 180) {
            return $this->json(['ok' => true, 'results' => []]);
        }

        return $this->json([
            'ok' => true,
            'results' => $client->suggestFast($query, 6),
        ]);
    }

    #[Route('/search', name: 'app_song_lyrics_ovh_search', methods: ['POST'])]
    public function search(Song $song, Request $request, LyricsOvhClient $client): JsonResponse
    {
        $this->requireEditor($song);
        $payload = $request->toArray();

        if (!$this->isCsrfTokenValid(
            'song_lyrics_ovh_'.$song->getId(),
            (string) ($payload['_token'] ?? ''),
        )) {
            return $this->json(['error' => 'invalid_csrf'], Response::HTTP_FORBIDDEN);
        }

        $query = trim((string) ($payload['query'] ?? ''));
        if ($query === '' || mb_strlen($query) > 180) {
            return $this->json(['error' => 'invalid_query'], Response::HTTP_UNPROCESSABLE_ENTITY);
        }

        return $this->json([
            'ok' => true,
            'results' => $client->search(
                $query,
                8,
                $song->getArtist(),
                $song->getTitle(),
            ),
        ]);
    }

    #[Route('/import', name: 'app_song_lyrics_ovh_import', methods: ['POST'])]
    public function import(
        Song $song,
        Request $request,
        LyricsOvhClient $client,
        LyricsSourceHistoryService $history,
    ): JsonResponse {
        $user = $this->requireEditor($song);
        $payload = $request->toArray();

        if (!$this->isCsrfTokenValid(
            'song_lyrics_ovh_'.$song->getId(),
            (string) ($payload['_token'] ?? ''),
        )) {
            return $this->json(['error' => 'invalid_csrf'], Response::HTTP_FORBIDDEN);
        }

        $artist = trim((string) ($payload['artist'] ?? ''));
        $title = trim((string) ($payload['title'] ?? ''));

        if ($artist === '' || $title === '' || mb_strlen($artist) > 180 || mb_strlen($title) > 180) {
            return $this->json(['error' => 'invalid_song'], Response::HTTP_UNPROCESSABLE_ENTITY);
        }

        $lyrics = $client->fetchLyrics($artist, $title);
        if ($lyrics === null) {
            return $this->json(['error' => 'lyrics_not_found'], Response::HTTP_NOT_FOUND);
        }

        if (mb_strlen($lyrics) > 500000) {
            return $this->json(['error' => 'lyrics_too_large'], Response::HTTP_UNPROCESSABLE_ENTITY);
        }

        $history->archiveCurrentIfChanged(
            $song,
            $user,
            'manual',
            'Sauvegarde automatique avant recherche Lyrics.ovh.',
        );

        $comment = sprintf('Paroles recherchées avec Lyrics.ovh — %s — %s', $artist, $title);
        $revision = $history->saveVersion($song, $lyrics, $user, 'lyrics_ovh', $comment);

        return $this->json([
            'ok' => true,
            'text' => $lyrics,
            'artist' => $artist,
            'title' => $title,
            'revision_id' => $revision->getId(),
        ]);
    }

    private function requireEditor(Song $song): User
    {
        $user = $this->getUser();

        if (!$user instanceof User
            || !$this->songAccess->canEdit($song, $user, $this->isGranted('ROLE_ADMIN'))) {
            throw $this->createAccessDeniedException();
        }

        return $user;
    }
}
