<?php

declare(strict_types=1);

use App\Kernel;

/*
 * EZSCORE_R41_0I_PROD_INSTANCE_GUARD
 *
 * Invariant d'infrastructure:
 *   EZSCORE_INSTANCE in {online, prod} => APP_ENV=prod + APP_DEBUG=0
 *
 * "online" est conservé pour compatibilité legacy.
 * "prod" est la cible physique utilisée par EZS_orchestrator R3.
 *
 * Cette garde est exécutée avant Symfony Runtime.
 */
$ezscoreInstance = (string) ($_SERVER['EZSCORE_INSTANCE'] ?? $_ENV['EZSCORE_INSTANCE'] ?? getenv('EZSCORE_INSTANCE') ?: '');

// Normalize the physical instance marker into PHP superglobals so Symfony/Twig
// can reliably distinguish DEV from PROD independently of APP_ENV.
if ($ezscoreInstance !== '') {
    $_SERVER['EZSCORE_INSTANCE'] = $ezscoreInstance;
    $_ENV['EZSCORE_INSTANCE'] = $ezscoreInstance;
}

if (in_array($ezscoreInstance, ['online', 'prod'], true)) {
    putenv('APP_ENV=prod');
    putenv('APP_DEBUG=0');
    $_SERVER['APP_ENV'] = 'prod';
    $_SERVER['APP_DEBUG'] = '0';
    $_ENV['APP_ENV'] = 'prod';
    $_ENV['APP_DEBUG'] = '0';
}

require_once dirname(__DIR__).'/vendor/autoload_runtime.php';

return static function (array $context): Kernel {
    return new Kernel($context['APP_ENV'], (bool) $context['APP_DEBUG']);
};
