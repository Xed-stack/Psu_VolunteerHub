CREATE TABLE IF NOT EXISTS historical_activities (
    id INT NOT NULL AUTO_INCREMENT,
    source_key VARCHAR(64) NOT NULL,
    source_document VARCHAR(255) NOT NULL,
    source_page INT NOT NULL,
    source_row INT NOT NULL,
    unit_name VARCHAR(120) NOT NULL,
    campus_id INT NULL,
    title VARCHAR(500) NOT NULL,
    activity_type VARCHAR(30) NULL,
    partners TEXT NULL,
    participant_categories TEXT NULL,
    volunteer_count INT NULL,
    year_conducted INT NULL,
    imported_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_historical_activities_source_key (source_key),
    KEY ix_historical_activities_unit_name (unit_name),
    KEY ix_historical_activities_year (year_conducted),
    KEY ix_historical_activities_campus_id (campus_id),
    CONSTRAINT ck_historical_activity_year
        CHECK (year_conducted IS NULL OR year_conducted BETWEEN 1900 AND 2100),
    CONSTRAINT ck_historical_activity_volunteers
        CHECK (volunteer_count IS NULL OR volunteer_count >= 0),
    CONSTRAINT fk_historical_activities_campus
        FOREIGN KEY (campus_id) REFERENCES campuses (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
