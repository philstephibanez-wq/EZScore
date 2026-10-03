<?php
declare(strict_types=1);

namespace DoctrineMigrations;

use Doctrine\DBAL\Schema\Schema;
use Doctrine\Migrations\AbstractMigration;

final class Version20261002233000 extends AbstractMigration
{
    public function getDescription(): string
    {
        return 'R1.C7 synchronized Karaoke pre-roll';
    }

    public function up(Schema $schema): void
    {
        $columns = array_map(
            static fn(mixed $name): string => strtolower((string) $name),
            $this->connection->fetchFirstColumn("SELECT name FROM pragma_table_info('live_runs')")
        );

        if (!in_array('countdown_ends_at', $columns, true)) {
            $this->addSql("ALTER TABLE live_runs ADD COLUMN countdown_ends_at DATETIME DEFAULT NULL");
        }
        if (!in_array('countdown_total_seconds', $columns, true)) {
            $this->addSql("ALTER TABLE live_runs ADD COLUMN countdown_total_seconds INTEGER NOT NULL DEFAULT 0");
        }
    }

    public function down(Schema $schema): void
    {
        // POC SQLite: no destructive rollback.
    }
}
