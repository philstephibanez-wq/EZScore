<?php
$root=$argv[1] ?? 'H:\\EZScore_v1';

$catalog=file_get_contents($root.'/templates/catalog/index.html.twig');
if(strpos($catalog,'data-public-contact-form')!==false){
  fwrite(STDERR,"Public contact form still embedded in catalogue\n");
  exit(1);
}

$base=file_get_contents($root.'/templates/base.html.twig');
foreach(["R38.14a public contact header","Contacter LogAndPlay","app_public_contact"] as $needle){
  if(strpos($base,$needle)===false){
    fwrite(STDERR,"Missing header invariant: $needle\n");
    exit(1);
  }
}

$controller=file_get_contents($root.'/src/Controller/ContactController.php');
foreach(["methods: ['GET', 'POST']","render('contact/public.html.twig')"] as $needle){
  if(strpos($controller,$needle)===false){
    fwrite(STDERR,"Missing controller invariant: $needle\n");
    exit(1);
  }
}

$template=$root.'/templates/contact/public.html.twig';
if(!is_file($template) || strpos(file_get_contents($template),'data-public-contact-form')===false){
  fwrite(STDERR,"Dedicated public contact template missing\n");
  exit(1);
}

echo "R38_14A_CONTACT_HEADER_CONTRACT_OK\n";
