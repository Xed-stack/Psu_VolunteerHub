-- Phase 2 schema for existing MySQL databases.
ALTER TABLE users
    ADD COLUMN profile_image_path VARCHAR(255) NULL AFTER reactivation_requested_at,
    ADD COLUMN profile_image_name VARCHAR(255) NULL AFTER profile_image_path;

ALTER TABLE events
    ADD COLUMN cancellation_deadline DATETIME NULL AFTER end_date,
    ADD COLUMN cover_uploaded_by_id INT NULL AFTER cover_image_name,
    ADD COLUMN cover_uploaded_at DATETIME NULL AFTER cover_uploaded_by_id,
    ADD CONSTRAINT fk_events_cover_uploaded_by FOREIGN KEY (cover_uploaded_by_id)
        REFERENCES users(id) ON DELETE SET NULL;

ALTER TABLE milestones
    ADD COLUMN uploaded_by_id INT NULL AFTER category,
    ADD COLUMN uploaded_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP AFTER uploaded_by_id,
    ADD CONSTRAINT fk_milestones_uploaded_by FOREIGN KEY (uploaded_by_id)
        REFERENCES users(id) ON DELETE SET NULL;

ALTER TABLE historical_activities
    ADD COLUMN imported_by_id INT NULL AFTER imported_at,
    ADD CONSTRAINT fk_historical_imported_by FOREIGN KEY (imported_by_id)
        REFERENCES users(id) ON DELETE SET NULL;

CREATE TABLE event_announcements (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    event_id INT NOT NULL,
    author_id INT NULL,
    announcement_type ENUM('last_call', 'event_update', 'cancelled_postponed') NOT NULL,
    message TEXT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX ix_event_announcements_event_id (event_id),
    CONSTRAINT fk_event_announcements_event FOREIGN KEY (event_id)
        REFERENCES events(id) ON DELETE CASCADE,
    CONSTRAINT fk_event_announcements_author FOREIGN KEY (author_id)
        REFERENCES users(id) ON DELETE SET NULL
);
