<?php
declare(strict_types=1);

namespace DoctrineMigrations;

use Doctrine\DBAL\Schema\Schema;
use Doctrine\Migrations\AbstractMigration;

final class Version20260929090000 extends AbstractMigration
{
    public function getDescription(): string
    {
        return 'R38.15 unlimited full-block lyrics source history';
    }

    public function up(Schema $schema): void
    {
        $this->addSql("CREATE TABLE lyrics_source_revisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            song_id INTEGER NOT NULL,
            created_by_user_id INTEGER DEFAULT NULL,
            content CLOB NOT NULL,
            source_type VARCHAR(32) NOT NULL,
            comment VARCHAR(1000) DEFAULT NULL,
            created_at DATETIME NOT NULL,
            CONSTRAINT FK_LYRICS_REVISION_SONG FOREIGN KEY (song_id) REFERENCES songs (id) ON DELETE CASCADE,
            CONSTRAINT FK_LYRICS_REVISION_USER FOREIGN KEY (created_by_user_id) REFERENCES users (id) ON DELETE SET NULL
        )");
        $this->addSql('CREATE INDEX IDX_LYRICS_REVISION_SONG_CREATED ON lyrics_source_revisions (song_id, created_at)');
        $this->addSql('CREATE INDEX IDX_LYRICS_REVISION_USER ON lyrics_source_revisions (created_by_user_id)');

        // Preserve every pre-existing source block as the first historical snapshot.
        $this->addSql("
            INSERT INTO lyrics_source_revisions
                (song_id, created_by_user_id, content, source_type, comment, created_at)
            SELECT
                id, editor_id, lyrics_source_text, 'legacy',
                'Version existante avant activation de l''historique.',
                CURRENT_TIMESTAMP
            FROM songs
            WHERE lyrics_source_text IS NOT NULL AND TRIM(lyrics_source_text) <> ''
        ");
    }

    public function down(Schema $schema): void
    {
        $this->addSql('DROP TABLE lyrics_source_revisions');
    }
}
