<?php

declare(strict_types=1);

namespace App\Controller;

use App\Domain\Song\Song;
use App\Domain\Song\SongStatus;
use App\Domain\User\User;
use App\Domain\User\UserRepository;
use App\Service\SongImportStorage;
use App\Service\SongStemStorage;
use App\Service\ChordTimelineStorage;
use App\Domain\Song\SongTimelineEventRepository;
use Doctrine\ORM\EntityManagerInterface;
use Psr\Log\LoggerInterface;
use Symfony\Component\DependencyInjection\Attribute\Autowire;
use Symfony\Bundle\FrameworkBundle\Controller\AbstractController;
use Symfony\Component\HttpFoundation\File\UploadedFile;
use Symfony\Component\HttpFoundation\Request;
use Symfony\Component\HttpFoundation\Response;
use Symfony\Component\Routing\Attribute\Route;

final class SongImportController extends AbstractController
{
    #[Route('/import', name: 'app_song_import', methods: ['GET', 'POST'])]
    public function import(
        Request $request,
        UserRepository $users,
        SongImportStorage $storage,
        EntityManagerInterface $em,
        LoggerInterface $logger,
        #[Autowire('%kernel.environment%')]
        string $environment,
    ): Response {
        $user = $this->getUser();
        if (!$user instanceof User || (!$this->isGranted('ROLE_ADMIN') && !$this->isGranted('ROLE_EDITOR'))) {
            throw $this->createAccessDeniedException();
        }

        $editors = [];
        if ($this->isGranted('ROLE_ADMIN')) {
            $editors = $users->createQueryBuilder('u')
                ->andWhere('u.active = :active')
                ->andWhere('(u.roles LIKE :editor OR u.roles LIKE :admin)')
                ->setParameter('active', true)
                ->setParameter('editor', '%ROLE_EDITOR%')
                ->setParameter('admin', '%ROLE_ADMIN%')
                ->orderBy('u.displayName', 'ASC')
                ->getQuery()
                ->getResult();
        }

        if ($request->isMethod('POST')) {
            if (!$this->isCsrfTokenValid('song_import', (string) $request->request->get('_token'))) {
                throw $this->createAccessDeniedException();
            }

            try {
                $song = $this->buildSong($request, $user, $users);

                $audio = $request->files->get('audio');
                if (!$audio instanceof UploadedFile) {
                    throw new \InvalidArgumentException('catalog.import.validation.audio_required');
                }

                if (!$audio->isValid()) {
                    $errorKey = match ($audio->getError()) {
                        UPLOAD_ERR_INI_SIZE, UPLOAD_ERR_FORM_SIZE => 'catalog.import.validation.audio_too_large',
                        UPLOAD_ERR_PARTIAL => 'catalog.import.validation.audio_partial',
                        default => 'catalog.import.validation.audio_upload',
                    };
                    throw new \InvalidArgumentException($errorKey);
                }

                $audioData = $storage->storeAudio($audio);
                $song->setImportedAudio(
                    $audioData['original_name'],
                    $audioData['storage_path'],
                    $audioData['mime_type'],
                    $audioData['size'],
                    $audioData['sha256'],
                );

                $cover = $request->files->get('cover');
                if ($cover instanceof UploadedFile && !$cover->isValid()) {
                    $errorKey = match ($cover->getError()) {
                        UPLOAD_ERR_INI_SIZE, UPLOAD_ERR_FORM_SIZE => 'catalog.import.validation.cover_too_large',
                        UPLOAD_ERR_PARTIAL => 'catalog.import.validation.cover_partial',
                        default => 'catalog.import.validation.cover_upload',
                    };
                    throw new \InvalidArgumentException($errorKey);
                }

                $song->setCoverPath($storage->storeCover($cover instanceof UploadedFile ? $cover : null));

                $em->persist($song);
                $em->flush();

                $this->addFlash('success', 'catalog.import.created');

                return $this->redirectToRoute('app_song_workspace', [
                    '_locale' => $request->getLocale(),
                    'id' => $song->getId(),
                ]);
            } catch (\InvalidArgumentException $e) {
                $message = $e->getMessage();
                $this->addFlash('error', str_starts_with($message, 'catalog.') ? $message : 'catalog.import.validation.invalid');
            } catch (\Throwable $e) {
                $logger->error('Song import failed', [
                    'exception_class' => $e::class,
                    'exception_message' => $e->getMessage(),
                    'exception_file' => $e->getFile(),
                    'exception_line' => $e->getLine(),
                    'song_title' => (string) $request->request->get('title', ''),
                    'song_artist' => (string) $request->request->get('artist', ''),
                    'audio_original_name' => $request->files->get('audio') instanceof UploadedFile
                        ? $request->files->get('audio')->getClientOriginalName()
                        : null,
                    'user_id' => $user->getId(),
                    'user_email' => $user->getUserIdentifier(),
                    'exception' => $e,
                ]);

                if ($environment === 'dev') {
                    $this->addFlash(
                        'error',
                        sprintf(
                            'Import DEV: %s — %s (%s:%d)',
                            $e::class,
                            $e->getMessage(),
                            basename($e->getFile()),
                            $e->getLine(),
                        ),
                    );
                } else {
                    $this->addFlash('error', 'catalog.import.validation.failed');
                }
            }
        }

        return $this->render('song/import.html.twig', [
            'editors' => $editors,
            'current_editor' => $user,
            'status_choices' => [SongStatus::Imported, SongStatus::Editing, SongStatus::Published],
        ]);
    }

    #[Route('/song/{id}/reimport', name: 'app_song_reimport', requirements: ['id' => '\d+'], methods: ['POST'])]
    public function reimport(
        Song $song,
        Request $request,
        SongImportStorage $storage,
        SongStemStorage $stems,
        ChordTimelineStorage $chords,
        SongTimelineEventRepository $timeline,
        EntityManagerInterface $em,
    ): Response {
        $user = $this->getUser();
        $canEdit = $user instanceof User && (
            $this->isGranted('ROLE_ADMIN')
            || ($this->isGranted('ROLE_EDITOR') && $song->getEditor()?->getId() === $user->getId())
        );
        if (!$canEdit) throw $this->createAccessDeniedException();
        if (!$this->isCsrfTokenValid('song_reimport_'.$song->getId(), (string) $request->request->get('_token'))) {
            throw $this->createAccessDeniedException();
        }
        $audio = $request->files->get('audio');
        if (!$audio instanceof UploadedFile || !$audio->isValid()) {
            $this->addFlash('error', 'Réimportation impossible : fichier audio invalide.');
            return $this->redirectToRoute('app_song_workspace', ['_locale'=>$request->getLocale(),'id'=>$song->getId()]);
        }
        $audioData = $storage->storeAudio($audio);
        $timeline->deleteAllForSong($song);
        $stems->deleteForSong($song);
        $chords->deleteForSong($song);
        $song->setImportedAudio($audioData['original_name'], $audioData['storage_path'], $audioData['mime_type'], $audioData['size'], $audioData['sha256']);
        $song->markImported();
        $em->flush();
        $this->addFlash('success', 'Audio réimporté ; analyses précédentes invalidées.');
        return $this->redirectToRoute('app_song_workspace', ['_locale'=>$request->getLocale(),'id'=>$song->getId()]);
    }

    private function buildSong(Request $request, User $user, UserRepository $users): Song
    {
        $title = trim((string) $request->request->get('title'));
        $artist = trim((string) $request->request->get('artist'));

        if ($title === '' || $artist === '') {
            throw new \InvalidArgumentException('catalog.import.validation.required');
        }

        $song = (new Song())
            ->setTitle($title)
            ->setArtist($artist)
            ->setAuthor((string) $request->request->get('author'))
            ->setComposer((string) $request->request->get('composer'))
            ->setTimeSignature((string) $request->request->get('time_signature', 'auto'))
            ->setCapo((int) $request->request->get('capo', 0))
            ->setStrummingPrimary((string) $request->request->get('strumming_primary'))
            ->setStrummingAlternate((string) $request->request->get('strumming_alternate'))
            ->setComment((string) $request->request->get('comment'));

        if ($this->isGranted('ROLE_ADMIN')) {
            $editorId = (int) $request->request->get('editor_id');
            $editor = $editorId > 0 ? $users->find($editorId) : $user;
            if (!$editor instanceof User) {
                throw new \InvalidArgumentException('catalog.import.validation.editor');
            }
            $song->setEditor($editor);
        } else {
            $song->setEditor($user);
        }

        $status = SongStatus::tryFrom((string) $request->request->get('status', SongStatus::Imported->value));
        if (!$status instanceof SongStatus || $status === SongStatus::Analyzed) {
            throw new \InvalidArgumentException('catalog.import.validation.status');
        }

        match ($status) {
            SongStatus::Imported => $song->markImported(),
            SongStatus::Editing => $song->markEditing(),
            SongStatus::Published => $song->publish(),
            SongStatus::Analyzed => throw new \LogicException('Analyzed cannot be selected during import.'),
        };

        return $song;
    }
}
