<?php

declare(strict_types=1);

namespace App\Controller;

use App\Domain\Song\Song;
use App\Domain\Song\SongRatingRepository;
use App\Domain\Song\SongStatus;
use App\Domain\User\User;
use App\Domain\User\UserRepository;
use App\Service\SongImportStorage;
use App\Service\SongAccessPolicy;
use Doctrine\ORM\EntityManagerInterface;
use Psr\Log\LoggerInterface;
use Symfony\Bundle\FrameworkBundle\Controller\AbstractController;
use Symfony\Component\HttpFoundation\File\UploadedFile;
use Symfony\Component\HttpFoundation\Request;
use Symfony\Component\HttpFoundation\Response;
use Symfony\Component\Routing\Attribute\Route;

final class SongEditController extends AbstractController
{
    public function __construct(private readonly SongAccessPolicy $songAccess) {}

    #[Route('/song/{id}/edit', name: 'app_song_edit', requirements: ['id' => '\d+'], methods: ['GET', 'POST'])]
    public function edit(
        Song $song,
        Request $request,
        UserRepository $users,
        SongRatingRepository $ratings,
        SongImportStorage $storage,
        EntityManagerInterface $em,
    ): Response {
        $user = $this->requireEditor($song);

        $editors = $this->isGranted('ROLE_ADMIN') ? $this->activeEditors($users) : [];

        if ($request->isMethod('POST')) {
            if (!$this->isCsrfTokenValid('song_edit_' . $song->getId(), (string) $request->request->get('_token'))) {
                throw $this->createAccessDeniedException();
            }

            try {
                $title = trim((string) $request->request->get('title'));
                $artist = trim((string) $request->request->get('artist'));

                if ($title === '' || $artist === '') {
                    throw new \InvalidArgumentException('song.edit.validation.required');
                }

                $song
                    ->setTitle($title)
                    ->setArtist($artist)
                    ->setAuthor((string) $request->request->get('author'))
                    ->setComposer((string) $request->request->get('composer'))
                    ->setTimeSignature((string) $request->request->get('time_signature', 'auto'))
                    ->setCapo((int) $request->request->get('capo', 0))
                    ->setStrummingPrimary((string) $request->request->get('strumming_primary'))
                    ->setStrummingAlternate((string) $request->request->get('strumming_alternate'))
                    ->setComment((string) $request->request->get('comment'));

                // R35.5: propriétaire immuable après création.

                $requestedStatus = SongStatus::tryFrom((string) $request->request->get('status', $song->getStatus()->value));
                if (!$requestedStatus instanceof SongStatus) {
                    throw new \InvalidArgumentException('song.edit.validation.status');
                }

                if ($requestedStatus === SongStatus::Analyzed && $song->getStatus() !== SongStatus::Analyzed) {
                    throw new \InvalidArgumentException('song.edit.validation.analyzed');
                }

                match ($requestedStatus) {
                    SongStatus::Imported => $song->markImported(),
                    SongStatus::Analyzed => $song->markAnalyzed(),
                    SongStatus::Editing => $song->markEditing(),
                    SongStatus::Published => $song->publish($song->getPublishedAt()),
                };

                $cover = $request->files->get('cover');
                if ($cover instanceof UploadedFile) {
                    if (!$cover->isValid()) {
                        throw new \InvalidArgumentException('catalog.import.validation.cover_upload');
                    }
                    $song->setCoverPath($storage->storeCover($cover));
                }

                $em->flush();
                $this->addFlash('success', 'song.edit.saved');

                return $this->redirectToRoute('app_song_workspace', [
                    '_locale' => $request->getLocale(),
                    'id' => $song->getId(),
                ]);
            } catch (\InvalidArgumentException $e) {
                $message = $e->getMessage();
                $this->addFlash('error', str_starts_with($message, 'song.') || str_starts_with($message, 'catalog.')
                    ? $message
                    : 'song.edit.validation.invalid');
            }
        }

        $statusChoices = [SongStatus::Imported];
        if ($song->getStatus() === SongStatus::Analyzed) {
            $statusChoices[] = SongStatus::Analyzed;
        }
        $statusChoices[] = SongStatus::Editing;
        $statusChoices[] = SongStatus::Published;

        return $this->render('song/edit.html.twig', [
            'song' => $song,
            'editors' => $editors,
            'current_editor' => $user,
            'status_choices' => $statusChoices,
            'rating_summary' => $ratings->summaryForSong($song),
            'user_rating' => null,
        ]);
    }

    #[Route('/song/{id}/audio', name: 'app_song_audio_replace', requirements: ['id' => '\d+'], methods: ['POST'])]
    public function replaceAudio(
        Song $song,
        Request $request,
        SongImportStorage $storage,
        EntityManagerInterface $em,
        LoggerInterface $logger,
    ): Response {
        $this->requireEditor($song);

        if (!$this->isCsrfTokenValid('song_audio_' . $song->getId(), (string) $request->request->get('_token'))) {
            throw $this->createAccessDeniedException();
        }

        $audio = $request->files->get('audio');
        if (!$audio instanceof UploadedFile) {
            $this->addFlash('error', 'song.edit.audio.required');
            return $this->redirectToEdit($song, $request);
        }

        try {
            $previous = [
                'original_name' => $song->getAudioOriginalName(),
                'storage_path' => $song->getAudioStoragePath(),
                'mime_type' => $song->getAudioMimeType(),
                'size' => $song->getAudioSize(),
                'sha256' => $song->getAudioSha256(),
                'imported_at' => $song->getImportedAt()?->format(DATE_ATOM),
                'replaced_at' => (new \DateTimeImmutable())->format(DATE_ATOM),
            ];

            if ($song->getAudioSha256()) {
                $storage->archiveAudioVersion((int) $song->getId(), $previous);
            }

            $audioData = $storage->storeAudio($audio);
            $song->setImportedAudio(
                $audioData['original_name'],
                $audioData['storage_path'],
                $audioData['mime_type'],
                $audioData['size'],
                $audioData['sha256'],
            );

            // A new source invalidates the meaning of previous analysis results.
            $song->markImported();

            $em->flush();

            $logger->info('Song audio replaced', [
                'song_id' => $song->getId(),
                'new_audio_sha256' => $song->getAudioSha256(),
                'new_audio_original_name' => $song->getAudioOriginalName(),
            ]);

            $this->addFlash('success', 'song.edit.audio.replaced');
        } catch (\InvalidArgumentException $e) {
            $message = $e->getMessage();
            $this->addFlash('error', str_starts_with($message, 'catalog.')
                ? $message
                : 'song.edit.audio.failed');
        } catch (\Throwable $e) {
            $logger->error('Song audio replacement failed', [
                'song_id' => $song->getId(),
                'exception' => $e,
            ]);
            $this->addFlash('error', 'song.edit.audio.failed');
        }

        return $this->redirectToEdit($song, $request);
    }

    private function requireEditor(Song $song): User
    {
        $user=$this->getUser();
        if(!$user instanceof User || !$this->songAccess->canEdit($song,$user,$this->isGranted('ROLE_ADMIN'))) throw $this->createAccessDeniedException();
        return $user;
    }

    /**
     * @return list<User>
     */
    private function activeEditors(UserRepository $users): array
    {
        return $users->createQueryBuilder('u')
            ->andWhere('u.active = :active')
            ->andWhere('(u.roles LIKE :editor OR u.roles LIKE :admin)')
            ->setParameter('active', true)
            ->setParameter('editor', '%ROLE_EDITOR%')
            ->setParameter('admin', '%ROLE_ADMIN%')
            ->orderBy('u.displayName', 'ASC')
            ->getQuery()
            ->getResult();
    }

    private function redirectToEdit(Song $song, Request $request): Response
    {
        return $this->redirectToRoute('app_song_edit', [
            '_locale' => $request->getLocale(),
            'id' => $song->getId(),
        ]);
    }
}
