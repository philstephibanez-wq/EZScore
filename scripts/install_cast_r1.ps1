param(
    [string]$RepoRoot = "H:\EZScore"
)

$ErrorActionPreference = "Stop"

$base = Join-Path $RepoRoot "templates\base.html.twig"
if (-not (Test-Path $base)) {
    throw "Fichier introuvable: $base"
}

$content = Get-Content -LiteralPath $base -Raw -Encoding UTF8

$cssTag = '    <link rel="stylesheet" href="/assets/css/cast/ezscore-cast.css?v=20261002r1">'
$coreTag = '<script src="/assets/js/cast/ezscore-cast.js?v=20261002r1"></script>'
$nativeTag = '<script src="/assets/js/cast/ezscore-cast-native-bridge.js?v=20261002r1"></script>'
$uiTag = '<script src="/assets/js/cast/ezscore-cast-ui.js?v=20261002r1"></script>'

if ($content -notmatch [regex]::Escape('/assets/css/cast/ezscore-cast.css')) {
    $needle = '    {% block stylesheets %}{% endblock %}'
    if (-not $content.Contains($needle)) {
        throw "Point d'insertion CSS introuvable dans templates/base.html.twig"
    }
    $content = $content.Replace($needle, "$needle`r`n$cssTag")
}

if ($content -notmatch [regex]::Escape('/assets/js/cast/ezscore-cast.js')) {
    $needle = '<script src="/assets/js/app.js?v=20260924f"></script>'
    if (-not $content.Contains($needle)) {
        throw "Point d'insertion JS introuvable dans templates/base.html.twig"
    }
    $insert = @(
        $coreTag,
        $nativeTag,
        $uiTag,
        $needle
    ) -join "`r`n"
    $content = $content.Replace($needle, $insert)
}

[System.IO.File]::WriteAllText($base, $content, (New-Object System.Text.UTF8Encoding($false)))

Write-Host "CAST_R1_INSTALL_OK"
