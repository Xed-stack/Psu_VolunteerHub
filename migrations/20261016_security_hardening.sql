-- Apply once to an existing MySQL database before deploying the security update.
ALTER TABLE users ADD COLUMN auth_version INT NOT NULL DEFAULT 1 AFTER first_use_guide_dismissed_at;

CREATE TABLE auth_security_events (
    id INT NOT NULL AUTO_INCREMENT,
    action VARCHAR(40) NOT NULL,
    subject_hash CHAR(64) NOT NULL,
    created_at DATETIME NOT NULL,
    PRIMARY KEY (id),
    KEY ix_auth_security_events_action (action),
    KEY ix_auth_security_events_subject_hash (subject_hash),
    KEY ix_auth_security_events_created_at (created_at)
) ENGINE=InnoDB;

CREATE TABLE password_reset_tokens (
    id INT NOT NULL AUTO_INCREMENT,
    user_id INT NOT NULL,
    token_hash CHAR(64) NOT NULL,
    expires_at DATETIME NOT NULL,
    used_at DATETIME NULL,
    created_at DATETIME NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_password_reset_tokens_token_hash (token_hash),
    KEY ix_password_reset_tokens_user_id (user_id),
    KEY ix_password_reset_tokens_expires_at (expires_at),
    CONSTRAINT fk_password_reset_tokens_user FOREIGN KEY (user_id)
        REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB;
