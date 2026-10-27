<?php
declare(strict_types=1);
$root=dirname(__DIR__);
$version=trim(file_get_contents($root.'/VERSION'));
$agents=file_get_contents($root.'/AGENTS.md');
if (!str_contains($agents,'[vVERSION]') || !str_contains($agents,'Le préfixe littéral `[v]` est interdit')) {
    throw new RuntimeException('Convention des commits absente');
}
if (!preg_match('/^1\\.0i$/',$version)) throw new RuntimeException('VERSION inattendue');
echo "EZScore_VERSIONED_COMMIT_PREFIX_CONTRACT_OK\n";
