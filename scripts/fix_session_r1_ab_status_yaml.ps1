param([string]$Root = (Get-Location).Path)
$ErrorActionPreference = 'Stop'

function ReadUtf8([string]$p) {
    [IO.File]::ReadAllText($p, [Text.UTF8Encoding]::new($false))
}
function WriteUtf8([string]$p,[string]$s) {
    [IO.File]::WriteAllText($p,$s,[Text.UTF8Encoding]::new($false))
}

function EnsureStatusValidated([string]$Text, [string]$Value) {
    $lines = $Text -split "`r?`n"
    $statusStart = -1
    $statusEnd = $lines.Length

    for($i=0; $i -lt $lines.Length; $i++) {
        if($lines[$i] -match '^  status:\s*$') {
            $statusStart = $i
            break
        }
    }
    if($statusStart -lt 0) { throw "Bloc YAML 'status:' introuvable" }

    for($i=$statusStart+1; $i -lt $lines.Length; $i++) {
        if($lines[$i] -match '^  [A-Za-z0-9_]+:\s*' -and $lines[$i] -notmatch '^    ') {
            $statusEnd = $i
            break
        }
    }

    for($i=$statusStart+1; $i -lt $statusEnd; $i++) {
        if($lines[$i] -match '^    validated:\s*') {
            $lines[$i] = "    validated: $Value"
            return ($lines -join "`n")
        }
    }

    for($i=$statusStart+1; $i -lt $statusEnd; $i++) {
        if($lines[$i] -match '^    draft:\s*') {
            $before = @()
            if($i -ge 0) { $before = $lines[0..$i] }
            $after = @()
            if($i + 1 -le $lines.Length - 1) { $after = $lines[($i+1)..($lines.Length-1)] }
            return (($before + "    validated: $Value" + $after) -join "`n")
        }
    }

    throw "Clé 'draft' introuvable dans le bloc status"
}

$fr = Join-Path $Root 'translations\event.fr.yaml'
$en = Join-Path $Root 'translations\event.en.yaml'
foreach($p in @($fr,$en)) {
    if(-not (Test-Path $p)) { throw "SESSION_R1_AB_HOTFIX4 fichier absent: $p" }
}

$s = EnsureStatusValidated (ReadUtf8 $fr) 'Validée'
WriteUtf8 $fr $s

$s = EnsureStatusValidated (ReadUtf8 $en) 'Validated'
WriteUtf8 $en $s

Write-Host 'SESSION_R1_AB_HOTFIX4_OK'
