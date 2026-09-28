<?php
$root=$argv[1] ?? 'H:\\EZScore_v1';
$checks=[
 ['config/packages/security.yaml','R38.14b public contact'],
 ['src/Controller/ContactController.php','TurnstileVerifier $turnstile'],
 ['src/Controller/ContactController.php','PublicContactRateLimiter $rateLimiter'],
 ['src/Controller/ContactController.php','cf-turnstile-response'],
 ['src/Controller/ContactController.php','$rateLimiter->consume($clientIp, $email)'],
 ['templates/contact/public.html.twig','challenges.cloudflare.com/turnstile/v0/api.js'],
 ['templates/contact/public.html.twig','class="cf-turnstile"'],
 ['src/Service/TurnstileVerifier.php','turnstile/v0/siteverify'],
 ['src/Service/PublicContactRateLimiter.php',"$globalKey = 'global'"],
];
foreach($checks as [$file,$needle]){
  $src=file_get_contents($root.'/'.$file);
  if(strpos($src,$needle)===false){fwrite(STDERR,"Missing $needle in $file\n");exit(1);}
}
$google=file_get_contents($root.'/src/Security/GoogleAuthenticator.php');
if(strpos($google,'if ($user === null)')===false || strpos($google,'auth.account.google_not_registered')===false){
  fwrite(STDERR,"Google unknown-user refusal invariant missing\n"); exit(1);
}
if(strpos($google,'new User(')!==false){
  fwrite(STDERR,"Forbidden Google auto-registration detected\n"); exit(1);
}
echo "R38_14B_SECURE_PUBLIC_CONTACT_CONTRACT_OK\n";
