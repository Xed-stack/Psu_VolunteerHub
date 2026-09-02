-- Enforce the manuscript's one-to-one Registration-to-Attendance relationship.
-- Preflight checks should return no rows before applying this migration:
--   SELECT registration_id, COUNT(*) FROM attendance
--   WHERE registration_id IS NOT NULL GROUP BY registration_id HAVING COUNT(*) > 1;
--   SELECT id FROM attendance WHERE registration_id IS NULL;

ALTER TABLE attendance
    DROP FOREIGN KEY attendance_ibfk_1,
    MODIFY registration_id INT NOT NULL,
    ADD CONSTRAINT uq_attendance_registration UNIQUE (registration_id),
    ADD CONSTRAINT fk_attendance_registration
        FOREIGN KEY (registration_id) REFERENCES registrations (id)
        ON DELETE CASCADE;
