<?php
declare(strict_types=1);

namespace App\EventSubscriber;

use App\Domain\User\User;
use Symfony\Bundle\SecurityBundle\Security;
use Symfony\Component\EventDispatcher\EventSubscriberInterface;
use Symfony\Component\HttpFoundation\RedirectResponse;
use Symfony\Component\HttpKernel\Event\RequestEvent;
use Symfony\Component\HttpKernel\KernelEvents;
use Symfony\Component\Routing\Generator\UrlGeneratorInterface;

final class DisplayUserGateSubscriber implements EventSubscriberInterface
{
    private const ALLOWED_ROUTES = [
        'app_live_display_home',
        'app_live_open',
        'app_live_display',
        'app_live_karaoke_song_data',
        'app_live_karaoke_state_read',
        'app_live_state',
        'app_live_song_data',
        'app_logout',
        'app_locale',
    ];

    public function __construct(
        private readonly Security $security,
        private readonly UrlGeneratorInterface $urls,
    ) {
    }

    public static function getSubscribedEvents(): array
    {
        return [
            KernelEvents::REQUEST => ['onKernelRequest', -20],
        ];
    }

    public function onKernelRequest(RequestEvent $event): void
    {
        if (!$event->isMainRequest()) {
            return;
        }

        $request = $event->getRequest();
        $route = (string) $request->attributes->get('_route', '');

        if ($route === '' || str_starts_with($route, '_')) {
            return;
        }

        $user = $this->security->getUser();
        if (!$user instanceof User || !in_array('ROLE_DISPLAY', $user->getRoles(), true)) {
            return;
        }

        if (in_array($route, self::ALLOWED_ROUTES, true)) {
            return;
        }

        $event->setResponse(new RedirectResponse(
            $this->urls->generate('app_live_display_home')
        ));
    }
}
