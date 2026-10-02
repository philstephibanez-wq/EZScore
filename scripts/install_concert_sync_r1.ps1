param([string]$RepoRoot = "H:\EZScore")
$ErrorActionPreference = "Stop"
$routes = Join-Path $RepoRoot "config\routes.yaml"
$base = Join-Path $RepoRoot "templates\base.html.twig"
if (-not (Test-Path $routes)) { throw "Fichier introuvable: $routes" }
if (-not (Test-Path $base)) { throw "Fichier introuvable: $base" }

$routeContent = Get-Content -LiteralPath $routes -Raw -Encoding UTF8
if ($routeContent -notmatch '(?m)^concert_session_controller:\s*$') {
    $routeBlock = @"

concert_session_controller:
    resource: ../src/Controller/ConcertSessionController.php
    type: attribute
"@
    $routeContent = $routeContent.TrimEnd() + "`r`n" + $routeBlock.TrimStart()
    [System.IO.File]::WriteAllText($routes,$routeContent,(New-Object System.Text.UTF8Encoding($false)))
}

$baseContent = Get-Content -LiteralPath $base -Raw -Encoding UTF8
$cssNeedle = '    <link rel="stylesheet" href="/assets/css/cast/ezscore-cast.css?v=20261002r1">'
$cssLine = '    <link rel="stylesheet" href="/assets/css/concert-sync-r1.css?v=20261002r1">'
if ($baseContent -notmatch [regex]::Escape('/assets/css/concert-sync-r1.css?v=20261002r1')) {
    if (-not $baseContent.Contains($cssNeedle)) { throw "Point d'insertion CSS introuvable dans templates/base.html.twig" }
    $baseContent = $baseContent.Replace($cssNeedle,$cssNeedle + "`r`n" + $cssLine)
}

$linkMarkup = @'
            <a class="ez-concert-link"
               href="{{ path('app_concert_control') }}"
               title="Session concert"
               aria-label="Session concert">Session</a>
'@
if ($baseContent -notmatch 'class="ez-concert-link"') {
    $topbarNeedle = '        <div class="ez-topbar-right">'
    if (-not $baseContent.Contains($topbarNeedle)) { throw "Point d'insertion topbar introuvable dans templates/base.html.twig" }
    $baseContent = $baseContent.Replace($topbarNeedle,$topbarNeedle + "`r`n" + $linkMarkup.TrimEnd())
}
[System.IO.File]::WriteAllText($base,$baseContent,(New-Object System.Text.UTF8Encoding($false)))
Write-Host "CONCERT_SYNC_R1_INSTALL_OK"
