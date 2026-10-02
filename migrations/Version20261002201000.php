<?php
declare(strict_types=1);

namespace DoctrineMigrations;

use Doctrine\DBAL\Schema\Schema;
use Doctrine\Migrations\AbstractMigration;

final class Version20261002201000 extends AbstractMigration
{
    public function getDescription(): string
    {
        return 'Session contract: remove obsolete event mode from Session';
    }

    public function up(Schema $schema): void
    {
        $this->addSql('ALTER TABLE events DROP COLUMN mode');
    }

    public function down(Schema $schema): void
    {
        $this->addSql("ALTER TABLE events ADD COLUMN mode VARCHAR(16) NOT NULL DEFAULT 'onsite'");
    }
}
