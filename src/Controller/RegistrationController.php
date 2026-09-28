<?php

declare(strict_types=1);

namespace App\Controller;

use App\Domain\User\UserRepository;
use App\Service\RegistrationMailer;
use App\Service\RegistrationService;
use Symfony\Bundle\FrameworkBundle\Controller\AbstractController;
use Symfony\Component\HttpFoundation\Request;
use Symfony\Component\HttpFoundation\Response;
use App\Service\Exception\ActivationMailException;
use Symfony\Component\Routing\Attribute\Route;
use Symfony\Contracts\Translation\TranslatorInterface;

final class RegistrationController extends AbstractController
{
    #[Route('/register', name: 'app_register', methods: ['GET', 'POST'])]
    public function register(
        Request $request,
        UserRepository $users,
        RegistrationService $registration,
        RegistrationMailer $mailer,
        TranslatorInterface $translator,
    ): Response {
        if ($users->countAll() === 0) {
            return $this->redirectToRoute('app_first_run');
        }

        if ($this->getUser()) {
            return $this->redirectToRoute('app_dashboard');
        }

        // R38.14 PUBLIC DEVELOPMENT MODE: public registrations are temporarily closed.
        $this->addFlash('info', $request->getLocale() === 'en'
            ? 'Registrations will open soon.'
            : 'Les inscriptions ouvriront prochainement.');
        return $this->redirectToRoute('app_login', ['_locale' => $request->getLocale()]);

        $errors = [];

        if ($request->isMethod('POST')) {
            if (!$this->isCsrfTokenValid('register', (string) $request->request->get('_token'))) {
                throw $this->createAccessDeniedException();
            }

            $name = trim((string) $request->request->get('display_name'));
            $email = mb_strtolower(trim((string) $request->request->get('email')));
            $password = (string) $request->request->get('password');
            $confirm = (string) $request->request->get('confirm_password');

            if ($name === '') {
                $errors[] = 'registration.error.name';
            }
            if (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
                $errors[] = 'registration.error.email';
            }
            if ($users->findOneBy(['email' => $email]) !== null) {
                $errors[] = 'registration.error.email_used';
            }
            if (mb_strlen($password) < 10) {
                $errors[] = 'registration.error.password_length';
            }
            if ($password !== $confirm) {
                $errors[] = 'registration.error.password_match';
            }

            if ($errors === []) {
                try {
                    $result = $registration->register(
                        $name,
                        $email,
                        $password,
                        $request->getLocale(),
                    );
                } catch (\DomainException $exception) {
                    $errors[] = $exception->getMessage();
                    $result = null;
                }

                if ($result !== null) {
                    try {
                        $mailer->sendActivation($result['user'], $result['token']);
                        $this->addFlash(
                            'success',
                            $translator->trans(
                                'registration.activation_sent',
                                [],
                                'registration',
                                $request->getLocale(),
                            ),
                        );
                    } catch (ActivationMailException) {
                        $this->addFlash(
                            'error',
                            $translator->trans(
                                'registration.activation_delivery_failed',
                                [],
                                'registration',
                                $request->getLocale(),
                            ),
                        );
                    }

                    return $this->redirectToRoute('app_registration_pending');
                }
            }
        }

        return $this->render('auth/register.html.twig', [
            'errors' => $errors,
        ]);
    }

    #[Route('/registration/pending', name: 'app_registration_pending', methods: ['GET'])]
    public function pending(): Response
    {
        return $this->render('auth/registration_pending.html.twig');
    }

    #[Route('/activation/resend', name: 'app_registration_resend', methods: ['POST'])]
    public function resend(
        Request $request,
        RegistrationService $registration,
        RegistrationMailer $mailer,
        TranslatorInterface $translator,
    ): Response {
        if (!$this->isCsrfTokenValid('resend_activation', (string) $request->request->get('_token'))) {
            throw $this->createAccessDeniedException();
        }

        $email = mb_strtolower(trim((string) $request->request->get('email')));

        if (filter_var($email, FILTER_VALIDATE_EMAIL)) {
            $result = $registration->renewActivationForEmail($email);

            if ($result !== null) {
                try {
                    $mailer->sendActivation($result['user'], $result['token']);
                } catch (ActivationMailException) {
                    $this->addFlash(
                        'error',
                        $translator->trans(
                            'registration.activation_delivery_failed',
                            [],
                            'registration',
                            $request->getLocale(),
                        ),
                    );

                    return $this->redirectToRoute('app_registration_pending');
                }
            }
        }

        $this->addFlash(
            'success',
            $translator->trans(
                'registration.resend_generic',
                [],
                'registration',
                $request->getLocale(),
            ),
        );

        return $this->redirectToRoute('app_registration_pending');
    }

    #[Route(
        '/activate/{token}',
        name: 'app_registration_activate',
        requirements: ['token' => '[a-f0-9]{64}'],
        methods: ['GET'],
    )]
    public function activate(
        string $token,
        RegistrationService $registration,
        TranslatorInterface $translator,
        Request $request,
    ): Response {
        $user = $registration->activate($token);

        if ($user === null) {
            $this->addFlash(
                'error',
                $translator->trans(
                    'registration.activation_invalid',
                    [],
                    'registration',
                    $request->getLocale(),
                ),
            );

            return $this->redirectToRoute('app_registration_pending');
        }

        $this->addFlash(
            'success',
            $translator->trans(
                'registration.activated',
                [],
                'registration',
                $user->getLocale(),
            ),
        );

        return $this->redirectToRoute('app_login');
    }
}
