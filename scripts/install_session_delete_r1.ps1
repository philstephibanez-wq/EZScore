param([string]$Root = (Get-Location).Path)
$ErrorActionPreference = 'Stop'

function ReadUtf8([string]$Path) {
    [IO.File]::ReadAllText($Path, [Text.UTF8Encoding]::new($false))
}
function WriteUtf8([string]$Path,[string]$Text) {
    [IO.File]::WriteAllText($Path,$Text,[Text.UTF8Encoding]::new($false))
}

$tpl = Join-Path $Root 'templates\events\show.html.twig'
if(-not (Test-Path $tpl)) { throw "SESSION_DELETE_R1 fichier absent: $tpl" }

$text = ReadUtf8 $tpl

$old = @'
{% if is_granted('EVENT_MANAGE', event) %}
<form method="post" action="{{ path('app_event_delete', {'_locale': app.request.locale, id: event.id}) }}" onsubmit="return confirm('{{ 'event.delete_confirm'|trans({}, 'event')|e('js') }}');">
  <input type="hidden" name="_token" value="{{ csrf_token('event_delete_' ~ event.id) }}">
  <button type="submit">{{ 'event.delete'|trans({}, 'event') }}</button>
</form>
{% endif %}
'@

$new = @'
{% if is_granted('EVENT_MANAGE', event) %}
<div class="session-delete-actions">
  <button type="button" class="session-delete-danger" data-session-delete-open>
    {{ 'event.delete'|trans({}, 'event') }}
  </button>
</div>

<dialog class="session-delete-dialog" data-session-delete-dialog>
  <div class="session-delete-dialog__body">
    <h2>{{ 'event.delete'|trans({}, 'event') }}</h2>
    <p>{{ 'event.delete_confirm'|trans({}, 'event') }}</p>
    <div class="session-delete-dialog__buttons">
      <button type="button" data-session-delete-cancel>{{ 'event.delete_cancel'|trans({}, 'event') }}</button>
      <form method="post" action="{{ path('app_event_delete', {'_locale': app.request.locale, id: event.id}) }}">
        <input type="hidden" name="_token" value="{{ csrf_token('event_delete_' ~ event.id) }}">
        <button class="primary session-delete-danger" type="submit">{{ 'event.delete_confirm_button'|trans({}, 'event') }}</button>
      </form>
    </div>
  </div>
</dialog>
{% endif %}
'@

if($text.Contains($old)) {
    $text = $text.Replace($old,$new)
} elseif(-not $text.Contains('data-session-delete-dialog')) {
    throw "SESSION_DELETE_R1 bloc suppression inattendu"
}

# Add CSS in stylesheets block if missing.
$cssLine = '<link rel="stylesheet" href="/assets/css/events/session-delete-confirm-r1.css?v=20261002r1">'
if(-not $text.Contains($cssLine)) {
    $anchor = '<link rel="stylesheet" href="/assets/css/collection-filters.css?v=20260925r20">'
    if(-not $text.Contains($anchor)) { throw "SESSION_DELETE_R1 ancre CSS introuvable" }
    $text = $text.Replace($anchor, $anchor + "`n" + $cssLine)
}

# Extend javascripts block if missing.
$jsLine = '<script src="/assets/js/events/session-delete-confirm-r1.js?v=20261002r1"></script>'
if(-not $text.Contains($jsLine)) {
    $oldJs = '{% block javascripts %}<script src="/assets/js/entity-picker.js?v=20260925r20"></script>{% endblock %}'
    $newJs = '{% block javascripts %}<script src="/assets/js/entity-picker.js?v=20260925r20"></script><script src="/assets/js/events/session-delete-confirm-r1.js?v=20261002r1"></script>{% endblock %}'
    if(-not $text.Contains($oldJs)) { throw "SESSION_DELETE_R1 bloc JS inattendu" }
    $text = $text.Replace($oldJs,$newJs)
}

WriteUtf8 $tpl $text

# Translations, ASCII-only payload to avoid PowerShell 5 encoding issues.
$fr = Join-Path $Root 'translations\event.fr.yaml'
$en = Join-Path $Root 'translations\event.en.yaml'

foreach($p in @($fr,$en)) {
    if(-not (Test-Path $p)) { throw "SESSION_DELETE_R1 traduction absente: $p" }
}

$frText = ReadUtf8 $fr
if(-not $frText.Contains('  delete_cancel:')) {
    $frText = $frText.Replace(
        '  delete_confirm: Supprimer définitivement cette session ?',
        "  delete_confirm: Supprimer définitivement cette session ?`n  delete_cancel: Annuler`n  delete_confirm_button: Supprimer définitivement"
    )
    WriteUtf8 $fr $frText
}

$enText = ReadUtf8 $en
if(-not $enText.Contains('  delete_cancel:')) {
    $enText = $enText.Replace(
        '  delete_confirm: Permanently delete this session?',
        "  delete_confirm: Permanently delete this session?`n  delete_cancel: Cancel`n  delete_confirm_button: Delete permanently"
    )
    WriteUtf8 $en $enText
}

foreach($required in @(
    (Join-Path $Root 'public\assets\js\events\session-delete-confirm-r1.js'),
    (Join-Path $Root 'public\assets\css\events\session-delete-confirm-r1.css'),
    (Join-Path $Root 'tests\session_delete_r1_contract.php')
)) {
    if(-not (Test-Path $required)) { throw "SESSION_DELETE_R1 fichier de livraison absent: $required" }
}

Write-Host 'SESSION_DELETE_R1_INSTALL_OK'
