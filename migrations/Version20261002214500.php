<?php
declare(strict_types=1);

namespace DoctrineMigrations;

use Doctrine\DBAL\Schema\Schema;
use Doctrine\Migrations\AbstractMigration;

final class Version20261002214500 extends AbstractMigration
{
    public function getDescription(): string
    {
        return 'R1.C3 LiveRun canonical transport state';
    }

    public function up(Schema $schema): void
    {
        $this->addSql('ALTER TABLE live_runs ADD COLUMN current_song_id INTEGER DEFAULT NULL');
        $this->addSql('ALTER TABLE live_runs ADD COLUMN playing BOOLEAN NOT NULL DEFAULT 0');
        $this->addSql('ALTER TABLE live_runs ADD COLUMN position_ms INTEGER NOT NULL DEFAULT 0');
        $this->addSql('ALTER TABLE live_runs ADD COLUMN playback_rate DOUBLE PRECISION NOT NULL DEFAULT 1');
        $this->addSql('ALTER TABLE live_runs ADD COLUMN state_updated_at DATETIME DEFAULT NULL');
    }

    public function down(Schema $schema): void
    {
        $this->addSql('ALTER TABLE live_runs DROP COLUMN current_song_id');
        $this->addSql('ALTER TABLE live_runs DROP COLUMN playing');
        $this->addSql('ALTER TABLE live_runs DROP COLUMN position_ms');
        $this->addSql('ALTER TABLE live_runs DROP COLUMN playback_rate');
        $this->addSql('ALTER TABLE live_runs DROP COLUMN state_updated_at');
    }
}
