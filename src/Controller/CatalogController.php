<?php

declare(strict_types=1);

namespace App\Controller;

use App\Domain\Song\Song;
use App\Domain\Song\SongRating;
use App\Domain\Song\SongRatingRepository;
use App\Domain\Song\SongRepository;
use App\Domain\Song\SongStatus;
use App\Domain\User\User;
use App\Domain\User\UserRepository;
use App\Service\ListPagination;
use App\Service\SongPublicationQueue;
use Doctrine\ORM\EntityManagerInterface;
use Symfony\Bundle\FrameworkBundle\Controller\AbstractController;
use Symfony\Component\HttpFoundation\Request;
use Symfony\Component\HttpFoundation\Response;
use Symfony\Component\Routing\Attribute\Route;
use Symfony\Contracts\Translation\TranslatorInterface;

final class CatalogController extends AbstractController
{
    #[Route('/catalog', name: 'app_catalog', methods: ['GET'])]
    public function index(
        Request $request,
        SongRepository $songs,
        SongRatingRepository $ratings,
        UserRepository $users,
        ListPagination $pagination,
    ): Response {
        $user = $this->getUser();
        $query = trim((string) $request->query->get('q', ''));

        $sort = (string) $request->query->get('sort', 'title');
        $sort = in_array($sort, ['title', 'artist'], true) ? $sort : 'title';

        $letter = mb_strtoupper(trim((string) $request->query->get('letter', '')));
        $letter = preg_match('/^[A-Z]$/', $letter) ? $letter : null;

        $pager = null;
        $editors = [];
        $adminFilters = [
            'status' => '',
            'editor' => '',
        ];

        if ($this->isGranted('ROLE_ADMIN')) {
            $statusFilter = (string) $request->query->get('status', '');
            $editorFilter = (string) $request->query->get('editor', '');

            $qb = $songs->createQueryBuilder('s')
                ->leftJoin('s.editor', 'editor')
                ->addSelect('editor');

            if ($query !== '') {
                $qb->andWhere(
                    "(LOWER(s.title) LIKE :q
                      OR LOWER(s.artist) LIKE :q
                      OR LOWER(COALESCE(s.author, '')) LIKE :q
                      OR LOWER(COALESCE(s.composer, '')) LIKE :q
                      OR LOWER(COALESCE(editor.displayName, '')) LIKE :q)"
                )->setParameter('q', '%'.mb_strtolower($query).'%');
            }

            if ($letter !== null) {
                $letterField = $sort === 'artist' ? 's.artist' : 's.title';
                $qb->andWhere(sprintf('UPPER(SUBSTRING(%s, 1, 1)) = :letter', $letterField))
                    ->setParameter('letter', $letter);
            }

            $status = SongStatus::tryFrom($statusFilter);
            if ($status instanceof SongStatus) {
                $qb->andWhere('s.status = :status')
                    ->setParameter('status', $status->value);
            } else {
                $statusFilter = '';
            }

            if ($editorFilter === 'none') {
                $qb->andWhere('s.editor IS NULL');
            } elseif (ctype_digit($editorFilter) && (int) $editorFilter > 0) {
                $qb->andWhere('editor.id = :editorId')
                    ->setParameter('editorId', (int) $editorFilter);
            } else {
                $editorFilter = '';
            }

            $primarySort = $sort === 'artist' ? 's.artist' : 's.title';
            $secondarySort = $sort === 'artist' ? 's.title' : 's.artist';

            $qb->orderBy('LOWER('.$primarySort.')', 'ASC')
                ->addOrderBy('LOWER('.$secondarySort.')', 'ASC');

            $pager = $pagination->paginate($qb, $request, 's', 'page', 50);
            $visibleSongs = $pager['rows'];

            $editors = $this->activeEditors($users);
            $adminFilters = [
                'status' => $statusFilter,
                'editor' => $editorFilter,
            ];
        } elseif ($user instanceof User && $this->isGranted('ROLE_EDITOR')) {
            $visibleSongs = $songs->findForEditor($user, $query, $sort, $letter);
        } else {
            $visibleSongs = $songs->findPublished($query, $sort, $letter);
        }

        return $this->render('catalog/index.html.twig', [
            'songs' => $visibleSongs,
            'ratings' => $ratings->summariesForSongs($visibleSongs),
            'query' => $query,
            'sort' => $sort,
            'letter' => $letter,
            'alphabet' => range('A', 'Z'),
            'can_import' => $this->isGranted('ROLE_ADMIN') || $this->isGranted('ROLE_EDITOR'),
            'is_public_catalog' => !$user instanceof User,
            'admin_pager' => $pager,
            'admin_editors' => $editors,
            'admin_filters' => $adminFilters,
            'admin_statuses' => SongStatus::cases(),
        ]);
    }

    #[Route('/catalog/song/{id}/admin', name: 'admin_catalog_song_update', requirements: ['id' => '\d+'], methods: ['POST'])]
    public function adminUpdateSong(
        Song $song,
        Request $request,
        UserRepository $users,
        EntityManagerInterface $em,
        TranslatorInterface $translator,
        SongPublicationQueue $publicationQueue,
    ): Response {
        $this->denyAccessUnlessGranted('ROLE_ADMIN');

        if (!$this->isCsrfTokenValid(
            'admin_catalog_song_'.$song->getId(),
            (string) $request->request->get('_token'),
        )) {
            throw $this->createAccessDeniedException();
        }

        // R35.5: propriétaire immuable; délégations via SongCollaborator.

        $wasPublished = $song->isPublished();
        $this->applyStatus($song, $requestedStatus);

        $em->flush();

        if (!$wasPublished && $song->isPublished()) {
            $publicationQueue->enqueue($song);
            $this->addFlash(
                'success',
                $translator->trans('publication_mail.queued', [], 'publication_mail'),
            );
        }

        $this->addFlash(
            'success',
            $translator->trans('catalog_admin.updated', ['%title%' => $song->getTitle()], 'admin_catalog'),
        );

        return $this->redirectToRoute('app_catalog', $this->catalogReturnParams($request));
    }

    #[Route('/catalog/song/{id}/delete', name: 'admin_catalog_song_delete', requirements: ['id' => '\d+'], methods: ['POST'])]
    public function adminDeleteSong(
        Song $song,
        Request $request,
        EntityManagerInterface $em,
        TranslatorInterface $translator,
    ): Response {
        $this->denyAccessUnlessGranted('ROLE_ADMIN');

        if (!$this->isCsrfTokenValid(
            'admin_catalog_song_delete_'.$song->getId(),
            (string) $request->request->get('_token'),
        )) {
            throw $this->createAccessDeniedException();
        }

        $title = $song->getTitle();
        $em->remove($song);
        $em->flush();

        $this->addFlash(
            'success',
            $translator->trans('catalog_admin.deleted', ['%title%' => $title], 'admin_catalog'),
        );

        return $this->redirectToRoute('app_catalog', $this->catalogReturnParams($request));
    }

    #[Route('/song/{id}', name: 'app_song_workspace', requirements: ['id' => '\d+'], methods: ['GET'])]
    public function song(Song $song, SongRatingRepository $ratings): Response
    {
        $user = $this->getUser();

        if (!$this->canViewSong($song, $user)) {
            throw $this->createNotFoundException();
        }

        $isOwnerEditor = $this->isOwnerEditor($song, $user);
        $canEdit = $this->isGranted('ROLE_ADMIN') || $isOwnerEditor;

        $canUseKaraoke = $this->isGranted('ROLE_ADMIN')
            || ($user instanceof User && !$this->isGranted('ROLE_EDITOR') && $song->isPublished())
            || $isOwnerEditor;

        $userRating = $user instanceof User
            ? $ratings->findForUserAndSong($user, $song)
            : null;

        return $this->render('song/workspace.html.twig', [
            'song' => $song,
            'can_edit' => $canEdit,
            'can_publish' => $canEdit,
            'can_play_audio' => $user instanceof User,
            'can_use_karaoke' => $canUseKaraoke,
            'karaoke_preview_seconds' => $user instanceof User ? 0 : 20,
            'rating_summary' => $ratings->summaryForSong($song),
            'user_rating' => $userRating?->getRating(),
        ]);
    }

    #[Route('/song/{id}/rating', name: 'app_song_rating', requirements: ['id' => '\d+'], methods: ['POST'])]
    public function rate(
        Song $song,
        Request $request,
        SongRatingRepository $ratings,
        EntityManagerInterface $em,
    ): Response {
        $user = $this->getUser();
        if (!$user instanceof User) {
            throw $this->createAccessDeniedException();
        }

        if (!$this->canViewSong($song, $user)) {
            throw $this->createNotFoundException();
        }

        if (!$this->isCsrfTokenValid('song_rating_' . $song->getId(), (string) $request->request->get('_token'))) {
            throw $this->createAccessDeniedException();
        }

        $rating = filter_var(
            $request->request->get('rating'),
            FILTER_VALIDATE_INT,
            ['options' => ['min_range' => 0, 'max_range' => 5]],
        );

        if ($rating === false) {
            $this->addFlash('error', 'song.rating.invalid');
            return $this->redirectToRoute('app_song_workspace', [
                '_locale' => $request->getLocale(),
                'id' => $song->getId(),
            ]);
        }

        $existing = $ratings->findForUserAndSong($user, $song);

        if ($rating === 0) {
            if ($existing instanceof SongRating) {
                $em->remove($existing);
                $em->flush();
            }
            $this->addFlash('success', 'song.rating.removed');
        } else {
            if ($existing instanceof SongRating) {
                $existing->setRating($rating);
            } else {
                $em->persist(new SongRating($song, $user, $rating));
            }

            $em->flush();
            $this->addFlash('success', 'song.rating.saved');
        }

        return $this->redirectToRoute('app_song_workspace', [
            '_locale' => $request->getLocale(),
            'id' => $song->getId(),
        ]);
    }

    #[Route('/song/{id}/publication', name: 'app_song_publication', requirements: ['id' => '\d+'], methods: ['POST'])]
    public function publication(
        Song $song,
        Request $request,
        EntityManagerInterface $em,
        TranslatorInterface $translator,
        SongPublicationQueue $publicationQueue,
    ): Response {
        $user = $this->getUser();
        $canEdit = $this->isGranted('ROLE_ADMIN') || $this->isOwnerEditor($song, $user);

        if (!$canEdit) {
            throw $this->createAccessDeniedException();
        }

        if (!$this->isCsrfTokenValid('song_publication_' . $song->getId(), (string) $request->request->get('_token'))) {
            throw $this->createAccessDeniedException();
        }

        $action = (string) $request->request->get('action');

        $wasPublished = $song->isPublished();

        if ($action === 'publish') {
            $song->publish();
            $this->addFlash('success', 'song.publication.published');
        } elseif ($action === 'unpublish') {
            $song->unpublish();
            $this->addFlash('success', 'song.publication.unpublished');
        } elseif ($action === 'imported') {
            $song->markImported();
            $this->addFlash('success', $translator->trans('catalog_admin.reset_imported', [], 'admin_catalog'));
        } else {
            throw $this->createNotFoundException();
        }

        $em->flush();

        if (!$wasPublished && $song->isPublished()) {
            $publicationQueue->enqueue($song);
            $this->addFlash(
                'success',
                $translator->trans('publication_mail.queued', [], 'publication_mail'),
            );
        }

        return $this->redirectToRoute('app_song_workspace', [
            '_locale' => $request->getLocale(),
            'id' => $song->getId(),
        ]);
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
            ->orderBy('LOWER(u.displayName)', 'ASC')
            ->getQuery()
            ->getResult();
    }

    private function applyStatus(Song $song, SongStatus $status): void
    {
        match ($status) {
            SongStatus::Imported => $song->markImported(),
            SongStatus::Analyzed => $song->markAnalyzed(),
            SongStatus::Editing => $song->markEditing(),
            SongStatus::Published => $song->publish($song->getPublishedAt()),
        };
    }

    /** @return array<string,string|int> */
    private function catalogReturnParams(Request $request): array
    {
        $params = ['_locale' => $request->getLocale()];

        foreach (['q', 'sort', 'letter', 'status', 'editor', 'page'] as $key) {
            $value = trim((string) $request->request->get('return_'.$key, ''));

            if ($value === '') {
                continue;
            }

            $params[$key] = $key === 'page' ? max(1, (int) $value) : $value;
        }

        return $params;
    }

    private function canViewSong(Song $song, mixed $user): bool
    {
        return $this->isGranted('ROLE_ADMIN')
            || $song->isPublished()
            || $this->isOwnerEditor($song, $user);
    }

    private function isOwnerEditor(Song $song, mixed $user): bool
    {
        return $user instanceof User
            && $this->isGranted('ROLE_EDITOR')
            && $song->getEditor()?->getId() === $user->getId();
    }
}
