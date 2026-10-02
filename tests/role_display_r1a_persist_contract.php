<?php
declare(strict_types=1);

require dirname(__DIR__).'/vendor/autoload.php';

use App\Domain\User\User;
use App\Service\UserManager;

$u = new User();
$u->setRoles(['ROLE_DISPLAY']);

if ($u->getPrimaryRole() !== 'ROLE_DISPLAY') {
    fwrite(STDERR, "ROLE_DISPLAY_R1A failed: primary role=".$u->getPrimaryRole()."\n");
    exit(1);
}

if (!in_array('ROLE_DISPLAY', $u->getRoles(), true)) {
    fwrite(STDERR, "ROLE_DISPLAY_R1A failed: ROLE_DISPLAY filtered out by User::setRoles()\n");
    exit(1);
}

if (!in_array('ROLE_DISPLAY', UserManager::ROLES, true)) {
    fwrite(STDERR, "ROLE_DISPLAY_R1A failed: UserManager::ROLES rejects ROLE_DISPLAY\n");
    exit(1);
}

$controller = file_get_contents(dirname(__DIR__).'/src/Controller/AdminUserController.php');
if (!str_contains($controller, "['ROLE_READER', 'ROLE_EDITOR', 'ROLE_ADMIN', 'ROLE_DISPLAY']")) {
    fwrite(STDERR, "ROLE_DISPLAY_R1A failed: admin role filter not updated\n");
    exit(1);
}

echo "ROLE_DISPLAY_R1A_PERSIST_CONTRACT_OK\n";
