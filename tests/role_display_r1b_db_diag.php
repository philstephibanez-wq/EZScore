<?php
declare(strict_types=1);

require dirname(__DIR__).'/vendor/autoload.php';

use App\Kernel;

$kernel = new Kernel('dev', true);
$kernel->boot();

$em = $kernel->getContainer()->get('doctrine')->getManager();
$conn = $em->getConnection();

$rows = $conn->fetchAllAssociative(
    "SELECT id, display_name, email, roles FROM users ORDER BY LOWER(display_name)"
);

echo "=== USERS / ROLES DB ===\n";
foreach ($rows as $row) {
    printf("%s | %s | %s | %s\n", $row['id'], $row['display_name'], $row['email'], $row['roles']);
}
