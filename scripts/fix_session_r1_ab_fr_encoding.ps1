param([string]$Root = (Get-Location).Path)
$ErrorActionPreference = 'Stop'

$path = Join-Path $Root 'translations\event.fr.yaml'
if(-not (Test-Path $path)) {
    throw "SESSION_R1_AB_HOTFIX5 fichier absent: $path"
}

$utf8 = [System.Text.UTF8Encoding]::new($false)
$text = [System.IO.File]::ReadAllText($path, $utf8)

$replacements = [ordered]@{
    'ValidÃ©e' = 'Validée'
    'validÃ©e' = 'validée'
    'Ã©' = 'é'
    'Ã¨' = 'è'
    'Ã ' = 'à'
    'Ã´' = 'ô'
    'Ãª' = 'ê'
    'Ã§' = 'ç'
}

foreach($pair in $replacements.GetEnumerator()) {
    $text = $text.Replace([string]$pair.Key, [string]$pair.Value)
}

[System.IO.File]::WriteAllText($path, $text, $utf8)

Write-Host 'SESSION_R1_AB_HOTFIX5_OK'
