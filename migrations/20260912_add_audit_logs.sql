CREATE TABLE IF NOT EXISTS audit_logs (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    actor_id INT NULL,
    action VARCHAR(100) NOT NULL,
    target_type VARCHAR(50) NOT NULL,
    target_id INT NULL,
    details TEXT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX ix_audit_logs_created_at (created_at),
    INDEX ix_audit_logs_actor_id (actor_id),
    CONSTRAINT fk_audit_logs_actor FOREIGN KEY (actor_id)
        REFERENCES users(id) ON DELETE SET NULL
);
