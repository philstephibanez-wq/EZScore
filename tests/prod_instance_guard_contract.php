<?php

declare(strict_types=1);

$source = file_get_contents(__DIR__.'/../public/index.php');
if ($source === false) {
    fwrite(STDERR, "Cannot read public/index.php\n");
    exit(2);
}

$required = [
    "EZSCORE_R41_0I_PROD_INSTANCE_GUARD",
    "in_array(\$ezscoreInstance, ['online', 'prod'], true)",
    "putenv('APP_ENV=prod')",
    "putenv('APP_DEBUG=0')",
    "\$_SERVER['APP_ENV'] = 'prod'",
    "\$_SERVER['APP_DEBUG'] = '0'",
    "\$_ENV['APP_ENV'] = 'prod'",
    "\$_ENV['APP_DEBUG'] = '0'",
];

foreach ($required as $needle) {
    if (strpos($source, $needle) === false) {
        fwrite(STDERR, "Missing guard contract: {$needle}\n");
        exit(1);
    }
}

echo "EZSCORE_PROD_INSTANCE_GUARD_OK\n";
