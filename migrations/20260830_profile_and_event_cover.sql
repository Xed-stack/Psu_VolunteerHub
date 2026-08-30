-- Volunteer classification, unique PSU identifiers, and event cover images.
-- Compatible with MySQL 8.x and MariaDB 10.4+.

UPDATE users SET id_number = NULL WHERE TRIM(COALESCE(id_number, '')) = '';

ALTER TABLE users
    MODIFY id_number VARCHAR(50) NULL,
    ADD COLUMN volunteer_type VARCHAR(20) NULL AFTER role,
    ADD COLUMN college_affiliation VARCHAR(150) NULL AFTER volunteer_type;

ALTER TABLE users
    ADD UNIQUE KEY uq_users_id_number (id_number);

ALTER TABLE events
    ADD COLUMN cover_image_path VARCHAR(255) NULL AFTER location,
    ADD COLUMN cover_image_name VARCHAR(255) NULL AFTER cover_image_path;

-- Rollback (manual, if needed):
-- ALTER TABLE events DROP COLUMN cover_image_name, DROP COLUMN cover_image_path;
-- ALTER TABLE users DROP INDEX uq_users_id_number,
--   DROP COLUMN college_affiliation, DROP COLUMN volunteer_type;
