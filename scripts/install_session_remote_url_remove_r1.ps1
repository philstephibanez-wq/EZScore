param([string]$Root = (Get-Location).Path)
$ErrorActionPreference = 'Stop'

function ReadUtf8([string]$Path) {
    [IO.File]::ReadAllText($Path, [Text.UTF8Encoding]::new($false))
}
function WriteUtf8([string]$Path,[string]$Text) {
    [IO.File]::WriteAllText($Path,$Text,[Text.UTF8Encoding]::new($false))
}

$event = Join-Path $Root 'src\Domain\Event\Event.php'
$ctrl = Join-Path $Root 'src\Controller\EventController.php'
$index = Join-Path $Root 'templates\events\index.html.twig'
$show = Join-Path $Root 'templates\events\show.html.twig'
$fr = Join-Path $Root 'translations\event.fr.yaml'
$en = Join-Path $Root 'translations\event.en.yaml'

foreach($p in @($event,$ctrl,$index,$show,$fr,$en)) {
    if(-not (Test-Path $p)) { throw "SESSION_REMOTE_URL_REMOVE_R1 fichier absent: $p" }
}

# Domain Event: remove property + getter/setter.
$s = ReadUtf8 $event
$s = [regex]::Replace($s, '(?ms)\s*#\[ORM\\Column\(length: 800, nullable: true\)\]\s*private \?string \$remoteUrl = null;\s*', "`n")
$s = [regex]::Replace($s, '(?m)^\s*public function getRemoteUrl\(\): \?string \{ return \$this->remoteUrl; \}\r?\n', '')
$s = [regex]::Replace($s, '(?m)^\s*public function setRemoteUrl\(\?string \$url\): self \{ \$this->remoteUrl = \$url !== null \? trim\(\$url\) : null; return \$this->touch\(\); \}\r?\n', '')
WriteUtf8 $event $s

# Controller: remove request/model handling.
$s = ReadUtf8 $ctrl
$s = [regex]::Replace($s, '(?m)^\s*->setRemoteUrl\(\(string\) \$request->request->get\(''remote_url''\)\)\r?\n', '')
WriteUtf8 $ctrl $s

# Index template: remove creation input.
$s = ReadUtf8 $index
$s = [regex]::Replace($s, '(?m)^\s*<label>\{\{ ''event\.fields\.remote_url''\|trans\(\{\}, ''event''\) \}\}<input type="url" name="remote_url"></label>\r?\n', '')
WriteUtf8 $index $s

# Show template: remove summary + edit input.
$s = ReadUtf8 $show
$s = [regex]::Replace($s, '(?m)^\s*<div><span>\{\{ ''event\.fields\.remote_url''\|trans\(\{\}, ''event''\) \}\}</span>\{% if event\.remoteUrl %\}.*?</div>\r?\n', '')
$s = [regex]::Replace($s, '(?m)^\s*<label>\{\{ ''event\.fields\.remote_url''\|trans\(\{\}, ''event''\) \}\}<input type="url" name="remote_url" value="\{\{ event\.remoteUrl \}\}"></label>\r?\n', '')
WriteUtf8 $show $s

# Translations: remove key only.
foreach($p in @($fr,$en)) {
    $s = ReadUtf8 $p
    $s = [regex]::Replace($s, '(?m)^\s{4}remote_url:.*\r?\n', '')
    WriteUtf8 $p $s
}

foreach($required in @(
    (Join-Path $Root 'migrations\Version20261002183000.php'),
    (Join-Path $Root 'tests\session_remote_url_remove_r1_contract.php'),
    (Join-Path $Root 'docs\SESSION_REMOTE_URL_REMOVAL_R1.md')
)) {
    if(-not (Test-Path $required)) { throw "SESSION_REMOTE_URL_REMOVE_R1 fichier de livraison absent: $required" }
}

Write-Host 'SESSION_REMOTE_URL_REMOVE_R1_INSTALL_OK'
