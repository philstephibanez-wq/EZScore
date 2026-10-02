<?php
declare(strict_types=1);

namespace DoctrineMigrations;

use Doctrine\DBAL\Schema\Schema;
use Doctrine\Migrations\AbstractMigration;

final class Version20261002194500 extends AbstractMigration
{
    public function getDescription(): string
    {
        return 'R1.C1 persistent LiveRun test foundation';
    }

    public function up(Schema $schema): void
    {
        $this->addSql("CREATE TABLE live_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            event_id INTEGER NOT NULL,
            conductor_user_id INTEGER NOT NULL,
            status VARCHAR(16) NOT NULL,
            test_mode BOOLEAN NOT NULL DEFAULT 1,
            revision INTEGER NOT NULL DEFAULT 0,
            started_at DATETIME NOT NULL,
            ended_at DATETIME DEFAULT NULL,
            CONSTRAINT FK_LIVE_RUN_EVENT FOREIGN KEY (event_id) REFERENCES events (id) ON DELETE CASCADE,
            CONSTRAINT FK_LIVE_RUN_CONDUCTOR FOREIGN KEY (conductor_user_id) REFERENCES users (id) ON DELETE CASCADE
        )");
        $this->addSql('CREATE INDEX IDX_LIVE_RUN_EVENT_STATUS ON live_runs (event_id, status)');
        $this->addSql('CREATE INDEX IDX_LIVE_RUN_CONDUCTOR ON live_runs (conductor_user_id)');
    }

    public function down(Schema $schema): void
    {
        $this->addSql('DROP TABLE live_runs');
    }
}
