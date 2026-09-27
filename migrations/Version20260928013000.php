<?php

declare(strict_types=1);
namespace DoctrineMigrations;
use Doctrine\DBAL\Schema\Schema;
use Doctrine\Migrations\AbstractMigration;
final class Version20260928013000 extends AbstractMigration
{
    public function getDescription(): string { return 'Persist ChordsLab crowd/applause filter per song'; }
    public function up(Schema $schema): void { $this->addSql('ALTER TABLE songs ADD COLUMN chord_noise_filter_enabled BOOLEAN NOT NULL DEFAULT 0'); }
    public function down(Schema $schema): void { $this->addSql('ALTER TABLE songs DROP COLUMN chord_noise_filter_enabled'); }
}
