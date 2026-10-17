-- Public external-volunteer consent records.
-- Existing coordinator-entered and historical registrations remain valid.
ALTER TABLE registrations
    ADD COLUMN IF NOT EXISTS external_privacy_accepted_at DATETIME NULL,
    ADD COLUMN IF NOT EXISTS external_privacy_version VARCHAR(30) NULL;
