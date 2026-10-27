<?php
declare(strict_types=1);
$s=file_get_contents(dirname(__DIR__).'/scripts/dev-fastcgi.ps1');
if(!str_contains($s,'$normalized = $c.Trim()')) throw new RuntimeException('Trim missing');
if(!str_contains($s,'[regex]::Escape($Exe)')) throw new RuntimeException('Executable escape missing');
if(!str_contains($s,'127\\.0\\.0\\.1:8602$')) throw new RuntimeException('Missing anchored address');
if(!str_contains($s,'RegexOptions]::IgnoreCase')) throw new RuntimeException('Regex options missing');
if(!str_contains($s,'$commandMatches=(Identity $candidate) -and $exeMatches')) throw new RuntimeException('Divergent identity diagnostic');
echo "EZScore_DEV_FASTCGI_COMMAND_MATCH_CONTRACT_OK\n";
