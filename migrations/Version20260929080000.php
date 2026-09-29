<?php
declare(strict_types=1);

namespace DoctrineMigrations;

use Doctrine\DBAL\Schema\Schema;
use Doctrine\Migrations\AbstractMigration;

final class Version20260929080000 extends AbstractMigration
{
    public function getDescription(): string
    {
        return 'Track the exact current lyrics revision on songs.';
    }

    public function up(Schema $schema): void
    {
        $this->addSql('ALTER TABLE songs ADD COLUMN lyrics_current_revision_id INTEGER DEFAULT NULL');

        $this->addSql(<<<'SQL'
UPDATE songs
SET lyrics_current_revision_id = (
    SELECT revision.id
    FROM lyrics_source_revisions revision
    WHERE revision.song_id = songs.id
      AND revision.content = songs.lyrics_source_text
    ORDER BY revision.created_at DESC, revision.id DESC
    LIMIT 1
)
WHERE lyrics_source_text IS NOT NULL
  AND lyrics_source_text <> ''
SQL);
    }

    public function down(Schema $schema): void
    {
        $this->abortIf(true, 'Down migration intentionally unsupported for SQLite.');
    }
}
