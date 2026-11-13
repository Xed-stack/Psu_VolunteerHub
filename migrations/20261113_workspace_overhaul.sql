-- MySQL 8 / MariaDB: run explicitly after a verified backup, before deploying this code.
-- Do not run twice. Existing published activities are backfilled as approved.
CREATE TABLE form_drafts (
 id INTEGER NOT NULL AUTO_INCREMENT PRIMARY KEY,
 user_id INTEGER NOT NULL, campus_id INTEGER NULL, `key` VARCHAR(160) NOT NULL,
 payload JSON NOT NULL, updated_at DATETIME NOT NULL,
 CONSTRAINT uq_form_draft_user_key UNIQUE (user_id, `key`),
 FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
 FOREIGN KEY (campus_id) REFERENCES campuses(id) ON DELETE CASCADE
);
CREATE TABLE partner_agencies (
 id INTEGER NOT NULL AUTO_INCREMENT PRIMARY KEY, campus_id INTEGER NOT NULL,
 name VARCHAR(200) NOT NULL, contact_name VARCHAR(150) NOT NULL,
 email VARCHAR(120), phone VARCHAR(50),
 FOREIGN KEY (campus_id) REFERENCES campuses(id) ON DELETE RESTRICT
);
CREATE TABLE partner_agreements (
 id INTEGER NOT NULL AUTO_INCREMENT PRIMARY KEY, agency_id INTEGER NOT NULL,
 reference VARCHAR(150) NOT NULL, valid_from DATE NOT NULL, valid_until DATE NOT NULL,
 document JSON NOT NULL,
 FOREIGN KEY (agency_id) REFERENCES partner_agencies(id) ON DELETE RESTRICT
);
ALTER TABLE events
 ADD lifecycle_status VARCHAR(16) NOT NULL DEFAULT 'approved',
 ADD cancellation_reason TEXT NULL,
 ADD cancelled_at DATETIME NULL,
 ADD proposal_document JSON NULL,
 ADD conducting_department VARCHAR(150) NULL,
 ADD participant_type VARCHAR(100) NULL,
 ADD audience JSON NULL,
 ADD agreement_id INTEGER NULL,
 ADD CONSTRAINT fk_event_agreement FOREIGN KEY (agreement_id) REFERENCES partner_agreements(id) ON DELETE RESTRICT;
UPDATE events SET audience = JSON_OBJECT() WHERE audience IS NULL;
ALTER TABLE events MODIFY audience JSON NOT NULL;
CREATE TABLE external_groups (
 id INTEGER NOT NULL AUTO_INCREMENT PRIMARY KEY, event_id INTEGER NOT NULL,
 name VARCHAR(150) NOT NULL,
 FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE RESTRICT
);
ALTER TABLE external_participants ADD group_id INTEGER NULL,
 ADD CONSTRAINT fk_external_group FOREIGN KEY (group_id) REFERENCES external_groups(id) ON DELETE SET NULL;
UPDATE users SET role = 'director' WHERE role = 'admin';
ALTER TABLE users MODIFY role ENUM('volunteer','coordinator','director') DEFAULT 'volunteer';
-- Preserve historical roles in audit JSON; no attendance or consent data is rewritten.
