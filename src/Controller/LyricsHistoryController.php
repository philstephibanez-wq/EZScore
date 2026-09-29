<?php
declare(strict_types=1);

namespace App\Controller;

use App\Domain\Song\LyricsSourceRevision;
use App\Domain\Song\LyricsSourceRevisionRepository;
use App\Domain\Song\Song;
use App\Domain\User\User;
use App\Service\LyricsSourceHistoryService;
use App\Service\SongAccessPolicy;
use Symfony\Bundle\FrameworkBundle\Controller\AbstractController;
use Symfony\Component\HttpFoundation\JsonResponse;
use Symfony\Component\HttpFoundation\Request;
use Symfony\Component\HttpFoundation\Response;
use Symfony\Component\Routing\Attribute\Route;

#[Route('/song/{id}/lab/lyrics/history', requirements: ['id' => '\d+'])]
final class LyricsHistoryController extends AbstractController
{
    public function __construct(private readonly SongAccessPolicy $songAccess)
    {
    }

    #[Route('', name: 'app_song_lyrics_history', methods: ['GET'])]
    public function list(Song $song, LyricsSourceRevisionRepository $revisions): JsonResponse
    {
        $this->requireEditor($song);
        $currentRevisionId = $song->getLyricsCurrentRevisionId();

        return $this->json([
            'revisions' => array_map(
                fn (LyricsSourceRevision $revision): array => $this->serialise($revision, $currentRevisionId),
                $revisions->findForSong($song),
            ),
        ]);
    }

    #[Route('/save', name: 'app_song_lyrics_history_save', methods: ['POST'])]
    public function save(
        Song $song,
        Request $request,
        LyricsSourceHistoryService $history,
    ): JsonResponse {
        $user = $this->requireEditor($song);
        $payload = $request->toArray();

        if (!$this->isCsrfTokenValid(
            'song_lyrics_history_'.$song->getId(),
            (string) ($payload['_token'] ?? ''),
        )) {
            return $this->json(['error' => 'invalid_csrf'], Response::HTTP_FORBIDDEN);
        }

        $content = (string) ($payload['text'] ?? '');
        if (mb_strlen($content) > 500000) {
            return $this->json(['error' => 'lyrics_too_large'], Response::HTTP_UNPROCESSABLE_ENTITY);
        }

        $comment = isset($payload['comment']) ? (string) $payload['comment'] : null;
        if ($comment !== null && mb_strlen($comment) > 1000) {
            return $this->json(['error' => 'comment_too_large'], Response::HTTP_UNPROCESSABLE_ENTITY);
        }

        $revision = $history->saveVersion(
            $song,
            $content,
            $user,
            (string) ($payload['source_type'] ?? 'manual'),
            $comment,
        );

        return $this->json([
            'ok' => true,
            'revision_id' => $revision->getId(),
            'text' => $revision->getContent(),
        ]);
    }

    #[Route('/{revisionId}/restore', name: 'app_song_lyrics_history_restore', requirements: ['revisionId' => '\d+'], methods: ['POST'])]
    public function restore(
        Song $song,
        int $revisionId,
        Request $request,
        LyricsSourceRevisionRepository $revisions,
        LyricsSourceHistoryService $history,
    ): JsonResponse {
        $user = $this->requireEditor($song);
        $payload = $request->toArray();

        if (!$this->isCsrfTokenValid(
            'song_lyrics_history_'.$song->getId(),
            (string) ($payload['_token'] ?? ''),
        )) {
            return $this->json(['error' => 'invalid_csrf'], Response::HTTP_FORBIDDEN);
        }

        $revision = $revisions->find($revisionId);
        if (!$revision instanceof LyricsSourceRevision || $revision->getSong()->getId() !== $song->getId()) {
            return $this->json(['error' => 'not_found'], Response::HTTP_NOT_FOUND);
        }

        $restored = $history->restore($song, $revision, $user);

        return $this->json([
            'ok' => true,
            'text' => $restored->getContent(),
            'revision_id' => $restored->getId(),
        ]);
    }

    #[Route('/{revisionId}/delete', name: 'app_song_lyrics_history_delete', requirements: ['revisionId' => '\d+'], methods: ['POST'])]
    public function delete(
        Song $song,
        int $revisionId,
        Request $request,
        LyricsSourceRevisionRepository $revisions,
        LyricsSourceHistoryService $history,
    ): JsonResponse {
        $this->requireEditor($song);
        $payload = $request->toArray();

        if (!$this->isCsrfTokenValid(
            'song_lyrics_history_'.$song->getId(),
            (string) ($payload['_token'] ?? ''),
        )) {
            return $this->json(['error' => 'invalid_csrf'], Response::HTTP_FORBIDDEN);
        }

        $revision = $revisions->find($revisionId);
        if (!$revision instanceof LyricsSourceRevision || $revision->getSong()->getId() !== $song->getId()) {
            return $this->json(['error' => 'not_found'], Response::HTTP_NOT_FOUND);
        }

        try {
            $history->delete($song, $revision);
        } catch (\LogicException $exception) {
            if ($exception->getMessage() === 'current_revision') {
                return $this->json(['error' => 'current_revision'], Response::HTTP_CONFLICT);
            }
            throw $exception;
        }

        return $this->json(['ok' => true]);
    }

    private function serialise(LyricsSourceRevision $revision, ?int $currentRevisionId): array
    {
        $author = $revision->getCreatedBy();

        return [
            'id' => $revision->getId(),
            'source_type' => $revision->getSourceType(),
            'comment' => $revision->getComment(),
            'created_at' => $revision->getCreatedAt()->format(DATE_ATOM),
            'created_by' => $author?->getDisplayName(),
            'is_current' => $currentRevisionId !== null && $revision->getId() === $currentRevisionId,
        ];
    }

    private function requireEditor(Song $song): User
    {
        $user = $this->getUser();
        if (!$user instanceof User || !$this->songAccess->canEdit($song, $user, $this->isGranted('ROLE_ADMIN'))) {
            throw $this->createAccessDeniedException();
        }
        return $user;
    }
}
