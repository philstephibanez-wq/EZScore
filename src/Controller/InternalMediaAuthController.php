<?php

declare(strict_types=1);

namespace App\Controller;

use App\Domain\Song\Song;
use App\Domain\User\User;
use App\Service\SongAccessPolicy;
use App\Service\SongStemPlaybackStorage;
use Doctrine\ORM\EntityManagerInterface;
use Symfony\Bundle\FrameworkBundle\Controller\AbstractController;
use Symfony\Component\HttpFoundation\Request;
use Symfony\Component\HttpFoundation\Response;
use Symfony\Component\Routing\Attribute\Route;

final class InternalMediaAuthController extends AbstractController
{
    #[Route('/internal/media/auth', name: 'app_internal_media_auth', methods: ['GET'])]
    public function __invoke(
        Request $request,
        EntityManagerInterface $em,
        SongAccessPolicy $songAccess,
        SongStemPlaybackStorage $playback,
    ): Response {
        $forwardedUri = (string) $request->headers->get('X-Forwarded-Uri', '');
        $path = (string) parse_url($forwardedUri, PHP_URL_PATH);

        if (!preg_match(
            '#^/song-(\d+)/([a-f0-9]{64})/playback/(run-[A-Za-z0-9]+)/([A-Za-z0-9_]+)\.opus$#',
            $path,
            $match,
        )) {
            return new Response('', Response::HTTP_FORBIDDEN);
        }

        $song = $em->getRepository(Song::class)->find((int) $match[1]);
        $user = $this->getUser();

        if (
            !$song instanceof Song
            || !$user instanceof User
            || !$songAccess->canEdit($song, $user, $this->isGranted('ROLE_ADMIN'))
        ) {
            return new Response('', Response::HTTP_FORBIDDEN);
        }

        $expected = $playback->mediaRelativePath($song, $match[4]);
        $requested = ltrim($path, '/');

        if ($expected === null || !hash_equals($expected, $requested)) {
            return new Response('', Response::HTTP_FORBIDDEN);
        }

        return new Response('', Response::HTTP_NO_CONTENT);
    }
}
