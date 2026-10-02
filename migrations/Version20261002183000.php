<?php
declare(strict_types=1);

namespace DoctrineMigrations;

use Doctrine\DBAL\Schema\Schema;
use Doctrine\Migrations\AbstractMigration;

final class Version20261002183000 extends AbstractMigration
{
    public function getDescription(): string
    {
        return 'Session R1: remove obsolete remote_url from events';
    }

    public function up(Schema $schema): void
    {
        $this->addSql('ALTER TABLE events DROP COLUMN remote_url');
    }

    public function down(Schema $schema): void
    {
        $this->addSql('ALTER TABLE events ADD COLUMN remote_url VARCHAR(800) DEFAULT NULL');
    }
}
