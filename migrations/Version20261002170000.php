<?php
declare(strict_types=1);

namespace DoctrineMigrations;

use Doctrine\DBAL\Schema\Schema;
use Doctrine\Migrations\AbstractMigration;

final class Version20261002170000 extends AbstractMigration
{
    public function getDescription(): string
    {
        return 'Session R1.A/B: add validated_at';
    }

    public function up(Schema $schema): void
    {
        $this->addSql('ALTER TABLE events ADD COLUMN validated_at DATETIME DEFAULT NULL');
    }

    public function down(Schema $schema): void
    {
        $this->abortIf(true, 'Version20261002170000 is intentionally irreversible.');
    }
}
