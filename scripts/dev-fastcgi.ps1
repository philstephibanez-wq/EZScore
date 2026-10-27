param([Parameter(Mandatory=$true)][ValidateSet('start','stop','status')][string]$Action)
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$Runtime = Join-Path $Root 'var\runtime\dev-fastcgi'
$Meta = Join-Path $Runtime 'backend.json'
$Lock = Join-Path $Runtime 'backend.lock'
$Exe = 'H:\PHP\php-8.5-x64\php-cgi.exe'
$Port = 8602
New-Item -ItemType Directory -Force -Path $Runtime | Out-Null
$mutex = [IO.File]::Open($Lock,[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
try {
 function Listener { $x=Get-NetTCPConnection -State Listen -LocalAddress '127.0.0.1' -LocalPort $Port -ErrorAction SilentlyContinue | Select-Object -First 1; if($x){return [int]$x.OwningProcess}; return 0 }
 function Identity([int]$Candidate) {
  if($Candidate -le 0){return $false}
  $p=Get-CimInstance Win32_Process -Filter "ProcessId = $Candidate" -ErrorAction SilentlyContinue
  if(!$p){return $false}
  if(![string]::Equals([string]$p.ExecutablePath,$Exe,[StringComparison]::OrdinalIgnoreCase)){return $false}
  $c=[string]$p.CommandLine
  return ($c -eq ('"'+$Exe+'" -b 127.0.0.1:8602') -or $c -eq ($Exe+' -b 127.0.0.1:8602'))
 }
 $state=$null
 if(Test-Path -LiteralPath $Meta){try{$state=Get-Content -LiteralPath $Meta -Raw -Encoding UTF8 | ConvertFrom-Json}catch{throw 'DEV_FASTCGI_METADATA_INVALID'}}
 $pid=if($state){[int]$state.pid}else{0}
 $actual=Listener
 $owned=($pid -gt 0 -and $actual -eq $pid -and (Identity $pid))
 if($Action -eq 'status'){
  if($owned){Write-Host "DEV_FASTCGI_OWNED PID=$pid";return}
  if($actual){Write-Host "DEV_FASTCGI_UNOWNED LISTENER_PID=$actual";return}
  if($state){Write-Host 'DEV_FASTCGI_STALE_METADATA';return}
  Write-Host 'DEV_FASTCGI_STOPPED';return
 }
 if($Action -eq 'stop'){
  if($actual -and -not $owned){throw "DEV_FASTCGI_STOP_REFUSED PID=$actual"}
  if($pid -gt 0 -and -not $owned -and (Get-Process -Id $pid -ErrorAction SilentlyContinue)){throw "DEV_FASTCGI_PID_REUSED=$pid"}
  if($owned){Stop-Process -Id $pid -Force -ErrorAction Stop}
  for($i=0;$i -lt 40;$i++){if(!(Listener)){break};Start-Sleep -Milliseconds 250}
  if(Listener){throw 'DEV_FASTCGI_STILL_LISTENING_METADATA_PRESERVED'}
  if(Test-Path -LiteralPath $Meta){Remove-Item -LiteralPath $Meta -Force}
  Write-Host 'DEV_FASTCGI_STOPPED';return
 }
 if($owned){Write-Host "DEV_FASTCGI_ALREADY_RUNNING PID=$pid";return}
 if($actual -or $state){throw 'DEV_FASTCGI_START_REFUSED_UNOWNED_OR_STALE'}
 foreach($f in @($Exe,(Join-Path $Root 'public\index.php'),(Join-Path $Root 'vendor\autoload_runtime.php'))){if(!(Test-Path -LiteralPath $f -PathType Leaf)){throw "DEV_FASTCGI_MISSING $f"}}
 $env:APP_ENV='dev';$env:APP_DEBUG='1';$env:EZSCORE_INSTANCE='dev'
 $p=Start-Process -FilePath $Exe -ArgumentList @('-b','127.0.0.1:8602') -WorkingDirectory $Root -WindowStyle Hidden -PassThru
 try {
  $ready=$false
  for($i=0;$i -lt 40;$i++){Start-Sleep -Milliseconds 250;if((Listener) -eq $p.Id -and (Identity $p.Id)){$ready=$true;break};if($p.HasExited){break}}
  if(!$ready){throw 'DEV_FASTCGI_START_FAILED_OR_DIFFERENT_LISTENER'}
  $json=@{schema='ezscore.dev-fastcgi.v1';pid=$p.Id;started_utc=[DateTime]::UtcNow.ToString('o')} | ConvertTo-Json
  [IO.File]::WriteAllText($Meta,$json+"`n",[Text.UTF8Encoding]::new($false))
  Write-Host "DEV_FASTCGI_STARTED PID=$($p.Id) PORT=8602"
 } catch {if(Identity $p.Id){Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue};throw}
} finally {$mutex.Dispose()}
