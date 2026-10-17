-- Apply once to an existing MySQL database before deploying this feature.
ALTER TABLE users
    ADD COLUMN sex ENUM('male', 'female') NULL AFTER volunteer_type;

CREATE TABLE sdg_goals (
    id INT NOT NULL AUTO_INCREMENT,
    number TINYINT UNSIGNED NOT NULL,
    name VARCHAR(200) NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_sdg_goals_number (number)
) ENGINE=InnoDB;

CREATE TABLE event_sdgs (
    event_id INT NOT NULL,
    sdg_id INT NOT NULL,
    PRIMARY KEY (event_id, sdg_id),
    CONSTRAINT fk_event_sdgs_event FOREIGN KEY (event_id)
        REFERENCES events (id) ON DELETE CASCADE,
    CONSTRAINT fk_event_sdgs_sdg FOREIGN KEY (sdg_id)
        REFERENCES sdg_goals (id) ON DELETE RESTRICT
) ENGINE=InnoDB;

INSERT INTO sdg_goals (number, name) VALUES
    (1, 'No Poverty'), (2, 'Zero Hunger'),
    (3, 'Good Health and Well-Being'), (4, 'Quality Education'),
    (5, 'Gender Equality'), (6, 'Clean Water and Sanitation'),
    (7, 'Affordable and Clean Energy'),
    (8, 'Decent Work and Economic Growth'),
    (9, 'Industry, Innovation and Infrastructure'),
    (10, 'Reduced Inequalities'),
    (11, 'Sustainable Cities and Communities'),
    (12, 'Responsible Consumption and Production'),
    (13, 'Climate Action'), (14, 'Life Below Water'),
    (15, 'Life on Land'),
    (16, 'Peace, Justice and Strong Institutions'),
    (17, 'Partnerships for the Goals')
ON DUPLICATE KEY UPDATE name = VALUES(name);
