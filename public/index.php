<?php

declare(strict_types=1);

use App\Kernel;

/*
 * EZSCORE_R41_0H_ONLINE_PROD_GUARD
 *
 * Invariant d'infrastructure:
 *   EZSCORE_INSTANCE=online => APP_ENV=prod + APP_DEBUG=0
 *
 * Cette garde est exécutée avant Symfony Runtime.
 */
$ezscoreInstance = (string) ($_SERVER['EZSCORE_INSTANCE'] ?? $_ENV['EZSCORE_INSTANCE'] ?? getenv('EZSCORE_INSTANCE') ?: '');
if ($ezscoreInstance === 'online') {
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
