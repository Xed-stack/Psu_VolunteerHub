-- Run once on an existing MySQL database.
ALTER TABLE users
    ADD COLUMN first_use_guide_dismissed_at DATETIME NULL AFTER profile_image_name;
