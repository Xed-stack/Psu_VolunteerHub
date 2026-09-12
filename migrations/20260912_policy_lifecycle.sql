-- Additive migration for policy acknowledgement, event consent, targets, and cancellation review.
CREATE TABLE IF NOT EXISTS privacy_revisions (
  id INT AUTO_INCREMENT PRIMARY KEY, title VARCHAR(150) NOT NULL, body TEXT NOT NULL,
  version VARCHAR(30) NOT NULL UNIQUE, is_active BOOLEAN NOT NULL DEFAULT TRUE,
  published_by_id INT NULL, published_at DATETIME NOT NULL,
  CONSTRAINT fk_privacy_publisher FOREIGN KEY (published_by_id) REFERENCES users(id) ON DELETE SET NULL
);
CREATE TABLE IF NOT EXISTS privacy_acknowledgements (
  id INT AUTO_INCREMENT PRIMARY KEY, user_id INT NOT NULL, revision_id INT NOT NULL,
  acknowledged_at DATETIME NOT NULL,
  CONSTRAINT uq_user_privacy_revision UNIQUE (user_id, revision_id),
  CONSTRAINT fk_privacy_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  CONSTRAINT fk_privacy_revision FOREIGN KEY (revision_id) REFERENCES privacy_revisions(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS participation_agreement_revisions (
  id INT AUTO_INCREMENT PRIMARY KEY, title VARCHAR(150) NOT NULL, body TEXT NOT NULL,
  version VARCHAR(30) NOT NULL UNIQUE, is_active BOOLEAN NOT NULL DEFAULT TRUE,
  published_by_id INT NULL, published_at DATETIME NOT NULL,
  CONSTRAINT fk_agreement_publisher FOREIGN KEY (published_by_id) REFERENCES users(id) ON DELETE SET NULL
);
ALTER TABLE events
  ADD COLUMN target_participants INT NULL,
  ADD COLUMN participation_agreement_text TEXT NULL,
  ADD COLUMN participation_agreement_version VARCHAR(30) NULL,
  ADD COLUMN nda_required BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN nda_text TEXT NULL,
  ADD COLUMN nda_version VARCHAR(30) NULL;
ALTER TABLE registrations
  ADD COLUMN policy_accepted_at DATETIME NULL,
  ADD COLUMN policy_version VARCHAR(30) NULL,
  ADD COLUMN nda_accepted_at DATETIME NULL,
  ADD COLUMN nda_version VARCHAR(30) NULL;
CREATE TABLE IF NOT EXISTS cancellation_requests (
  id INT AUTO_INCREMENT PRIMARY KEY, registration_id INT NOT NULL UNIQUE,
  reason VARCHAR(50) NOT NULL, details TEXT NULL,
  status ENUM('pending', 'approved', 'rejected') NOT NULL DEFAULT 'pending',
  requested_at DATETIME NOT NULL, reviewed_at DATETIME NULL,
  reviewed_by_id INT NULL, review_note TEXT NULL,
  CONSTRAINT fk_cancel_registration FOREIGN KEY (registration_id) REFERENCES registrations(id) ON DELETE CASCADE,
  CONSTRAINT fk_cancel_reviewer FOREIGN KEY (reviewed_by_id) REFERENCES users(id) ON DELETE SET NULL
);
