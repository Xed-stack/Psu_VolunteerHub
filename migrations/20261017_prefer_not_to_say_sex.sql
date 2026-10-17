-- Preserve existing values and allow a declared non-disclosure response.
-- NULL continues to mean a legacy account has no recorded response.
ALTER TABLE users
    MODIFY COLUMN sex ENUM('male', 'female', 'prefer_not_to_say') NULL;
