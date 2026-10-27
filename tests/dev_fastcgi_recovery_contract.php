<?php
declare(strict_types=1);
$s=file_get_contents(dirname(__DIR__).'/scripts/dev-fastcgi.ps1');
foreach(['backend.lock','DEV_FASTCGI_RECOVERY_REQUIRES_CONFIRMATION','DEV_FASTCGI_RECOVERY_METADATA_EXISTS','DEV_FASTCGI_RECOVERY_IDENTITY_MISMATCH','DEV_FASTCGI_RECOVERY_PID_CHANGED','DEV_FASTCGI_RECOVERED','STARTED_PID=','LISTENER_PID=','DEV_FASTCGI_STOP_REFUSED'] as $needle){
 if(!str_contains($s,$needle))throw new RuntimeException('missing '.$needle);
}
$a=strpos($s,"if(\$Action -eq 'recover')");
$b=strpos($s,"if(\$Action -eq 'status')");
if($a===false||$b===false||$b<=$a)throw new RuntimeException('recovery boundary');
$part=substr($s,$a,$b-$a);
if(str_contains($part,'Stop-Process')||str_contains($part,'Start-Process'))throw new RuntimeException('recover must not start/stop');
if(preg_match('/\\$pid\\b/i',$s))throw new RuntimeException('reserved PID');
echo "EZScore_DEV_FASTCGI_RECOVERY_CONTRACT_OK\n";
