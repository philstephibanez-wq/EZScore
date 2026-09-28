<?php
declare(strict_types=1);
namespace DoctrineMigrations;
use Doctrine\DBAL\Schema\Schema;
use Doctrine\Migrations\AbstractMigration;
final class Version20260928030000 extends AbstractMigration
{
    public function getDescription(): string{return 'LyricsLab editable source text';}
    public function up(Schema $schema): void{$this->addSql('ALTER TABLE songs ADD COLUMN lyrics_source_text CLOB DEFAULT NULL');}
    public function down(Schema $schema): void{$this->addSql('ALTER TABLE songs DROP COLUMN lyrics_source_text');}
}
