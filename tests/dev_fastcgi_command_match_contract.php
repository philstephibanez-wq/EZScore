<?php
declare(strict_types=1);
$s=file_get_contents(dirname(__DIR__).'/scripts/dev-fastcgi.ps1');
foreach (['$normalized = $c.Trim()','$escapedExe = [regex]::Escape($Exe)','[regex]::IsMatch($normalized,$pattern','RegexOptions]::IgnoreCase','$commandMatches=(Identity $candidate) -and $exeMatches'] as $part) {
 if (!str_contains($s,$part)) throw new RuntimeException('missing '.$part);
}
if (!str_contains($s, '1:8602'.chr(36)."'")) throw new RuntimeException('missing anchored address');
echo "EZScore_DEV_FASTCGI_COMMAND_MATCH_CONTRACT_OK\n";
