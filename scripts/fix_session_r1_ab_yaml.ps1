param([string]$Root = (Get-Location).Path)
$ErrorActionPreference = 'Stop'

function ReadUtf8([string]$p) {
    [IO.File]::ReadAllText($p, [Text.UTF8Encoding]::new($false))
}
function WriteUtf8([string]$p,[string]$s) {
    [IO.File]::WriteAllText($p,$s,[Text.UTF8Encoding]::new($false))
}

function DeduplicateYamlKey([string]$Text, [string]$Key) {
    $lines = $Text -split "`r?`n"
    $seen = $false
    $out = New-Object System.Collections.Generic.List[string]
    foreach($line in $lines) {
        if($line -match "^\s+$([regex]::Escape($Key))\s*:") {
            if($seen) { continue }
            $seen = $true
        }
        $out.Add($line)
    }
    return ($out -join "`n")
}

$files = @(
    (Join-Path $Root 'translations\event.fr.yaml'),
    (Join-Path $Root 'translations\event.en.yaml')
)

foreach($p in $files) {
    if(-not (Test-Path $p)) { throw "SESSION_R1_AB_HOTFIX3 fichier absent: $p" }
    $s = ReadUtf8 $p
    foreach($key in @(
        'required_group_playlist',
        'validated',
        'validate_title',
        'validate_note',
        'validate_button'
    )) {
        $s = DeduplicateYamlKey $s $key
    }
    WriteUtf8 $p $s
}

Write-Host 'SESSION_R1_AB_HOTFIX3_OK'
