<?php
$root=$argv[1] ?? 'H:\\EZScore_v1';
$checks=[
 ['src/Controller/RegistrationController.php','R38.14 PUBLIC DEVELOPMENT MODE'],
 ['src/Controller/ContactController.php',"name: 'app_public_contact'"],
 ['templates/catalog/index.html.twig','data-public-development-banner'],
 ['templates/catalog/index.html.twig','data-public-contact-form'],
 ['templates/catalog/index.html.twig','Inscriptions prochainement'],
 ['templates/auth/login.html.twig','Inscriptions prochainement'],
 ['templates/base.html.twig','registration-disabled'],
 ['public/assets/css/r38-14-public-development.css','.public-contact-panel'],
];
foreach($checks as [$file,$needle]){
  $src=file_get_contents($root.'/'.$file);
  if(strpos($src,$needle)===false){fwrite(STDERR,"Missing $needle in $file\n");exit(1);}
}
echo "R38_14_PUBLIC_DEV_MODE_CONTRACT_OK\n";
