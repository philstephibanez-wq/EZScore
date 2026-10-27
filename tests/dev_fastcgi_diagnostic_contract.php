<?php
declare(strict_types=1);
$s=file_get_contents(dirname(__DIR__).'/scripts/dev-fastcgi.ps1');
foreach(["'diagnose'",'DEV_FASTCGI_DIAG_LISTENER_COUNT','DEV_FASTCGI_DIAG_FILTERED_LISTENER','EXE_MATCH=','CMD_MATCH=','IDENTITY='] as $needle) {
    if(!str_contains($s,$needle)) throw new RuntimeException('Missing '.$needle);
}
$start=strpos($s,"if(\$Action -eq 'diagnose')");
$end=strpos($s,"if(\$Action -eq 'recover')");
if($start===false||$end===false||$start>=$end) throw new RuntimeException('Branch order');
$part=substr($s,$start,$end-$start);
foreach(['Stop-Process','Start-Process','WriteAllText','Remove-Item'] as $forbidden) {
    if(str_contains($part,$forbidden)) throw new RuntimeException('diagnostic mutates: '.$forbidden);
}
echo "EZScore_DEV_FASTCGI_DIAG_READONLY_CONTRACT_OK\n";
