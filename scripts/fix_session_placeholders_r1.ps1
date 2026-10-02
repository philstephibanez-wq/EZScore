param([string]$Root = (Get-Location).Path)
$ErrorActionPreference = 'Stop'

$path = Join-Path $Root 'templates\events\index.html.twig'
if(-not (Test-Path $path)) { throw "SESSION_PLACEHOLDER_R1 fichier absent: $path" }

$utf8 = [System.Text.UTF8Encoding]::new($false)
$text = [System.IO.File]::ReadAllText($path, $utf8)

# Avoid any non-ASCII placeholder in source: canonical HTML entity.
$text = [regex]::Replace(
    $text,
    '<option value="">[^<]*</option>',
    '<option value="">&mdash;</option>'
)

[System.IO.File]::WriteAllText($path, $text, $utf8)

Write-Host 'SESSION_PLACEHOLDER_R1_INSTALL_OK'
