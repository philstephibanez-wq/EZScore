param([string]$Root = (Get-Location).Path)
$ErrorActionPreference = 'Stop'

function ReadUtf8([string]$Path) {
    [IO.File]::ReadAllText($Path, [Text.UTF8Encoding]::new($false))
}
function WriteUtf8([string]$Path,[string]$Text) {
    [IO.File]::WriteAllText($Path,$Text,[Text.UTF8Encoding]::new($false))
}

$user = Join-Path $Root 'src\Domain\User\User.php'
$manager = Join-Path $Root 'src\Service\UserManager.php'
$controller = Join-Path $Root 'src\Controller\AdminUserController.php'
$template = Join-Path $Root 'templates\admin\users.html.twig'
$fr = Join-Path $Root 'translations\messages.fr.yaml'
$en = Join-Path $Root 'translations\messages.en.yaml'

foreach($p in @($user,$manager,$controller,$template,$fr,$en)) {
    if(-not (Test-Path $p)) { throw "ROLE_DISPLAY_R1 fichier absent: $p" }
}

$s = ReadUtf8 $user
$s = $s.Replace("$allowed = ['ROLE_ADMIN', 'ROLE_EDITOR', 'ROLE_READER'];", "$allowed = ['ROLE_ADMIN', 'ROLE_EDITOR', 'ROLE_READER', 'ROLE_DISPLAY'];")
$s = $s.Replace("foreach (['ROLE_ADMIN', 'ROLE_EDITOR', 'ROLE_READER'] as $role) {", "foreach (['ROLE_ADMIN', 'ROLE_EDITOR', 'ROLE_READER', 'ROLE_DISPLAY'] as $role) {")
WriteUtf8 $user $s

$s = ReadUtf8 $manager
$s = $s.Replace("public const ROLES = ['ROLE_ADMIN', 'ROLE_EDITOR', 'ROLE_READER'];", "public const ROLES = ['ROLE_ADMIN', 'ROLE_EDITOR', 'ROLE_READER', 'ROLE_DISPLAY'];")
WriteUtf8 $manager $s

$s = ReadUtf8 $controller
$s = $s.Replace("if (in_array($role, ['ROLE_READER', 'ROLE_EDITOR', 'ROLE_ADMIN'], true)) {", "if (in_array($role, ['ROLE_READER', 'ROLE_EDITOR', 'ROLE_ADMIN', 'ROLE_DISPLAY'], true)) {")
WriteUtf8 $controller $s

$s = ReadUtf8 $template
if(-not $s.Contains('value="ROLE_DISPLAY"')) {
    $s = $s.Replace('<option value="ROLE_ADMIN">{{ ''role.ROLE_ADMIN''|trans }}</option></select>', '<option value="ROLE_ADMIN">{{ ''role.ROLE_ADMIN''|trans }}</option><option value="ROLE_DISPLAY">{{ ''role.ROLE_DISPLAY''|trans }}</option></select>')
    $s = $s.Replace("['ROLE_READER','ROLE_EDITOR','ROLE_ADMIN']", "['ROLE_READER','ROLE_EDITOR','ROLE_ADMIN','ROLE_DISPLAY']")
    $s = $s.Replace('<option value="ROLE_ADMIN" {{ user.primaryRole == ''ROLE_ADMIN'' ? ''selected'' : '''' }}>{{ ''role.ROLE_ADMIN''|trans }}</option></select>', '<option value="ROLE_ADMIN" {{ user.primaryRole == ''ROLE_ADMIN'' ? ''selected'' : '''' }}>{{ ''role.ROLE_ADMIN''|trans }}</option><option value="ROLE_DISPLAY" {{ user.primaryRole == ''ROLE_DISPLAY'' ? ''selected'' : '''' }}>{{ ''role.ROLE_DISPLAY''|trans }}</option></select>')
}
WriteUtf8 $template $s

$s = ReadUtf8 $fr
if(-not $s.Contains('  ROLE_DISPLAY:')) {
    $s = $s.Replace("  ROLE_READER: Lecteur", "  ROLE_READER: Lecteur`n  ROLE_DISPLAY: Passif")
}
WriteUtf8 $fr $s

$s = ReadUtf8 $en
if(-not $s.Contains('  ROLE_DISPLAY:')) {
    $s = $s.Replace("  ROLE_READER: Reader", "  ROLE_READER: Reader`n  ROLE_DISPLAY: Passive display")
}
WriteUtf8 $en $s

Write-Host 'ROLE_DISPLAY_R1_INSTALL_OK'
