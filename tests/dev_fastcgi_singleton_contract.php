<?php
declare(strict_types=1);
$s=file_get_contents(dirname(__DIR__).'/scripts/dev-fastcgi.ps1');
foreach(['backend.lock','DEV_FASTCGI_START_REFUSED_UNOWNED_OR_STALE','DEV_FASTCGI_STOP_REFUSED','DEV_FASTCGI_STILL_LISTENING_METADATA_PRESERVED','DEV_FASTCGI_ALREADY_RUNNING','EZSCORE_INSTANCE'] as $k){if(!str_contains($s,$k))throw new RuntimeException('missing '.$k);}
if(preg_match('/\\$pid\\b/i',$s))throw new RuntimeException('reserved PowerShell PID variable');
if(str_contains($s,'caddy.exe') || str_contains($s,'8501') || str_contains($s,'php -S'))throw new RuntimeException('bad lifecycle dependency');
echo "EZScore_DEV_FASTCGI_SINGLETON_CONTRACT_OK\n";
