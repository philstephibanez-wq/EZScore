<?php
declare(strict_types=1);
$root = $argv[1] ?? 'H:\\EZScore_v1';
function fail_contract(string $message): never { fwrite(STDERR, $message.PHP_EOL); exit(1); }
$client = @file_get_contents($root.'/src/Service/LyricsOvhClient.php');
$controller = @file_get_contents($root.'/src/Controller/LyricsOvhController.php');
$js = @file_get_contents($root.'/public/assets/js/lyrics-ovh-r38-16.js');
$template = @file_get_contents($root.'/templates/song/lyricslab.html.twig');
if ($client === false || $controller === false || $js === false || $template === false) fail_contract('Missing Lyrics.ovh files');
foreach (['public function suggestFast(', "self::BASE_URL.'/suggest/'"] as $needle) if (strpos($client,$needle)===false) fail_contract('Missing fast client contract: '.$needle);
if (strpos($controller,'app_song_lyrics_ovh_autocomplete')===false || strpos($controller,'suggestFast($query, 6)')===false) fail_contract('Autocomplete route/service missing');
foreach (['data-autocomplete-url=', 'lyrics-ovh-r38-16.js?v=20260929r38_16i'] as $needle) if (strpos($template,$needle)===false) fail_contract('Template contract missing: '.$needle);
foreach (['const autocompleteUrl =','const autocompleteCache = new Map()','fetch(autocompleteUrl','setTimeout(autocompleteSearch, 140)','autocompleteCache.has(cacheKey)'] as $needle) if (strpos($js,$needle)===false) fail_contract('Fast autocomplete JS missing: '.$needle);
$autoStart = strpos($js,'async function autocompleteSearch()');
$autoEnd = strpos($js,'function scheduleAutocomplete()', $autoStart);
$autoBlock = substr($js,$autoStart,$autoEnd-$autoStart);
if (strpos($autoBlock,'fetch(searchUrl') !== false) fail_contract('Autocomplete still calls heavy verified search endpoint');
echo "R38_16I_FAST_AUTOCOMPLETE_CONTRACT_OK".PHP_EOL;
