<?php

declare(strict_types=1);

namespace App\Command;

use App\Service\AdminRecipientResolver;
use Symfony\Component\Console\Attribute\AsCommand;
use Symfony\Component\Console\Command\Command;
use Symfony\Component\Console\Input\InputInterface;
use Symfony\Component\Console\Output\OutputInterface;
use Symfony\Component\DependencyInjection\Attribute\Autowire;

#[AsCommand(name: 'ezscore:admin-mail-audit', description: 'Audite les adresses admin/error des fichiers env sans afficher de secrets.')]
final class AdminMailAuditCommand extends Command
{
    public function __construct(
        private readonly AdminRecipientResolver $adminRecipient,
        #[Autowire('%kernel.project_dir%')] private readonly string $projectDir,
    ) { parent::__construct(); }

    protected function execute(InputInterface $input, OutputInterface $output): int
    {
        $admin = $this->adminRecipient->resolve();
        $expected = strtolower(trim($admin->getEmail()));
        $output->writeln('Admin attendu: '.$admin->getDisplayName().' <'.$admin->getEmail().'>');
        $mismatches = 0;
        foreach (['.env','.env.local','.env.dev','.env.prod','.env.test'] as $file) {
            $path = $this->projectDir.'/'.$file;
            if (!is_file($path)) continue;
            foreach (file($path, FILE_IGNORE_NEW_LINES) ?: [] as $line) {
                $line = trim($line);
                if ($line === '' || str_starts_with($line, '#') || !str_contains($line, '=')) continue;
                [$key,$value] = array_map('trim', explode('=', $line, 2));
                if (!preg_match('/(?:ADMIN|ERROR|MAIL|EMAIL|RECIPIENT)/i', $key)) continue;
                if (preg_match('/(?:DSN|PASSWORD|PASS|SECRET|TOKEN|KEY)/i', $key)) {
                    $output->writeln($file.' '.$key.'=<masqué>');
                    continue;
                }
                $clean = trim($value, "\"'");
                if (filter_var($clean, FILTER_VALIDATE_EMAIL)) {
                    $status = strtolower($clean) === $expected ? 'OK' : 'DIFF';
                    if ($status === 'DIFF') ++$mismatches;
                    $output->writeln(sprintf('%s %s=%s [%s]', $file, $key, $clean, $status));
                }
            }
        }
        if ($mismatches > 0) {
            $output->writeln('<error>ADMIN_MAIL_AUDIT_DIFF='.$mismatches.'</error>');
            return Command::FAILURE;
        }
        $output->writeln('<info>ADMIN_MAIL_AUDIT_OK</info>');
        return Command::SUCCESS;
    }
}
