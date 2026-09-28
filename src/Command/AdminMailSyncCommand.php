<?php

declare(strict_types=1);

namespace App\Command;

use App\Service\AdminRecipientResolver;
use Symfony\Component\Console\Attribute\AsCommand;
use Symfony\Component\Console\Command\Command;
use Symfony\Component\Console\Input\InputInterface;
use Symfony\Component\Console\Output\OutputInterface;
use Symfony\Component\DependencyInjection\Attribute\Autowire;

#[AsCommand(name: 'ezscore:admin-mail-sync', description: 'Synchronise les destinataires admin/error vers le compte admin first-run.')]
final class AdminMailSyncCommand extends Command
{
    public function __construct(
        private readonly AdminRecipientResolver $adminRecipient,
        #[Autowire('%kernel.project_dir%')] private readonly string $projectDir,
    ) { parent::__construct(); }

    protected function execute(InputInterface $input, OutputInterface $output): int
    {
        $admin = $this->adminRecipient->resolve();
        $email = trim($admin->getEmail());
        if (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
            $output->writeln('<error>Adresse admin invalide.</error>');
            return Command::FAILURE;
        }
        $path = $this->projectDir.'/.env.local';
        $text = is_file($path) ? (string) file_get_contents($path) : '';
        $keys = [
            'EZSCORE_ADMIN_CONTACT_EMAIL','EZSCORE_ADMIN_EMAIL','EZSCORE_ERROR_EMAIL','EZSCORE_ERROR_RECIPIENT',
            'ADMIN_EMAIL','ADMIN_RECIPIENT','ERROR_EMAIL','ERROR_RECIPIENT','ERROR_REPORT_EMAIL','ERROR_REPORT_RECIPIENT',
        ];
        foreach ($keys as $key) {
            $line = $key.'='.$email;
            $pattern = '/^'.preg_quote($key, '/').'=.*$/m';
            if (preg_match($pattern, $text) === 1) {
                $text = (string) preg_replace($pattern, $line, $text);
            } elseif (in_array($key, ['EZSCORE_ADMIN_CONTACT_EMAIL','EZSCORE_ADMIN_EMAIL','EZSCORE_ERROR_RECIPIENT'], true)) {
                $text = rtrim($text).PHP_EOL.$line.PHP_EOL;
            }
        }
        file_put_contents($path, $text);
        $output->writeln('<info>ADMIN_MAIL_SYNC_OK</info>');
        $output->writeln('Admin first-run: '.$admin->getDisplayName().' <'.$email.'>');
        return Command::SUCCESS;
    }
}
