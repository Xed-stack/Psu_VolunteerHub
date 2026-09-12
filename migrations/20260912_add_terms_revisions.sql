CREATE TABLE IF NOT EXISTS terms_revisions (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(150) NOT NULL,
    body TEXT NOT NULL,
    version VARCHAR(30) NOT NULL UNIQUE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    published_by_id INT NULL,
    published_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_terms_revisions_published_by FOREIGN KEY (published_by_id)
        REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS terms_acceptances (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    revision_id INT NOT NULL,
    accepted_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_user_terms_revision (user_id, revision_id),
    CONSTRAINT fk_terms_acceptances_user FOREIGN KEY (user_id)
        REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_terms_acceptances_revision FOREIGN KEY (revision_id)
        REFERENCES terms_revisions(id) ON DELETE CASCADE
);
