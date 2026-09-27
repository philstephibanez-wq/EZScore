<?php
declare(strict_types=1);
namespace DoctrineMigrations;
use Doctrine\DBAL\Schema\Schema; use Doctrine\Migrations\AbstractMigration;
final class Version20260927093000 extends AbstractMigration{
 public function getDescription():string{return 'R35.4 collaborators and contact messages';}
 public function up(Schema $schema):void{
  $this->addSql("CREATE TABLE song_collaborators (id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, song_id INTEGER NOT NULL, user_id INTEGER NOT NULL, granted_by INTEGER NOT NULL, created_at DATETIME NOT NULL, CONSTRAINT FK_COLLAB_SONG FOREIGN KEY (song_id) REFERENCES songs (id) ON DELETE CASCADE, CONSTRAINT FK_COLLAB_USER FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE, CONSTRAINT FK_COLLAB_GRANTED FOREIGN KEY (granted_by) REFERENCES users (id) ON DELETE RESTRICT)");
  $this->addSql("CREATE UNIQUE INDEX uniq_song_collaborator ON song_collaborators (song_id,user_id)");
  $this->addSql("CREATE TABLE contact_messages (id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, user_id INTEGER NOT NULL, song_id INTEGER DEFAULT NULL, category VARCHAR(40) NOT NULL, subject VARCHAR(180) NOT NULL, message CLOB NOT NULL, status VARCHAR(20) NOT NULL, created_at DATETIME NOT NULL, CONSTRAINT FK_CONTACT_USER FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE, CONSTRAINT FK_CONTACT_SONG FOREIGN KEY (song_id) REFERENCES songs (id) ON DELETE SET NULL)");
  $this->addSql("CREATE INDEX IDX_CONTACT_USER_CREATED ON contact_messages (user_id,created_at)");
 }
 public function down(Schema $schema):void{$this->addSql('DROP TABLE contact_messages');$this->addSql('DROP TABLE song_collaborators');}
}
