-- Admin category management and deactivated-account lifecycle.
CREATE TABLE IF NOT EXISTS activity_categories (
  id INT NOT NULL AUTO_INCREMENT,
  name VARCHAR(50) NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_activity_categories_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

ALTER TABLE users
  ADD COLUMN deactivated_at DATETIME NULL,
  ADD COLUMN reactivation_requested_at DATETIME NULL;

ALTER TABLE events
  ADD COLUMN created_by_id INT NULL,
  ADD CONSTRAINT fk_events_created_by
    FOREIGN KEY (created_by_id) REFERENCES users(id) ON DELETE SET NULL;

INSERT IGNORE INTO activity_categories (name) VALUES ('General');
INSERT IGNORE INTO activity_categories (name)
  SELECT DISTINCT category FROM events
  WHERE category IS NOT NULL AND TRIM(category) <> '';
