<?php

declare(strict_types=1);

namespace DoctrineMigrations;

use Doctrine\DBAL\Schema\Schema;
use Doctrine\Migrations\AbstractMigration;

final class Version20261003104500 extends AbstractMigration
{
    public function getDescription(): string
    {
        return 'R1.C14B precise LiveRun transport timestamp and projector chord diagram flag';
    }

    public function up(Schema $schema): void
    {
        $this->addSql('ALTER TABLE live_runs ADD COLUMN state_updated_at_ms INTEGER DEFAULT NULL');
        $this->addSql('ALTER TABLE live_runs ADD COLUMN diagram_enabled BOOLEAN NOT NULL DEFAULT 0');
    }

    public function down(Schema $schema): void
    {
        // SQLite column removal is intentionally not automated here.
        $this->abortIf(true, 'R1.C14B down migration is not supported on SQLite.');
    }
}
