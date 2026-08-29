-- Phase 12: Outsider / External Volunteer support.
-- Outsiders are event participants stored separately from User accounts,
-- so no privileged (or login) account is ever created for them.
-- Review the current schema before applying; statements are idempotent
-- where possible but FK/constraint additions may need adjustment.

CREATE TABLE IF NOT EXISTS external_participants (
    id INT AUTO_INCREMENT PRIMARY KEY,
    id_number VARCHAR(50) NOT NULL,
    name VARCHAR(100) NULL,
    contact_number VARCHAR(50) NULL,
    address TEXT NULL,
    email VARCHAR(120) NULL,
    created_at DATETIME NULL,
    UNIQUE KEY uq_external_id_number (id_number)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Registrations: allow outsider participation without a User account.
ALTER TABLE registrations MODIFY user_id INT NULL;

ALTER TABLE registrations ADD COLUMN external_participant_id INT NULL;

ALTER TABLE registrations
    ADD CONSTRAINT fk_registration_external
    FOREIGN KEY (external_participant_id) REFERENCES external_participants (id)
    ON DELETE SET NULL;

-- One registration per outsider per event.
ALTER TABLE registrations
    ADD CONSTRAINT uk_external_event UNIQUE (external_participant_id, event_id);

-- A registration must always reference a User OR an ExternalParticipant.
ALTER TABLE registrations
    ADD CONSTRAINT ck_registration_participant
    CHECK ((user_id IS NOT NULL) OR (external_participant_id IS NOT NULL));

-- Attendance: user_id becomes nullable for outsider attendance records.
ALTER TABLE attendance MODIFY user_id INT NULL;
