<?php
declare(strict_types=1);

namespace DoctrineMigrations;

use Doctrine\DBAL\Schema\Schema;
use Doctrine\Migrations\AbstractMigration;

final class Version20261002223000 extends AbstractMigration
{
    public function getDescription(): string
    {
        return 'R1.C6 Karaoke LiveRun transport state';
    }

    public function up(Schema $schema): void
    {
        $columns = array_map(
            static fn(mixed $name): string => strtolower((string) $name),
            $this->connection->fetchFirstColumn("SELECT name FROM pragma_table_info('live_runs')")
        );

        $add = function (string $column, string $sql) use (&$columns): void {
            if (!in_array(strtolower($column), $columns, true)) {
                $this->addSql($sql);
                $columns[] = strtolower($column);
            }
        };

        $add('current_song_id', "ALTER TABLE live_runs ADD COLUMN current_song_id INTEGER DEFAULT NULL");
        $add('playing', "ALTER TABLE live_runs ADD COLUMN playing BOOLEAN NOT NULL DEFAULT 0");
        $add('position_ms', "ALTER TABLE live_runs ADD COLUMN position_ms INTEGER NOT NULL DEFAULT 0");
        $add('playback_rate', "ALTER TABLE live_runs ADD COLUMN playback_rate DOUBLE PRECISION NOT NULL DEFAULT 1");
        $add('state_updated_at', "ALTER TABLE live_runs ADD COLUMN state_updated_at DATETIME DEFAULT NULL");
    }

    public function down(Schema $schema): void
    {
        // SQLite compatibility: intentionally no destructive rollback for POC transport columns.
    }
}
