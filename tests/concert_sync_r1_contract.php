<?php

declare(strict_types=1);
$root = dirname(__DIR__);
$required = [
    'src/Service/ConcertSessionStore.php','src/Controller/ConcertSessionController.php','templates/concert/control.html.twig','templates/concert/follow.html.twig','public/assets/js/concert/concert-master-r1.js','public/assets/js/concert/concert-follower-r1.js','public/assets/css/concert-sync-r1.css','scripts/install_concert_sync_r1.ps1',
];
foreach ($required as $relative) {
    if (!is_file($root . '/' . $relative)) { fwrite(STDERR,"MISSING: {$relative}\n"); exit(1); }
}
$routes=file_get_contents($root.'/config/routes.yaml');
$base=file_get_contents($root.'/templates/base.html.twig');
$store=file_get_contents($root.'/src/Service/ConcertSessionStore.php');
$controller=file_get_contents($root.'/src/Controller/ConcertSessionController.php');
$masterJs=file_get_contents($root.'/public/assets/js/concert/concert-master-r1.js');
$followerJs=file_get_contents($root.'/public/assets/js/concert/concert-follower-r1.js');
$checks=[
'route import'=>str_contains($routes,'concert_session_controller:')&&str_contains($routes,'../src/Controller/ConcertSessionController.php'),
'header session link'=>str_contains($base,'class="ez-concert-link"')&&str_contains($base,"path('app_concert_control')"),
'cast r1 remains loaded'=>str_contains($base,'/assets/js/cast/ezscore-cast.js?v=20261002r1')&&str_contains($base,'/assets/js/cast/ezscore-cast-native-bridge.js?v=20261002r1')&&str_contains($base,'/assets/js/cast/ezscore-cast-ui.js?v=20261002r1'),
'ephemeral store'=>str_contains($store,"/var/concert_sessions")&&str_contains($store,'TTL_SECONDS = 14400')&&str_contains($store,'flock('),
'unpredictable secrets'=>substr_count($store,'random_bytes(')>=4&&str_contains($store,"hash('sha256', \$masterKey)")&&str_contains($store,"hash('sha256', \$inviteToken)")&&str_contains($store,"hash('sha256', \$clientKey)"),
'single master write authority'=>str_contains($store,"'master_user_id'")&&str_contains($store,'INVALID_MASTER_KEY')&&str_contains($controller,'X-Concert-Master-Key'),
'master server auth'=>substr_count($controller,"denyAccessUnlessGranted('ROLE_USER')")>=4&&str_contains($controller,"isCsrfTokenValid('concert_session'"),
'follower read only role'=>str_contains($store,"'role' => 'follower_local'")&&str_contains($store,"'transport' => false"),
'session sync endpoints'=>str_contains($controller,"'/api/concert/session'")&&str_contains($controller,"'/api/concert/session/{sessionId}/join'")&&str_contains($controller,"'/api/concert/session/{sessionId}/client-state'")&&str_contains($controller,"'/api/concert/session/{sessionId}/heartbeat'"),
'follower interpolation'=>str_contains($followerJs,'requestAnimationFrame(renderClock)')&&str_contains($followerJs,'performance.now()')&&str_contains($followerJs,'state.playing'),
'master test clock'=>str_contains($masterJs,'currentPositionMs')&&str_contains($masterJs,'X-Concert-Master-Key'),
'no obsolete projector dependency'=>!str_contains($controller,'/projector/')&&!str_contains($store,'Projector'),
'no audio engine coupling'=>!str_contains($controller,'AudioEngine')&&!str_contains($store,'AudioEngine')&&!str_contains($masterJs,'EZScoreAudioEngine')&&!str_contains($followerJs,'EZScoreAudioEngine'),
];
foreach($checks as $label=>$ok){if(!$ok){fwrite(STDERR,"FAILED: {$label}\n");exit(1);}}
echo "CONCERT_SYNC_R1_CONTRACT_OK\n";


