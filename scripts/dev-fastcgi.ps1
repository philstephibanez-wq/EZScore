param([Parameter(Mandatory=$true)][ValidateSet('start','stop','status','recover','diagnose')][string]$Action,[int]$ExpectedPid=0,[switch]$ConfirmRecovery)
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
  $normalized = $c.Trim()
  $pattern = '^(?:"' + [regex]::Escape($Exe) + '"|' + [regex]::Escape($Exe) + ')\\s+-b\\s+127\\.0\\.0\\.1:8602
 }
 $state=$null
 if(Test-Path -LiteralPath $Meta){try{$state=Get-Content -LiteralPath $Meta -Raw -Encoding UTF8 | ConvertFrom-Json}catch{throw 'DEV_FASTCGI_METADATA_INVALID'}}
 $storedPid=if($state){[int]$state.pid}else{0}
 $actual=Listener
 $owned=($storedPid -gt 0 -and $actual -eq $storedPid -and (Identity $storedPid))
 if($Action -eq 'diagnose'){
  $connections=@(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
  Write-Host "DEV_FASTCGI_DIAG_LISTENER_COUNT=$($connections.Count)"
  foreach($connection in $connections){
   $candidate=[int]$connection.OwningProcess
   $proc=Get-CimInstance Win32_Process -Filter "ProcessId = $candidate" -ErrorAction SilentlyContinue
   $exeMatches=($null -ne $proc -and [string]::Equals([string]$proc.ExecutablePath,$Exe,[StringComparison]::OrdinalIgnoreCase))
   $cmd=[string]$proc.CommandLine
   $expectedQuoted='"'+$Exe+'" -b 127.0.0.1:8602'
   $expectedPlain=$Exe+' -b 127.0.0.1:8602'
   $commandMatches=(Identity $candidate) -and $exeMatches
   $matched=(Identity $candidate)
   Write-Host "DEV_FASTCGI_DIAG PID=$candidate ADDRESS=$($connection.LocalAddress) EXE_MATCH=$exeMatches CMD_MATCH=$commandMatches IDENTITY=$matched"
   if(-not $exeMatches){Write-Host "DEV_FASTCGI_DIAG_EXECUTABLE=$([string]$proc.ExecutablePath)"}
   if(-not $commandMatches){Write-Host "DEV_FASTCGI_DIAG_COMMAND=$cmd"}
  }
  Write-Host "DEV_FASTCGI_DIAG_FILTERED_LISTENER=$actual"
  Write-Host "DEV_FASTCGI_DIAG_STORED_PID=$storedPid"
  return
 }
 if($Action -eq 'recover'){
  if(-not $ConfirmRecovery -or $ExpectedPid -le 0){throw 'DEV_FASTCGI_RECOVERY_REQUIRES_CONFIRMATION'}
  if($state){throw 'DEV_FASTCGI_RECOVERY_METADATA_EXISTS'}
  if($actual -ne $ExpectedPid -or -not (Identity $ExpectedPid)){throw 'DEV_FASTCGI_RECOVERY_IDENTITY_MISMATCH'}
  $again=Listener
  if($again -ne $ExpectedPid -or -not (Identity $ExpectedPid)){throw 'DEV_FASTCGI_RECOVERY_PID_CHANGED'}
  $json=@{schema='ezscore.dev-fastcgi.v1';pid=$ExpectedPid;recovery_mode='operator_explicit_pid';recovered_utc=[DateTime]::UtcNow.ToString('o')}|ConvertTo-Json
  [IO.File]::WriteAllText($Meta,$json+"`n",[Text.UTF8Encoding]::new($false))
  Write-Host "DEV_FASTCGI_RECOVERED PID=$ExpectedPid";return
 }
 if($Action -eq 'status'){
  if($owned){Write-Host "DEV_FASTCGI_OWNED PID=$storedPid";return}
  if($actual){Write-Host "DEV_FASTCGI_UNOWNED LISTENER_PID=$actual";return}
  if($state){Write-Host 'DEV_FASTCGI_STALE_METADATA';return}
  Write-Host 'DEV_FASTCGI_STOPPED';return
 }
 if($Action -eq 'stop'){
  if($actual -and -not $owned){throw "DEV_FASTCGI_STOP_REFUSED PID=$actual"}
  if($storedPid -gt 0 -and -not $owned -and (Get-Process -Id $storedPid -ErrorAction SilentlyContinue)){throw "DEV_FASTCGI_PID_REUSED=$storedPid"}
  if($owned){Stop-Process -Id $storedPid -Force -ErrorAction Stop}
  for($i=0;$i -lt 40;$i++){if(!(Listener)){break};Start-Sleep -Milliseconds 250}
  if(Listener){throw 'DEV_FASTCGI_STILL_LISTENING_METADATA_PRESERVED'}
  if(Test-Path -LiteralPath $Meta){Remove-Item -LiteralPath $Meta -Force}
  Write-Host 'DEV_FASTCGI_STOPPED';return
 }
 if($owned){Write-Host "DEV_FASTCGI_ALREADY_RUNNING PID=$storedPid";return}
 if($actual -or $state){throw 'DEV_FASTCGI_START_REFUSED_UNOWNED_OR_STALE'}
 foreach($f in @($Exe,(Join-Path $Root 'public\index.php'),(Join-Path $Root 'vendor\autoload_runtime.php'))){if(!(Test-Path -LiteralPath $f -PathType Leaf)){throw "DEV_FASTCGI_MISSING $f"}}
 $env:APP_ENV='dev';$env:APP_DEBUG='1';$env:EZSCORE_INSTANCE='dev'
 $p=Start-Process -FilePath $Exe -ArgumentList @('-b','127.0.0.1:8602') -WorkingDirectory $Root -WindowStyle Hidden -PassThru
 try {
  $ready=$false
  for($i=0;$i -lt 40;$i++){Start-Sleep -Milliseconds 250;if((Listener) -eq $p.Id -and (Identity $p.Id)){$ready=$true;break};if($p.HasExited){break}}
  if(!$ready){
   $unexpected=Listener
   $observed=if($unexpected){Get-CimInstance Win32_Process -Filter "ProcessId = $unexpected" -ErrorAction SilentlyContinue}else{$null}
   $started=Get-CimInstance Win32_Process -Filter "ProcessId = $($p.Id)" -ErrorAction SilentlyContinue
   $detail=if($observed){"LISTENER_PID=$unexpected PARENT_PID=$($observed.ParentProcessId) EXECUTABLE=$($observed.ExecutablePath) COMMAND=$($observed.CommandLine)"}else{'LISTENER_PID=0'}
   throw "DEV_FASTCGI_START_FAILED_OR_DIFFERENT_LISTENER STARTED_PID=$($p.Id) STARTED_ALIVE=$([bool]$started) $detail"
  }
  $json=@{schema='ezscore.dev-fastcgi.v1';pid=$p.Id;started_utc=[DateTime]::UtcNow.ToString('o')} | ConvertTo-Json
  [IO.File]::WriteAllText($Meta,$json+"`n",[Text.UTF8Encoding]::new($false))
  Write-Host "DEV_FASTCGI_STARTED PID=$($p.Id) PORT=8602"
 } catch {if(Identity $p.Id){Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue};throw}
} finally {$mutex.Dispose()}

  return [regex]::IsMatch($normalized,$pattern,[System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
 }
 $state=$null
 if(Test-Path -LiteralPath $Meta){try{$state=Get-Content -LiteralPath $Meta -Raw -Encoding UTF8 | ConvertFrom-Json}catch{throw 'DEV_FASTCGI_METADATA_INVALID'}}
 $storedPid=if($state){[int]$state.pid}else{0}
 $actual=Listener
 $owned=($storedPid -gt 0 -and $actual -eq $storedPid -and (Identity $storedPid))
 if($Action -eq 'diagnose'){
  $connections=@(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
  Write-Host "DEV_FASTCGI_DIAG_LISTENER_COUNT=$($connections.Count)"
  foreach($connection in $connections){
   $candidate=[int]$connection.OwningProcess
   $proc=Get-CimInstance Win32_Process -Filter "ProcessId = $candidate" -ErrorAction SilentlyContinue
   $exeMatches=($null -ne $proc -and [string]::Equals([string]$proc.ExecutablePath,$Exe,[StringComparison]::OrdinalIgnoreCase))
   $cmd=[string]$proc.CommandLine
   $expectedQuoted='"'+$Exe+'" -b 127.0.0.1:8602'
   $expectedPlain=$Exe+' -b 127.0.0.1:8602'
   $commandMatches=($cmd -ceq $expectedQuoted -or $cmd -ceq $expectedPlain)
   $matched=(Identity $candidate)
   Write-Host "DEV_FASTCGI_DIAG PID=$candidate ADDRESS=$($connection.LocalAddress) EXE_MATCH=$exeMatches CMD_MATCH=$commandMatches IDENTITY=$matched"
   if(-not $exeMatches){Write-Host "DEV_FASTCGI_DIAG_EXECUTABLE=$([string]$proc.ExecutablePath)"}
   if(-not $commandMatches){Write-Host "DEV_FASTCGI_DIAG_COMMAND=$cmd"}
  }
  Write-Host "DEV_FASTCGI_DIAG_FILTERED_LISTENER=$actual"
  Write-Host "DEV_FASTCGI_DIAG_STORED_PID=$storedPid"
  return
 }
 if($Action -eq 'recover'){
  if(-not $ConfirmRecovery -or $ExpectedPid -le 0){throw 'DEV_FASTCGI_RECOVERY_REQUIRES_CONFIRMATION'}
  if($state){throw 'DEV_FASTCGI_RECOVERY_METADATA_EXISTS'}
  if($actual -ne $ExpectedPid -or -not (Identity $ExpectedPid)){throw 'DEV_FASTCGI_RECOVERY_IDENTITY_MISMATCH'}
  $again=Listener
  if($again -ne $ExpectedPid -or -not (Identity $ExpectedPid)){throw 'DEV_FASTCGI_RECOVERY_PID_CHANGED'}
  $json=@{schema='ezscore.dev-fastcgi.v1';pid=$ExpectedPid;recovery_mode='operator_explicit_pid';recovered_utc=[DateTime]::UtcNow.ToString('o')}|ConvertTo-Json
  [IO.File]::WriteAllText($Meta,$json+"`n",[Text.UTF8Encoding]::new($false))
  Write-Host "DEV_FASTCGI_RECOVERED PID=$ExpectedPid";return
 }
 if($Action -eq 'status'){
  if($owned){Write-Host "DEV_FASTCGI_OWNED PID=$storedPid";return}
  if($actual){Write-Host "DEV_FASTCGI_UNOWNED LISTENER_PID=$actual";return}
  if($state){Write-Host 'DEV_FASTCGI_STALE_METADATA';return}
  Write-Host 'DEV_FASTCGI_STOPPED';return
 }
 if($Action -eq 'stop'){
  if($actual -and -not $owned){throw "DEV_FASTCGI_STOP_REFUSED PID=$actual"}
  if($storedPid -gt 0 -and -not $owned -and (Get-Process -Id $storedPid -ErrorAction SilentlyContinue)){throw "DEV_FASTCGI_PID_REUSED=$storedPid"}
  if($owned){Stop-Process -Id $storedPid -Force -ErrorAction Stop}
  for($i=0;$i -lt 40;$i++){if(!(Listener)){break};Start-Sleep -Milliseconds 250}
  if(Listener){throw 'DEV_FASTCGI_STILL_LISTENING_METADATA_PRESERVED'}
  if(Test-Path -LiteralPath $Meta){Remove-Item -LiteralPath $Meta -Force}
  Write-Host 'DEV_FASTCGI_STOPPED';return
 }
 if($owned){Write-Host "DEV_FASTCGI_ALREADY_RUNNING PID=$storedPid";return}
 if($actual -or $state){throw 'DEV_FASTCGI_START_REFUSED_UNOWNED_OR_STALE'}
 foreach($f in @($Exe,(Join-Path $Root 'public\index.php'),(Join-Path $Root 'vendor\autoload_runtime.php'))){if(!(Test-Path -LiteralPath $f -PathType Leaf)){throw "DEV_FASTCGI_MISSING $f"}}
 $env:APP_ENV='dev';$env:APP_DEBUG='1';$env:EZSCORE_INSTANCE='dev'
 $p=Start-Process -FilePath $Exe -ArgumentList @('-b','127.0.0.1:8602') -WorkingDirectory $Root -WindowStyle Hidden -PassThru
 try {
  $ready=$false
  for($i=0;$i -lt 40;$i++){Start-Sleep -Milliseconds 250;if((Listener) -eq $p.Id -and (Identity $p.Id)){$ready=$true;break};if($p.HasExited){break}}
  if(!$ready){
   $unexpected=Listener
   $observed=if($unexpected){Get-CimInstance Win32_Process -Filter "ProcessId = $unexpected" -ErrorAction SilentlyContinue}else{$null}
   $started=Get-CimInstance Win32_Process -Filter "ProcessId = $($p.Id)" -ErrorAction SilentlyContinue
   $detail=if($observed){"LISTENER_PID=$unexpected PARENT_PID=$($observed.ParentProcessId) EXECUTABLE=$($observed.ExecutablePath) COMMAND=$($observed.CommandLine)"}else{'LISTENER_PID=0'}
   throw "DEV_FASTCGI_START_FAILED_OR_DIFFERENT_LISTENER STARTED_PID=$($p.Id) STARTED_ALIVE=$([bool]$started) $detail"
  }
  $json=@{schema='ezscore.dev-fastcgi.v1';pid=$p.Id;started_utc=[DateTime]::UtcNow.ToString('o')} | ConvertTo-Json
  [IO.File]::WriteAllText($Meta,$json+"`n",[Text.UTF8Encoding]::new($false))
  Write-Host "DEV_FASTCGI_STARTED PID=$($p.Id) PORT=8602"
 } catch {if(Identity $p.Id){Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue};throw}
} finally {$mutex.Dispose()}
