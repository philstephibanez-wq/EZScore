<?php
declare(strict_types=1);

require dirname(__DIR__).'/vendor/autoload.php';

use App\Domain\User\User;
use App\Service\UserManager;

$u = new User();
$u->setRoles(['ROLE_DISPLAY']);

$errors = [];

if ($u->getPrimaryRole() !== 'ROLE_DISPLAY') {
    $errors[] = 'getPrimaryRole='.$u->getPrimaryRole();
}
if (!in_array('ROLE_DISPLAY', $u->getRoles(), true)) {
    $errors[] = 'ROLE_DISPLAY missing from getRoles';
}
if (!in_array('ROLE_DISPLAY', UserManager::ROLES, true)) {
    $errors[] = 'ROLE_DISPLAY missing from UserManager::ROLES';
}

$rc = new ReflectionClass(User::class);
$prop = $rc->getProperty('roles');
$prop->setAccessible(true);
$raw = $prop->getValue($u);
if ($raw !== ['ROLE_DISPLAY']) {
    $errors[] = 'raw roles='.json_encode($raw);
}

if ($errors !== []) {
    fwrite(STDERR, "ROLE_DISPLAY_R1B_STRICT_FAIL\n".implode("\n", $errors)."\n");
    exit(1);
}

echo "ROLE_DISPLAY_R1B_STRICT_CONTRACT_OK\n";
